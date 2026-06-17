"""SHMC router base classes.

The structure is capability-oriented instead of one rigid inheritance ladder.
The legacy implementation is preserved as ``shmc_api_classes.routers_legacy``.

=== by Sziller & GPT-5 ===
"""

from __future__ import annotations

import logging
import os.path
import sqlite3
import time
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Annotated, Any, Optional, Protocol, cast

from fastapi import APIRouter, Depends, HTTPException, Path as PathParam, Query, status

from shmc_api_classes.router_schemas import (
    BasicConfigPayload,
    BasicConfigResponse,
    DBRegistryPublicConfig,
    DBRolesResponse,
    DBTableDumpPayload,
    DBTableDumpResponse,
    DBTablesPayload,
    DBTablesResponse,
    FullDBDumpPayload,
    FullDBDumpResponse,
)
from shmc_api_classes.schema_init import initialize_db_role
from sql_access import sql_interface as sqli

lg = logging.getLogger()


try:
    from shmc_auth_client.auth_code import has_auth_bit
except ImportError:
    try:
        from shmc_auth.auth_code import has_auth_bit
    except ImportError:

        def has_auth_bit(auth_code: int, bit_index: int) -> bool:
            """Return True when the selected auth_code bit is set."""
            return auth_code & (1 << bit_index) != 0


try:
    from shmc_auth_client.security import get_current_claims, require_auth_admin_claims
except ImportError:
    try:
        from shmc_auth.security import get_current_claims, require_auth_admin_claims
    except ImportError:

        async def get_current_claims() -> dict[str, Any]:
            """Fallback auth dependency used when no auth package is installed."""
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="No SHMC auth dependency package is installed.",
            )

        def require_auth_admin_claims(claims: dict[str, Any]) -> None:
            """Fallback admin checker used when no auth package is installed."""
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="No SHMC auth dependency package is installed.",
            )


DBSpecDict = dict[str, Any]
DBRegistry = dict[str, DBSpecDict]


class RouterIdentity(Protocol):
    """Router identity attributes required by endpoint mixins."""

    name: str
    alias: str
    ip: str
    port: int


class DBInspectionCapability(Protocol):
    """DB inspection methods required by admin endpoint mixins."""

    def db_public_config(self) -> dict[str, Any]:
        """Return public DB registry metadata."""
        ...

    def resolve_db_role(self, db_role: Optional[str] = None) -> str:
        """Resolve a configured DB role."""
        ...

    def list_db_tables(self, db_role: Optional[str] = None) -> list[str]:
        """List tables for a DB role."""
        ...

    def dump_db_table(self, db_role: Optional[str], table_name: str) -> dict[str, Any]:
        """Dump one table from a DB role."""
        ...

    def dump_db(self, db_role: Optional[str] = None, table_name: Optional[str] = None) -> dict[str, Any]:
        """Dump one table or all tables for a DB role."""
        ...


def _as_api_router(value: object) -> APIRouter:
    """Treat a mixin instance as an APIRouter."""
    return cast(APIRouter, value)


def _as_router_identity(value: object) -> RouterIdentity:
    """Treat a mixin instance as router identity data."""
    return cast(RouterIdentity, value)


def _as_db_inspection(value: object) -> DBInspectionCapability:
    """Treat a mixin instance as DB inspection capable."""
    return cast(DBInspectionCapability, value)


DBRolePath = Annotated[
    str,
    PathParam(
        title="DB role",
        description=(
            "Configured DB role to inspect. Role names are defined by the router's DB registry, "
            "for example AUTH, AQUA, OBSR, R_KS, or OPTIMIZER."
        ),
        examples=["AUTH"],
        min_length=1,
    ),
]
TableNamePath = Annotated[
    str,
    PathParam(
        title="Table name",
        description=(
            "SQLite table name to dump. The name must exist in the selected DB role. "
            "Use /v0/dbs/{db_role}/tables first to discover available values."
        ),
        examples=["auth_users"],
        min_length=1,
        pattern=r"^[A-Za-z_][A-Za-z0-9_]*$",
    ),
]
DBRoleQuery = Annotated[
    Optional[str],
    Query(
        title="DB role",
        description=(
            "Optional configured DB role. If omitted, the router's default_db_role is used. "
            "Use /v0/dbs to inspect available roles."
        ),
        examples=["AUTH"],
    ),
]
TableNameQuery = Annotated[
    Optional[str],
    Query(
        title="Table name",
        description="Optional table name. If omitted, all tables in the selected DB role are dumped.",
        examples=["auth_users"],
        pattern=r"^[A-Za-z_][A-Za-z0-9_]*$",
    ),
]


def _jsonable_value(value: Any) -> Any:
    """Convert SQLite values to JSON-safe values."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


def _quote_sqlite_identifier(identifier: str) -> str:
    """Quote a SQLite identifier after metadata validation."""
    return '"' + identifier.replace('"', '""') + '"'


def _clean_db_spec(role: str, spec: Any) -> DBSpecDict:
    """Normalize one DB config entry while keeping dict-style access."""
    if spec is None:
        spec = {}
    if isinstance(spec, str):
        spec = {"fullname": spec, "style": "SQLite"}
    if not isinstance(spec, dict):
        raise TypeError(f"DB spec for role '{role}' must be a dict or string path.")

    fullname = spec.get("fullname") or spec.get("db_fullname") or spec.get("path")
    style = spec.get("style") or spec.get("db_style") or "SQLite"
    normalized: DBSpecDict = {
        **spec,
        "role": role,
        "fullname": fullname,
        "style": style,
    }
    return normalized


class SHMCBaseRouter(APIRouter):
    """Base FastAPI router for SHMC modules."""

    ccn = "SHMCBaseRouter"

    def __init__(
        self,
        name: str,
        alias: Optional[str] = None,
        ip: str = "0.0.0.0",
        port: int = 0,
        version: str | None = None,
    ) -> None:
        """Initialize router identity and APIRouter state."""
        super().__init__()
        self.name = name
        self.alias = alias if alias else name[:4]
        self.ip = ip
        self.port = port
        self.version = version or "0.1.0"
        self.router = self
        lg.info(
            "init.ed   : with name='%s', alias='%s', ip='%s', port='%s' - says %s",
            self.name,
            self.alias,
            self.ip,
            self.port,
            self.ccn,
        )

    def reinit(self) -> None:
        """Reinitialize runtime-derived state after dynamic attrs are assigned."""
        lg.debug("reinit    : - says %s", self.ccn)


class AuthorizationMixin:
    """Small authorization helpers; request auth remains dependency based."""

    auth_dict: dict[str, Any]

    def _init_authorization(self, auth_dict: Optional[dict[str, Any]] = None) -> None:
        """Initialize authorization helper config."""
        self.auth_dict = auth_dict or {}
        lg.info("init.ed   : with auth_dict=%s - says %s", self.auth_dict, self.__class__.__name__)

    def check_authorization(self, auth_code: int, nth_switch: int) -> bool:
        """Return True when the selected auth_code bit is set."""
        lg.debug(
            "%s performing authorization check with auth_code=%s, nth_switch=%s",
            self.__class__.__name__,
            auth_code,
            nth_switch,
        )
        result = has_auth_bit(auth_code=auth_code, bit_index=nth_switch)
        lg.debug("auth res. : %s", result)
        return result


class DBRegistryMixin:
    """Database registry capability for legacy single DB and multirole DB config."""

    db: Optional[list[dict[str, Any]]]
    db_fullname: Optional[str]
    db_style: Optional[str]
    dbs: DBRegistry
    default_db_role: Optional[str]
    db_init_results: dict[str, Any]
    db_init_errors: dict[str, str]

    def _init_db_registry(
        self,
        db_fullname: Optional[str] = None,
        db_style: Optional[str] = None,
        dbs: Optional[dict[str, Any]] = None,
        default_db_role: Optional[str] = None,
    ) -> None:
        """Initialize legacy and multirole DB registry config."""
        self.db = None
        self.db_fullname = db_fullname
        self.db_style = db_style or "SQLite"
        self.dbs = {}
        self.db_init_results = {}
        self.db_init_errors = {}

        if dbs:
            for role, spec in dbs.items():
                role_str = str(role)
                self.dbs[role_str] = _clean_db_spec(role_str, spec)

        if db_fullname and not self.dbs:
            role = default_db_role or "DEFAULT"
            self.dbs[role] = _clean_db_spec(role, {"fullname": db_fullname, "style": self.db_style})

        if default_db_role:
            self.default_db_role = default_db_role
        elif len(self.dbs) == 1:
            self.default_db_role = next(iter(self.dbs))
        else:
            self.default_db_role = None

        lg.info(
            "init.ed   : with db_fullname='%s', db_style='%s', db_roles=%s - says %s",
            self.db_fullname,
            self.db_style,
            list(self.dbs),
            self.__class__.__name__,
        )

    def reinit(self) -> None:
        """Check configured DB file presence without creating or mutating DBs."""
        cast(Any, super()).reinit()
        for role, spec in self.dbs.items():
            fullname = spec.get("fullname")
            if not fullname:
                lg.warning("undefined : database name for role %s - says %s", role, self.__class__.__name__)
            elif os.path.isfile(str(fullname)):
                lg.info("found DB  : %s role=%s - says %s", fullname, role, self.__class__.__name__)
            else:
                lg.warning("no DB     : %s role=%s - says %s", fullname, role, self.__class__.__name__)

    def db_public_config(self) -> dict[str, Any]:
        """Return DB registry metadata for status/config responses."""
        return {
            "default_db_role": self.default_db_role,
            "db_roles": list(self.dbs),
            "dbs": {
                role: {
                    "fullname": spec.get("fullname"),
                    "style": spec.get("style"),
                }
                for role, spec in self.dbs.items()
            },
            "db_init": {
                "results": {
                    role: self._jsonable_db_init_value(result)
                    for role, result in self.db_init_results.items()
                },
                "errors": dict(self.db_init_errors),
            },
        }

    @staticmethod
    def _jsonable_db_init_value(value: Any) -> Any:
        """Convert DB-init status values into JSON-safe structures."""
        if is_dataclass(value):
            return {
                key: DBRegistryMixin._jsonable_db_init_value(item)
                for key, item in asdict(value).items()
            }
        if isinstance(value, dict):
            return {
                str(key): DBRegistryMixin._jsonable_db_init_value(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple, set)):
            return [DBRegistryMixin._jsonable_db_init_value(item) for item in value]
        return value

    def record_db_init_result(self, db_role: str, result: Any) -> None:
        """Record successful DB initialization status for later introspection."""
        self.db_init_results[str(db_role)] = result
        self.db_init_errors.pop(str(db_role), None)

    def record_db_init_error(self, db_role: str, error: BaseException | str) -> None:
        """Record DB initialization failure status for later introspection."""
        self.db_init_errors[str(db_role)] = str(error)

    def initialize_configured_dbs(self) -> dict[str, Any]:
        """Explicitly initialize DB roles that request file/schema initialization."""
        for db_role, db_spec in self.dbs.items():
            if not (db_spec.get("ensure_file") or db_spec.get("create_schema")):
                continue
            try:
                result = initialize_db_role(db_role, db_spec)
            except Exception as exc:
                self.record_db_init_error(db_role, exc)
                raise
            self.record_db_init_result(db_role, result)

        return self.db_init_results

    def resolve_db_role(self, db_role: Optional[str] = None) -> str:
        """Resolve requested DB role, accepting case-insensitive matches."""
        if db_role is None:
            if self.default_db_role:
                return self.default_db_role
            if not self.dbs:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No databases configured.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"db_role is required. Available roles: {list(self.dbs)}",
            )

        if db_role in self.dbs:
            return db_role

        lowered = db_role.lower()
        for role in self.dbs:
            if role.lower() == lowered:
                return role

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown db_role '{db_role}'. Available roles: {list(self.dbs)}",
        )

    def get_db_spec(self, db_role: Optional[str] = None) -> DBSpecDict:
        """Return normalized DB spec for a role."""
        role = self.resolve_db_role(db_role)
        return self.dbs[role]

    def read_db_table(self, row_obj: Any, db_role: Optional[str] = None) -> None:
        """Legacy ORM table read helper, now optionally role-aware."""
        spec = self.get_db_spec(db_role)
        loc_session = None
        try:
            loc_session = sqli.createSession(
                db_fullname=str(spec.get("fullname")),
                style=str(spec.get("style") or "SQLite"),
                tables=None,
            )
            self.db = sqli.QUERY_entire_table(ordered_by="timestamp", row_obj=row_obj, session=loc_session)
            lg.info("read DB   : successfully from DB '%s'", spec.get("fullname"))
        except Exception as exc:
            lg.error("read DB   : Error reading DB '%s': %s", spec.get("fullname"), exc)
        finally:
            if loc_session is not None:
                loc_session.close()

    def _require_sqlite_spec(self, db_role: Optional[str] = None) -> tuple[str, DBSpecDict]:
        """Return a valid SQLite DB spec or raise an HTTP error."""
        role = self.resolve_db_role(db_role)
        spec = self.dbs[role]
        style = str(spec.get("style") or "SQLite")
        if style.lower() != "sqlite":
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"DB style '{style}' is not supported by generic DB dump yet.",
            )
        fullname = spec.get("fullname")
        if not fullname:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"DB role '{role}' has no fullname.")
        if not os.path.isfile(str(fullname)):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"DB file not found for role '{role}'.")
        return role, spec

    def list_db_tables(self, db_role: Optional[str] = None) -> list[str]:
        """List user tables for a SQLite DB role."""
        _, spec = self._require_sqlite_spec(db_role)
        with sqlite3.connect(str(spec["fullname"])) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        return [str(row[0]) for row in rows]

    def dump_db_table(self, db_role: Optional[str], table_name: str) -> dict[str, Any]:
        """Dump one SQLite table using reflection-safe table validation."""
        role, spec = self._require_sqlite_spec(db_role)
        tables = self.list_db_tables(role)
        if table_name not in tables:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown table '{table_name}' for db_role '{role}'. Available tables: {tables}",
            )

        with sqlite3.connect(str(spec["fullname"])) as conn:
            conn.row_factory = sqlite3.Row
            quoted_table = _quote_sqlite_identifier(table_name)
            column_info = conn.execute(f"PRAGMA table_info({quoted_table})").fetchall()
            columns = [str(row["name"]) for row in column_info]
            order_clause = f" ORDER BY {_quote_sqlite_identifier('timestamp')}" if "timestamp" in columns else ""
            rows = conn.execute(f"SELECT * FROM {quoted_table}{order_clause}").fetchall()

        return {
            "db_role": role,
            "table": table_name,
            "columns": columns,
            "rows": [
                {key: _jsonable_value(row[key]) for key in row.keys()}
                for row in rows
            ],
            "row_count": len(rows),
        }

    def dump_db(self, db_role: Optional[str] = None, table_name: Optional[str] = None) -> dict[str, Any]:
        """Dump one table or all tables for a DB role."""
        role, _ = self._require_sqlite_spec(db_role)
        tables = self.list_db_tables(role)
        if table_name:
            return {
                "db_role": role,
                "db": self.db_public_config()["dbs"].get(role),
                "tables": {table_name: self.dump_db_table(role, table_name)},
            }
        return {
            "db_role": role,
            "db": self.db_public_config()["dbs"].get(role),
            "tables": {table: self.dump_db_table(role, table) for table in tables},
        }


class BasicInfoEndpointsMixin:
    """Capability mixin adding harmless router-info endpoints."""

    def _add_basic_info_endpoints(self) -> None:
        """Register basic router-info endpoints."""
        router = _as_api_router(self)
        router.add_api_route(
            path="/v0/basic-config",
            endpoint=self.GET_basic_config,
            response_model=BasicConfigResponse,
            methods=["GET"],
            summary="Return Router Basic Configuration",
            description=(
                "Returns non-secret router metadata, DB registry information, and the authenticated "
                "JWT subject. This endpoint is inherited by shared SHMC router base classes."
            ),
        )

    async def GET_basic_config(
        self,
        current_claims: dict[str, Any] = Depends(get_current_claims),
    ) -> BasicConfigResponse:
        """Return non-secret runtime metadata for the current router."""
        timestamp = time.time()
        identity = _as_router_identity(self)
        return BasicConfigResponse(
            payload=BasicConfigPayload(
                name=identity.name,
                alias=identity.alias,
                ip=identity.ip,
                port=identity.port,
                version=getattr(self, "version", None),
                db_fullname=getattr(self, "db_fullname", None),
                db_style=getattr(self, "db_style", None),
                db_registry=(
                    DBRegistryPublicConfig.model_validate(self.db_public_config())
                    if isinstance(self, DBRegistryMixin)
                    else None
                ),
                claims_sub=current_claims.get("sub"),
            ),
            message=f"OK - says GET_basic_config on router: {self.__class__.__name__}",
            timestamp=timestamp,
        )


class AdminDBEndpointsMixin:
    """Capability mixin adding admin-protected generic DB inspection endpoints."""

    def _add_admin_db_endpoints(self) -> None:
        """Register admin DB inspection endpoints."""
        router = _as_api_router(self)
        router.add_api_route(
            path="/v0/dbs",
            endpoint=self.GET_db_roles,
            response_model=DBRolesResponse,
            methods=["GET"],
            summary="List Router DB Roles",
            description=(
                "Admin-only endpoint returning the DB roles configured for this router and recorded "
                "DB initialization status."
            ),
        )
        router.add_api_route(
            path="/v0/dbs/{db_role}/tables",
            endpoint=self.GET_db_tables,
            response_model=DBTablesResponse,
            methods=["GET"],
            summary="List Tables For DB Role",
            description="Admin-only endpoint returning all non-internal SQLite table names for one DB role.",
        )
        router.add_api_route(
            path="/v0/dbs/{db_role}/tables/{table_name}",
            endpoint=self.GET_db_table_data,
            response_model=DBTableDumpResponse,
            methods=["GET"],
            summary="Dump One DB Table",
            description=(
                "Admin-only endpoint returning all rows from one reflected SQLite table after validating "
                "the table name against the selected DB role."
            ),
        )
        router.add_api_route(
            path="/v0/full-db-data",
            endpoint=self.GET_full_db_data,
            response_model=FullDBDumpResponse,
            methods=["GET"],
            summary="Dump DB Data",
            description=(
                "Admin-only endpoint returning either a full DB dump for one DB role or one selected table. "
                "This endpoint can expose sensitive operational data and must remain admin-only."
            ),
        )

    def _require_admin(self, claims: dict[str, Any]) -> None:
        """Require admin claims for sensitive endpoints."""
        require_auth_admin_claims(claims)

    async def GET_db_roles(
        self,
        current_claims: dict[str, Any] = Depends(get_current_claims),
    ) -> DBRolesResponse:
        """Return the DB registry configured for this router."""
        self._require_admin(current_claims)
        timestamp = time.time()
        db = _as_db_inspection(self)
        return DBRolesResponse(
            payload=DBRegistryPublicConfig.model_validate(db.db_public_config()),
            message="OK - DB roles returned - says GET_db_roles",
            timestamp=timestamp,
        )

    async def GET_db_tables(
        self,
        db_role: DBRolePath,
        current_claims: dict[str, Any] = Depends(get_current_claims),
    ) -> DBTablesResponse:
        """Return all non-internal table names for one configured DB role."""
        self._require_admin(current_claims)
        timestamp = time.time()
        db = _as_db_inspection(self)
        role = db.resolve_db_role(db_role)
        return DBTablesResponse(
            payload=DBTablesPayload(db_role=role, tables=db.list_db_tables(role)),
            message="OK - DB tables returned - says GET_db_tables",
            timestamp=timestamp,
        )

    async def GET_db_table_data(
        self,
        db_role: DBRolePath,
        table_name: TableNamePath,
        current_claims: dict[str, Any] = Depends(get_current_claims),
    ) -> DBTableDumpResponse:
        """Return all rows from one selected table in one configured DB role."""
        self._require_admin(current_claims)
        timestamp = time.time()
        db = _as_db_inspection(self)
        return DBTableDumpResponse(
            payload=DBTableDumpPayload.model_validate(db.dump_db_table(db_role, table_name)),
            message="OK - DB table data returned - says GET_db_table_data",
            timestamp=timestamp,
        )

    async def GET_full_db_data(
        self,
        db_role: DBRoleQuery = None,
        table: TableNameQuery = None,
        current_claims: dict[str, Any] = Depends(get_current_claims),
    ) -> FullDBDumpResponse:
        """Return a full DB dump or one selected table for a configured DB role."""
        self._require_admin(current_claims)
        timestamp = time.time()
        db = _as_db_inspection(self)
        return FullDBDumpResponse(
            payload=FullDBDumpPayload.model_validate(db.dump_db(db_role=db_role, table_name=table)),
            message="OK - full DB data returned - says GET_full_db_data",
            timestamp=timestamp,
        )


class EngineClientMixin:
    """Capability mixin for routers that talk to an engine/ZMQ backend."""

    zmq_port: int

    def _init_engine_client(self, zmq_port: int = 0) -> None:
        """Initialize engine client metadata."""
        self.zmq_port = zmq_port
        lg.info("init.ed   : with zmq_port='%s' - says %s", self.zmq_port, self.__class__.__name__)

    def reinit(self) -> None:
        """Reinitialize engine metadata and parent state."""
        lg.debug("reinit    : with zmq_port=%s - says %s", getattr(self, "zmq_port", None), self.__class__.__name__)
        cast(Any, super()).reinit()


class BaseRouter(SHMCBaseRouter):
    """Backward-compatible base router name."""


class AuthorizedRouter(AuthorizationMixin, SHMCBaseRouter):
    """Backward-compatible router with auth_code helper methods."""

    def __init__(
        self,
        name: str,
        alias: Optional[str] = None,
        ip: str = "0.0.0.0",
        port: int = 0,
        auth_dict: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize a router with authorization helpers."""
        super().__init__(name=name, alias=alias, ip=ip, port=port)
        self._init_authorization(auth_dict)


class DBHandlerRouter(DBRegistryMixin, AuthorizationMixin, SHMCBaseRouter):
    """Router with auth_code helpers plus one or more configured DBs."""

    def __init__(
        self,
        name: str,
        alias: Optional[str] = None,
        ip: str = "0.0.0.0",
        port: int = 0,
        auth_dict: Optional[dict[str, Any]] = None,
        db_fullname: Optional[str] = None,
        db_style: Optional[str] = None,
        dbs: Optional[dict[str, Any]] = None,
        default_db_role: Optional[str] = None,
    ) -> None:
        """Initialize a router with auth helpers and DB registry."""
        super().__init__(name=name, alias=alias, ip=ip, port=port)
        self._init_authorization(auth_dict)
        self._init_db_registry(
            db_fullname=db_fullname,
            db_style=db_style,
            dbs=dbs,
            default_db_role=default_db_role,
        )


class SkeletonRouter(AdminDBEndpointsMixin, BasicInfoEndpointsMixin, DBHandlerRouter):
    """Router with default SHMC endpoints plus DB registry support."""

    def __init__(
        self,
        name: str,
        alias: Optional[str] = None,
        ip: str = "0.0.0.0",
        port: int = 0,
        auth_dict: Optional[dict[str, Any]] = None,
        db_fullname: Optional[str] = None,
        db_style: Optional[str] = None,
        dbs: Optional[dict[str, Any]] = None,
        default_db_role: Optional[str] = None,
    ) -> None:
        """Initialize a router with default SHMC endpoints."""
        super().__init__(
            name=name,
            alias=alias,
            ip=ip,
            port=port,
            auth_dict=auth_dict,
            db_fullname=db_fullname,
            db_style=db_style,
            dbs=dbs,
            default_db_role=default_db_role,
        )
        self._add_basic_info_endpoints()
        self._add_admin_db_endpoints()
        lg.info("init.ed   : with default SHMC endpoints - says %s", self.__class__.__name__)


class EngineMngrRouter(EngineClientMixin, SkeletonRouter):
    """Router with default endpoints, DB registry support, and engine metadata."""

    def __init__(
        self,
        name: str,
        alias: Optional[str] = None,
        ip: str = "0.0.0.0",
        port: int = 0,
        auth_dict: Optional[dict[str, Any]] = None,
        db_fullname: Optional[str] = None,
        db_style: Optional[str] = None,
        zmq_port: int = 0,
        dbs: Optional[dict[str, Any]] = None,
        default_db_role: Optional[str] = None,
    ) -> None:
        """Initialize a router with engine metadata."""
        super().__init__(
            name=name,
            alias=alias,
            ip=ip,
            port=port,
            auth_dict=auth_dict,
            db_fullname=db_fullname,
            db_style=db_style,
            dbs=dbs,
            default_db_role=default_db_role,
        )
        self._init_engine_client(zmq_port=zmq_port)


__all__ = [
    "SHMCBaseRouter",
    "AuthorizationMixin",
    "DBRegistryMixin",
    "BasicInfoEndpointsMixin",
    "AdminDBEndpointsMixin",
    "EngineClientMixin",
    "BaseRouter",
    "AuthorizedRouter",
    "DBHandlerRouter",
    "SkeletonRouter",
    "EngineMngrRouter",
]
