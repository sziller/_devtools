"""Pure helper functions for SHMC auth read models."""

from __future__ import annotations

from .data import AuthUserProjectAccessData


def user_has_project_access(
    access_rows: list[AuthUserProjectAccessData],
    project_code: str,
) -> bool:
    """Return True when an enabled access row exists for project_code."""
    return any(row.project_code == project_code and row.enabled for row in access_rows)


def active_project_codes(access_rows: list[AuthUserProjectAccessData]) -> list[str]:
    """Return sorted project codes from enabled access rows."""
    return sorted(row.project_code for row in access_rows if row.enabled)
