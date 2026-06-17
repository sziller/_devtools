"""SHMC authentication SQLAlchemy base package."""

from .bases import BaseUserSHMC
from .data import (
    AuthUserData,
    AuthUserProjectAccessData,
    auth_user_project_access_rows_to_data,
    auth_user_project_access_to_data,
    auth_user_to_data,
)
from .helpers import active_project_codes, user_has_project_access
from .models import AuthProject, AuthUser, AuthUserProjectAccess

__version__ = "0.2.7"


def get_schema_provider() -> dict:
    """Return SHMC schema metadata for dynamic DB initialization."""
    return {
        "role": "AUTH",
        "name": "sqlbase_user_shmc",
        "version": __version__,
        "description": "SHMC authentication users, projects, and project-access schema.",
        "metadata": [BaseUserSHMC.metadata],
        "bases": [BaseUserSHMC],
        "tables": [
            AuthUser,
            AuthProject,
            AuthUserProjectAccess,
        ],
        "managed_tables": [
            AuthUser.__tablename__,
            AuthProject.__tablename__,
            AuthUserProjectAccess.__tablename__,
        ],
    }


__all__ = [
    "BaseUserSHMC",
    "AuthUser",
    "AuthUserData",
    "AuthProject",
    "AuthUserProjectAccess",
    "AuthUserProjectAccessData",
    "auth_user_to_data",
    "auth_user_project_access_to_data",
    "auth_user_project_access_rows_to_data",
    "user_has_project_access",
    "active_project_codes",
    "__version__",
    "get_schema_provider",
]
