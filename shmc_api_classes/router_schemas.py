"""Shared response schemas for SHMC router base endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RouterResponseBase(BaseModel):
    """Common response envelope for inherited router endpoints."""

    message: str = Field(
        ...,
        description="Human-readable endpoint result message.",
        examples=["OK - says GET_basic_config on router: AquaRouter"],
    )
    timestamp: float = Field(
        ...,
        description="Unix timestamp when the response was generated.",
        examples=[1710000000.0],
    )


class DBPublicInfo(BaseModel):
    """Public, non-secret DB role metadata."""

    fullname: str | None = Field(
        None,
        description="Configured database filename or connection string.",
        examples=["/srv/shmc/.Auth.db"],
    )
    style: str | None = Field(
        None,
        description="Configured database style.",
        examples=["SQLite"],
    )


class DBInitInfo(BaseModel):
    """Recorded DB initialization status."""

    results: dict[str, Any] = Field(
        default_factory=dict,
        description="Successful DB initialization results keyed by DB role.",
        examples=[{"AUTH": {"created_file": True, "created_schema": True}}],
    )
    errors: dict[str, str] = Field(
        default_factory=dict,
        description="DB initialization errors keyed by DB role.",
        examples=[{"AUTH": "create_schema=True requires schema_providers."}],
    )


class DBRegistryPublicConfig(BaseModel):
    """Public DB registry state exposed by diagnostics endpoints."""

    default_db_role: str | None = Field(
        None,
        description="Default DB role used when an endpoint omits db_role.",
        examples=["AUTH"],
    )
    db_roles: list[str] = Field(
        default_factory=list,
        description="Configured DB role names.",
        examples=[["AUTH", "OPTIMIZER"]],
    )
    dbs: dict[str, DBPublicInfo] = Field(
        default_factory=dict,
        description="Public DB config keyed by role.",
        examples=[{"AUTH": {"fullname": "/srv/shmc/.Auth.db", "style": "SQLite"}}],
    )
    db_init: DBInitInfo = Field(
        default_factory=DBInitInfo,
        description="Recorded DB initialization result and error metadata.",
    )


class BasicConfigPayload(BaseModel):
    """Payload for the basic router diagnostics endpoint."""

    name: str = Field(..., description="Router instance name.", examples=["AuthRouter"])
    alias: str = Field(..., description="Router alias.", examples=["Auth"])
    ip: str = Field(..., description="Configured router/backend IP.", examples=["0.0.0.0"])
    port: int = Field(..., description="Configured router/backend port.", examples=[8080])
    version: str | None = Field(None, description="Router implementation version.", examples=["0.1.0"])
    db_fullname: str | None = Field(None, description="Legacy single DB filename.", examples=["/srv/shmc/.Auth.db"])
    db_style: str | None = Field(None, description="Legacy single DB style.", examples=["SQLite"])
    db_registry: DBRegistryPublicConfig | None = Field(
        None,
        description="Public multi-DB registry metadata when available.",
    )
    claims_sub: str | None = Field(
        None,
        description="Subject claim from the authenticated JWT.",
        examples=["user-uuid"],
    )


class BasicConfigResponse(RouterResponseBase):
    """Response for GET /v0/basic-config."""

    payload: BasicConfigPayload


class DBRolesResponse(RouterResponseBase):
    """Response for GET /v0/dbs."""

    payload: DBRegistryPublicConfig


class DBTablesPayload(BaseModel):
    """Payload listing reflected tables for one DB role."""

    db_role: str = Field(..., description="Resolved DB role.", examples=["AUTH"])
    tables: list[str] = Field(
        default_factory=list,
        description="Non-internal SQLite table names.",
        examples=[["auth_users", "auth_projects"]],
    )


class DBTablesResponse(RouterResponseBase):
    """Response for GET /v0/dbs/{db_role}/tables."""

    payload: DBTablesPayload


class DBTableDumpPayload(BaseModel):
    """Payload containing one table dump."""

    db_role: str = Field(..., description="Resolved DB role.", examples=["AUTH"])
    table: str = Field(..., description="Dumped table name.", examples=["auth_users"])
    columns: list[str] = Field(
        default_factory=list,
        description="Column names returned for the table.",
        examples=[["uuid", "email", "auth_code"]],
    )
    rows: list[dict[str, Any]] = Field(
        default_factory=list,
        description="JSON-safe table rows.",
        examples=[[{"uuid": "abc", "email": "user@example.com", "auth_code": 4}]],
    )
    row_count: int = Field(..., description="Number of returned rows.", examples=[1])


class DBTableDumpResponse(RouterResponseBase):
    """Response for GET /v0/dbs/{db_role}/tables/{table_name}."""

    payload: DBTableDumpPayload


class FullDBDumpPayload(BaseModel):
    """Payload containing one role's full DB dump."""

    db_role: str = Field(..., description="Resolved DB role.", examples=["AUTH"])
    db: DBPublicInfo | None = Field(None, description="Public config for the dumped DB role.")
    tables: dict[str, DBTableDumpPayload] = Field(
        default_factory=dict,
        description="Table dumps keyed by table name.",
    )


class FullDBDumpResponse(RouterResponseBase):
    """Response for GET /v0/full-db-data."""

    payload: FullDBDumpPayload
