import importlib

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sqlbase_user_shmc import (
    AuthProject,
    AuthUser,
    AuthUserData,
    AuthUserProjectAccess,
    AuthUserProjectAccessData,
    BaseUserSHMC,
    __version__,
    active_project_codes,
    auth_user_project_access_rows_to_data,
    auth_user_project_access_to_data,
    auth_user_to_data,
    get_schema_provider,
    user_has_project_access,
)


def test_import_and_table_names():
    assert AuthUser.__tablename__ == "auth_users"
    assert AuthProject.__tablename__ == "auth_projects"
    assert AuthUserProjectAccess.__tablename__ == "auth_user_project_access"
    assert AuthUserData.__name__ == "AuthUserData"
    assert AuthUserProjectAccessData.__name__ == "AuthUserProjectAccessData"
    assert callable(get_schema_provider)


def test_dynamic_schema_provider_import_string():
    module_name, function_name = "sqlbase_user_shmc:get_schema_provider".split(":")
    provider_func = getattr(importlib.import_module(module_name), function_name)

    assert provider_func is get_schema_provider


def test_schema_provider_shape():
    provider = get_schema_provider()

    assert provider["role"] == "AUTH"
    assert provider["name"] == "sqlbase_user_shmc"
    assert provider["version"] == __version__
    assert provider["metadata"] == [BaseUserSHMC.metadata]
    assert provider["bases"] == [BaseUserSHMC]
    assert AuthUser in provider["tables"]
    assert AuthProject in provider["tables"]
    assert AuthUserProjectAccess in provider["tables"]
    assert provider["managed_tables"] == [
        AuthUser.__tablename__,
        AuthProject.__tablename__,
        AuthUserProjectAccess.__tablename__,
    ]


def test_schema_provider_metadata_creates_expected_tables():
    provider = get_schema_provider()
    engine = create_engine("sqlite:///:memory:")

    for metadata in provider["metadata"]:
        metadata.create_all(engine)

    tables = set(inspect(engine).get_table_names())

    assert AuthUser.__tablename__ in tables
    assert AuthProject.__tablename__ in tables
    assert AuthUserProjectAccess.__tablename__ in tables


def test_create_persist_query_and_to_dict():
    engine = create_engine("sqlite:///:memory:")
    BaseUserSHMC.metadata.create_all(engine)

    with Session(engine) as session:
        user = AuthUser(uuid="abc", auth_code=4, is_anonymous=True)
        project = AuthProject(code="KARAK", name="Karak")
        access = AuthUserProjectAccess(user_uuid="abc", project_code="KARAK", enabled=True)
        session.add_all([user, project, access])
        session.commit()

    with Session(engine) as session:
        user = session.get(AuthUser, "abc")
        project = session.get(AuthProject, "KARAK")
        rows = session.query(AuthUserProjectAccess).all()
        access_data = auth_user_project_access_rows_to_data(rows)

        assert user.to_dict()["uuid"] == "abc"
        assert user.public_claims_base() == {
            "sub": "abc",
            "email": None,
            "username": None,
            "auth_code": 4,
            "anonymous": True,
        }
        assert project.to_dict()["name"] == "Karak"
        assert rows[0].to_dict()["project_code"] == "KARAK"
        assert user_has_project_access(access_data, "KARAK") is True
        assert active_project_codes(access_data) == ["KARAK"]


def test_auth_user_to_data_returns_plain_runtime_shape():
    user = AuthUser(
        uuid="abc",
        email="abc@example.com",
        username="abc_user",
        psswd_hsh="hash",
        auth_code=4,
        is_anonymous=False,
        disabled=True,
    )

    data = auth_user_to_data(user)

    assert data == AuthUserData(
        uuid="abc",
        email="abc@example.com",
        username="abc_user",
        psswd_hsh="hash",
        auth_code=4,
        is_anonymous=False,
        disabled=True,
    )


def test_auth_user_project_access_to_data_returns_plain_runtime_shape():
    row = AuthUserProjectAccess(
        user_uuid="abc",
        project_code="KARAK",
        enabled=True,
        granted_by_uuid="admin",
    )

    data = auth_user_project_access_to_data(row)

    assert data == AuthUserProjectAccessData(
        user_uuid="abc",
        project_code="KARAK",
        enabled=True,
        granted_by_uuid="admin",
    )


def test_unique_user_project_access_constraint():
    engine = create_engine("sqlite:///:memory:")
    BaseUserSHMC.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all([
            AuthUser(uuid="abc"),
            AuthProject(code="KARAK", name="Karak"),
            AuthUserProjectAccess(user_uuid="abc", project_code="KARAK"),
            AuthUserProjectAccess(user_uuid="abc", project_code="KARAK"),
        ])

        with pytest.raises(IntegrityError):
            session.commit()


def test_auth_user_uuid_immutability_guard():
    engine = create_engine("sqlite:///:memory:")
    BaseUserSHMC.metadata.create_all(engine)

    with Session(engine) as session:
        user = AuthUser(uuid="abc")
        session.add(user)
        session.commit()

        user.uuid = "def"
        with pytest.raises(ValueError, match="AuthUser.uuid is immutable"):
            session.commit()


def test_auth_project_code_immutability_guard():
    engine = create_engine("sqlite:///:memory:")
    BaseUserSHMC.metadata.create_all(engine)

    with Session(engine) as session:
        project = AuthProject(code="KARAK", name="Karak")
        session.add(project)
        session.commit()

        project.code = "OPTIMIZER"
        with pytest.raises(ValueError, match="AuthProject.code is immutable"):
            session.commit()


def test_required_non_empty_constructor_values():
    with pytest.raises(ValueError):
        AuthUser(uuid="")
    with pytest.raises(ValueError):
        AuthProject(code="", name="Karak")
    with pytest.raises(ValueError):
        AuthProject(code="KARAK", name="")
    with pytest.raises(ValueError):
        AuthUserProjectAccess(user_uuid="", project_code="KARAK")
    with pytest.raises(ValueError):
        AuthUserProjectAccess(user_uuid="abc", project_code="")
