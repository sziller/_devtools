"""Durable Firebase installation ownership in the Auth database."""

import time

from sqlalchemy import (
    Boolean, CheckConstraint, Float, ForeignKey, Index, Integer, String,
    UniqueConstraint, true,
)
from sqlalchemy.orm import Mapped, mapped_column, validates

from sql_bases.sqlbase_user_anonym.sqlbase_user_anonym import Base


class PushRegistration(Base):
    """One current row per FID, including inactive registrations.

    Ownership may change. Registration services explicitly refresh
    last_registered_at; unrelated updates must not change either timestamp.
    """

    __tablename__ = "push_registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_uuid: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("useranonyms.uuid", name="fk_push_registrations_user_uuid",
                   ondelete="CASCADE"),
        nullable=False,
    )
    firebase_installation_id: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[float] = mapped_column(Float, nullable=False, default=time.time)
    last_registered_at: Mapped[float] = mapped_column(Float, nullable=False, default=time.time)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true(),
    )

    __table_args__ = (
        UniqueConstraint("firebase_installation_id",
                         name="uq_push_registrations_firebase_installation_id"),
        CheckConstraint("length(trim(firebase_installation_id)) > 0",
                        name="ck_push_registrations_fid_nonempty"),
        CheckConstraint("platform IN ('android', 'ios')",
                        name="ck_push_registrations_platform"),
        Index("ix_push_registrations_user_uuid_active", "user_uuid", "active"),
    )

    @validates("firebase_installation_id")
    def _validate_fid(self, key, value):
        # Validate without transforming opaque infrastructure data.
        if isinstance(value, str) and not value.strip():
            raise ValueError("firebase_installation_id must not be blank")
        return value
