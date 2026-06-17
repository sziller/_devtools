"""SQLAlchemy ORM models for SHMC authentication database state.

Migration direction from the older UserAnonym model:
- UserAnonym.email -> AuthUser.email
- UserAnonym.psswd_hsh -> AuthUser.psswd_hsh
- UserAnonym.auth_code -> AuthUser.auth_code
- UserAnonym.uuid -> AuthUser.uuid
- wallet fields -> future wallet package, intentionally not modeled here
- kyc_status -> intentionally omitted
- referral fields -> future referral package, intentionally not modeled here
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, UniqueConstraint, event
from sqlalchemy import inspect as sqla_inspect
from sqlalchemy.orm import Mapped, mapped_column, object_mapper

from .bases import BaseUserSHMC, Str32, Str64, Str128, Str320


def _mapped_column_values(instance: object) -> dict[str, object]:
    """Return mapped column values for an ORM instance."""
    mapper = object_mapper(instance)
    return {prop.key: getattr(instance, prop.key) for prop in mapper.column_attrs}


class AuthUser(BaseUserSHMC):
    """Authentication subject/account for the SHMC auth database."""

    __tablename__ = "auth_users"

    uuid: Mapped[Str32] = mapped_column(primary_key=True)
    email: Mapped[Optional[Str320]] = mapped_column(nullable=True, unique=True, index=True)
    username: Mapped[Optional[Str128]] = mapped_column(nullable=True, unique=True, index=True)
    psswd_hsh: Mapped[Optional[str]] = mapped_column(nullable=True)
    auth_code: Mapped[int] = mapped_column(nullable=False, default=0)
    is_anonymous: Mapped[bool] = mapped_column(nullable=False, default=True)
    disabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    conf_tkn_hash: Mapped[Optional[Str64]] = mapped_column(nullable=True, index=True)
    created_ts: Mapped[float] = mapped_column(nullable=False, default=0.0)
    updated_ts: Mapped[float] = mapped_column(nullable=False, default=0.0)

    __table_args__ = (
        CheckConstraint("auth_code >= 0", name="ck_auth_users_auth_code_non_negative"),
        CheckConstraint("uuid <> ''", name="ck_auth_users_uuid_non_empty"),
    )

    def __init__(
        self,
        uuid: str,
        email: Optional[str] = None,
        username: Optional[str] = None,
        psswd_hsh: Optional[str] = None,
        auth_code: int = 0,
        is_anonymous: bool = True,
        disabled: bool = False,
        conf_tkn_hash: Optional[str] = None,
        created_ts: float = 0.0,
        updated_ts: float = 0.0,
        **kwargs,
    ):
        if not uuid:
            raise ValueError("AuthUser.uuid must be set and non-empty.")

        super().__init__()

        self.uuid = uuid
        self.email = email
        self.username = username
        self.psswd_hsh = psswd_hsh
        self.auth_code = auth_code
        self.is_anonymous = is_anonymous
        self.disabled = disabled
        self.conf_tkn_hash = conf_tkn_hash
        self.created_ts = created_ts
        self.updated_ts = updated_ts

    def to_dict(self) -> dict:
        """Return instance as dictionary."""
        return _mapped_column_values(self)

    @classmethod
    def construct(cls, d_in: dict):
        """Instantiate object from dictionary."""
        return cls(**d_in)

    def public_claims_base(self) -> dict:
        """Return JWT-friendly user claims without project access or token metadata."""
        return {
            "sub": self.uuid,
            "email": self.email,
            "username": self.username,
            "auth_code": self.auth_code,
            "anonymous": self.is_anonymous,
        }

    def __repr__(self):
        return f"AuthUser(uuid={self.uuid!r}, email={self.email!r}, auth_code={self.auth_code})"


class AuthProject(BaseUserSHMC):
    """Catalog entry for a project protected by SHMC auth."""

    __tablename__ = "auth_projects"

    code: Mapped[Str64] = mapped_column(primary_key=True)
    name: Mapped[Str128] = mapped_column(nullable=False)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_ts: Mapped[float] = mapped_column(nullable=False, default=0.0)
    updated_ts: Mapped[float] = mapped_column(nullable=False, default=0.0)

    __table_args__ = (
        CheckConstraint("code <> ''", name="ck_auth_projects_code_non_empty"),
        CheckConstraint("name <> ''", name="ck_auth_projects_name_non_empty"),
    )

    def __init__(
        self,
        code: str,
        name: str,
        description: Optional[str] = None,
        enabled: bool = True,
        created_ts: float = 0.0,
        updated_ts: float = 0.0,
        **kwargs,
    ):
        if not code:
            raise ValueError("AuthProject.code must be set and non-empty.")
        if not name:
            raise ValueError("AuthProject.name must be set and non-empty.")

        super().__init__()

        self.code = code
        self.name = name
        self.description = description
        self.enabled = enabled
        self.created_ts = created_ts
        self.updated_ts = updated_ts

    def to_dict(self) -> dict:
        """Return instance as dictionary."""
        return _mapped_column_values(self)

    @classmethod
    def construct(cls, d_in: dict):
        """Instantiate object from dictionary."""
        return cls(**d_in)

    def __repr__(self):
        return f"AuthProject(code={self.code!r}, name={self.name!r}, enabled={self.enabled})"


class AuthUserProjectAccess(BaseUserSHMC):
    """Binary access relation between an auth user and a project."""

    __tablename__ = "auth_user_project_access"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_uuid: Mapped[Str32] = mapped_column(nullable=False, index=True)
    project_code: Mapped[Str64] = mapped_column(nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    granted_by_uuid: Mapped[Optional[Str32]] = mapped_column(nullable=True)
    created_ts: Mapped[float] = mapped_column(nullable=False, default=0.0)
    updated_ts: Mapped[float] = mapped_column(nullable=False, default=0.0)

    __table_args__ = (
        ForeignKeyConstraint(("user_uuid",), ("auth_users.uuid",)),
        ForeignKeyConstraint(("project_code",), ("auth_projects.code",)),
        UniqueConstraint("user_uuid", "project_code", name="uq_auth_user_project_access"),
        CheckConstraint("user_uuid <> ''", name="ck_auth_user_project_access_user_uuid_non_empty"),
        CheckConstraint("project_code <> ''", name="ck_auth_user_project_access_project_code_non_empty"),
        Index("ix_auth_user_project_access_user_enabled", "user_uuid", "enabled"),
        Index("ix_auth_user_project_access_project_enabled", "project_code", "enabled"),
    )

    def __init__(
        self,
        user_uuid: str,
        project_code: str,
        enabled: bool = True,
        granted_by_uuid: Optional[str] = None,
        created_ts: float = 0.0,
        updated_ts: float = 0.0,
        **kwargs,
    ):
        if not user_uuid:
            raise ValueError("AuthUserProjectAccess.user_uuid must be set and non-empty.")
        if not project_code:
            raise ValueError("AuthUserProjectAccess.project_code must be set and non-empty.")

        super().__init__()

        self.user_uuid = user_uuid
        self.project_code = project_code
        self.enabled = enabled
        self.granted_by_uuid = granted_by_uuid
        self.created_ts = created_ts
        self.updated_ts = updated_ts

    def to_dict(self) -> dict:
        """Return instance as dictionary."""
        return _mapped_column_values(self)

    @classmethod
    def construct(cls, d_in: dict):
        """Instantiate object from dictionary."""
        return cls(**d_in)

    def __repr__(self):
        return (
            "AuthUserProjectAccess("
            f"user_uuid={self.user_uuid!r}, project_code={self.project_code!r}, enabled={self.enabled}"
            ")"
        )


@event.listens_for(AuthUser, "before_update", propagate=True)
def _guard_auth_user_immutable_fields(mapper, connection, target: AuthUser):
    insp = sqla_inspect(target)

    if "uuid" in insp.attrs and insp.attrs.uuid.history.has_changes():
        old = insp.attrs.uuid.history.deleted
        new = insp.attrs.uuid.history.added

        if old and old[0] and new and new[0] != old[0]:
            raise ValueError("AuthUser.uuid is immutable.")


@event.listens_for(AuthProject, "before_update", propagate=True)
def _guard_auth_project_immutable_fields(mapper, connection, target: AuthProject):
    insp = sqla_inspect(target)

    if "code" in insp.attrs and insp.attrs.code.history.has_changes():
        old = insp.attrs.code.history.deleted
        new = insp.attrs.code.history.added

        if old and old[0] and new and new[0] != old[0]:
            raise ValueError("AuthProject.code is immutable.")
