"""Plain typed read models for SHMC authentication data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from .models import AuthUser, AuthUserProjectAccess


def _str_value(value: object) -> str:
    return cast(str, value)


def _optional_str_value(value: object) -> str | None:
    return cast(str | None, value)


def _int_value(value: object) -> int:
    return cast(int, value)


def _bool_value(value: object) -> bool:
    return cast(bool, value)


@dataclass(frozen=True)
class AuthUserData:
    """Application-facing auth user shape outside the DB boundary."""

    uuid: str
    email: str | None
    username: str | None
    psswd_hsh: str | None
    auth_code: int
    is_anonymous: bool
    disabled: bool


@dataclass(frozen=True)
class AuthUserProjectAccessData:
    """Application-facing project access shape outside the DB boundary."""

    user_uuid: str
    project_code: str
    enabled: bool
    granted_by_uuid: str | None


def auth_user_to_data(user: AuthUser) -> AuthUserData:
    """Convert an AuthUser ORM row to plain application data."""
    return AuthUserData(
        uuid=_str_value(user.uuid),
        email=_optional_str_value(user.email),
        username=_optional_str_value(user.username),
        psswd_hsh=_optional_str_value(user.psswd_hsh),
        auth_code=_int_value(user.auth_code),
        is_anonymous=_bool_value(user.is_anonymous),
        disabled=_bool_value(user.disabled),
    )


def auth_user_project_access_to_data(
    row: AuthUserProjectAccess,
) -> AuthUserProjectAccessData:
    """Convert an AuthUserProjectAccess ORM row to plain application data."""
    return AuthUserProjectAccessData(
        user_uuid=_str_value(row.user_uuid),
        project_code=_str_value(row.project_code),
        enabled=_bool_value(row.enabled),
        granted_by_uuid=_optional_str_value(row.granted_by_uuid),
    )


def auth_user_project_access_rows_to_data(
    rows: list[AuthUserProjectAccess],
) -> list[AuthUserProjectAccessData]:
    """Convert project access ORM rows to plain application data."""
    return [auth_user_project_access_to_data(row) for row in rows]
