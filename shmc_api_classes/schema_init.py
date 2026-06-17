"""Opt-in SQLite DB file and schema initialization helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import create_engine

from .schema_provider import load_schema_providers


@dataclass(frozen=True)
class DBInitResult:
    """Result metadata for one DB role initialization pass."""

    role: str
    fullname: str
    style: str
    ensured_file: bool = False
    created_file: bool = False
    created_schema: bool = False
    schema_providers: list[str] = field(default_factory=list)


def initialize_db_role(db_role: str, db_spec: dict[str, Any]) -> DBInitResult:
    """Initialize one DB role only when its spec explicitly opts in."""
    style = str(db_spec.get("style") or "SQLite")
    if style.lower() != "sqlite":
        raise NotImplementedError(f"Only SQLite DB initialization is supported. Got style={style!r}.")

    fullname = db_spec.get("fullname")
    if not fullname:
        raise ValueError(f"DB role {db_role!r} has no fullname.")

    ensure_file = bool(db_spec.get("ensure_file"))
    create_schema = bool(db_spec.get("create_schema"))
    provider_refs = list(db_spec.get("schema_providers") or [])

    if create_schema and not provider_refs:
        raise ValueError("create_schema=True requires schema_providers.")

    created_file = False
    if ensure_file:
        parent = os.path.dirname(os.path.abspath(fullname))
        if parent:
            os.makedirs(parent, exist_ok=True)
        if not os.path.exists(fullname):
            open(fullname, "a", encoding="utf-8").close()
            created_file = True

    created_schema = False
    if create_schema:
        loaded_providers = load_schema_providers(provider_refs)
        engine = create_engine(f"sqlite:///{fullname}", future=True)
        for loaded in loaded_providers:
            provider_data = loaded.provider()
            for metadata in provider_data.get("metadata") or []:
                metadata.create_all(engine)
            for base in provider_data.get("bases") or []:
                base.metadata.create_all(engine)
        engine.dispose()
        created_schema = True

    return DBInitResult(
        role=str(db_role),
        fullname=str(fullname),
        style=style,
        ensured_file=ensure_file,
        created_file=created_file,
        created_schema=created_schema,
        schema_providers=provider_refs,
    )
