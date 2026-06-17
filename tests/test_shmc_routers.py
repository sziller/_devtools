import sqlite3

import pytest
from fastapi import FastAPI, HTTPException, status

from shmc_api_classes.routers import (
    DBHandlerRouter,
    EngineMngrRouter,
    SHMCBaseRouter,
    SkeletonRouter,
)


def test_router_imports_and_compatibility_shape():
    router = EngineMngrRouter(
        name="Optimizer",
        alias=None,
        ip="127.0.0.1",
        port=8001,
        zmq_port=5555,
        dbs={"AUTH": {"fullname": "/tmp/auth.db", "style": "SQLite"}},
        default_db_role="AUTH",
    )

    assert isinstance(router, SHMCBaseRouter)
    assert router.router is router
    assert router.alias == "Opti"
    assert router.zmq_port == 5555
    assert router.resolve_db_role("auth") == "AUTH"


def test_openapi_includes_inherited_routes():
    app = FastAPI()
    app.include_router(SkeletonRouter(name="Auth", db_fullname="/tmp/auth.db"))

    paths = app.openapi()["paths"]

    assert "/v0/basic-config" in paths
    assert "/v0/dbs" in paths
    assert "/v0/dbs/{db_role}/tables" in paths
    assert "/v0/dbs/{db_role}/tables/{table_name}" in paths
    assert "/v0/full-db-data" in paths


def test_legacy_and_multi_db_registry_config():
    legacy = DBHandlerRouter(name="Legacy", db_fullname="/tmp/legacy.db", db_style="SQLite")
    modern = DBHandlerRouter(
        name="Modern",
        dbs={
            "AUTH": {"fullname": "/tmp/auth.db", "style": "SQLite"},
            "OPTIMIZER": "/tmp/optimizer.db",
        },
        default_db_role="AUTH",
    )

    assert legacy.default_db_role == "DEFAULT"
    assert legacy.dbs["DEFAULT"]["fullname"] == "/tmp/legacy.db"
    assert modern.resolve_db_role("optimizer") == "OPTIMIZER"
    assert modern.dbs["OPTIMIZER"]["style"] == "SQLite"


def test_sqlite_table_listing_and_dump(tmp_path):
    db_path = tmp_path / "test.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT, blob_value BLOB)")
        conn.execute("INSERT INTO sample (name, blob_value) VALUES (?, ?)", ("abc", b'\x01\x02'))

    router = DBHandlerRouter(name="DB", dbs={"AUTH": {"fullname": str(db_path), "style": "SQLite"}})

    assert router.list_db_tables("AUTH") == ["sample"]
    dumped = router.dump_db_table("AUTH", "sample")

    assert dumped["db_role"] == "AUTH"
    assert dumped["columns"] == ["id", "name", "blob_value"]
    assert dumped["rows"] == [{"id": 1, "name": "abc", "blob_value": "0102"}]
    assert dumped["row_count"] == 1


def test_dump_validates_table_name_against_metadata(tmp_path):
    db_path = tmp_path / "test.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")

    router = DBHandlerRouter(name="DB", dbs={"AUTH": {"fullname": str(db_path), "style": "SQLite"}})

    with pytest.raises(HTTPException) as exc_info:
        router.dump_db_table("AUTH", "missing")

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


def test_initialize_configured_dbs_is_explicit_only(tmp_path):
    db_path = tmp_path / "explicit.db"
    router = DBHandlerRouter(
        name="DB",
        dbs={
            "AUTH": {
                "fullname": str(db_path),
                "style": "SQLite",
                "ensure_file": True,
            }
        },
    )

    assert not db_path.exists()

    router.reinit()
    assert not db_path.exists()

    result = router.initialize_configured_dbs()

    assert db_path.exists()
    assert result["AUTH"].ensured_file is True
    assert router.db_init_errors == {}
