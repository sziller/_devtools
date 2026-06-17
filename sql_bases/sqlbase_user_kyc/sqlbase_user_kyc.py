"""=====================================================================================================================
SQLAlchemy powered DB Bases: test, and production code.

This module defines the SQLAlchemy ORM base and a dedicated KYC side-table
used by the authentication/compliance layer.

Design goals
------------
- Keep KYC-specific provider/compliance data out of UserAnonym
- Link to the core user model indirectly via `uuid`
- Avoid hard coupling to UserAnonym through explicit FK / relationship
- Keep the table optional from the core business logic point of view
- Support provider-originated KYC lifecycle tracking and audit metadata

Important architecture note
---------------------------
`UserKYC` is the authoritative KYC detail store.

The application-facing, distilled KYC projection may still be mirrored into
`UserAnonym.kyc_status`, but that field is intentionally not modeled here.

This table is designed as a sidecar:
- no explicit foreign key
- no ORM relationship
- no mandatory join requirement

This allows the broader business logic to remain minimally coupled to KYC.
================================================================================================== by Sziller ==="""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import (
    String,
    Float,
    Boolean,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# -----------------------------------------------------------------------------
# Declarative base
# -----------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Declarative ORM base."""
    pass


# -----------------------------------------------------------------------------
# KYC detail side-table
# -----------------------------------------------------------------------------

class UserKYC(Base):
    """=== Classname: UserKYC(Base) =================================================================

    Dedicated KYC/compliance side-table for users.

    Design intent
    -------------
    - Keep KYC-specific provider/compliance data out of UserAnonym
    - Link to the core user model indirectly via `uuid`
    - Avoid hard coupling to UserAnonym through explicit FK / relationship
    - Serve as the authoritative KYC detail store, while `UserAnonym.kyc_status`
      remains the distilled application-facing projection

    Notes
    -----
    - This table is optional from the core business logic point of view.
    - Missing table must not block unrelated user/auth flows.
    - Provider-specific semantics are allowed here.
    ============================================================================================== by Sziller ==="""

    __tablename__ = "userkyc"

    __table_args__ = (
        Index("ix_userkyc_uuid_provider", "uuid", "kyc_provider"),
        UniqueConstraint(
            "kyc_provider",
            "provider_applicant_id",
            name="uq_userkyc_provider_applicant_id",
        ),
    )

    # -------------------------------------------------------------------------
    # Primary key
    # -------------------------------------------------------------------------

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # -------------------------------------------------------------------------
    # Core linkage
    # -------------------------------------------------------------------------

    uuid: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # -------------------------------------------------------------------------
    # Provider / integration identity
    # -------------------------------------------------------------------------

    kyc_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="sumsub")
    provider_user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    provider_applicant_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)

    # -------------------------------------------------------------------------
    # Requested / achieved KYC level
    # -------------------------------------------------------------------------

    kyc_level_requested: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    kyc_level_achieved: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # -------------------------------------------------------------------------
    # Internal KYC state inside KYC subsystem
    # -------------------------------------------------------------------------

    kyc_state_internal: Mapped[str] = mapped_column(String(32), nullable=False, default="none", index=True)

    # -------------------------------------------------------------------------
    # Raw provider review / status details
    # -------------------------------------------------------------------------

    provider_status_raw: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    provider_review_answer: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    provider_review_reject_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    provider_review_reject_labels: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------

    started_at: Mapped[Optional[float]] = mapped_column(nullable=True)
    reviewed_at: Mapped[Optional[float]] = mapped_column(nullable=True)
    last_provider_event_at: Mapped[Optional[float]] = mapped_column(nullable=True)
    timestamp: Mapped[float] = mapped_column(nullable=False, default=0.0)

    # -------------------------------------------------------------------------
    # Raw payload / audit reference
    # -------------------------------------------------------------------------

    raw_payload_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw_payload_last: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # -------------------------------------------------------------------------
    # Operational flags
    # -------------------------------------------------------------------------

    disabled: Mapped[bool] = mapped_column(nullable=False, default=False)

    # -------------------------------------------------------------------------
    # Convenience helpers
    # -------------------------------------------------------------------------

    def normalize(self) -> None:
        """Normalize instance values after construction or provider updates."""
        if not self.uuid:
            raise ValueError("UserKYC.uuid must be set and non-empty.")

        if not self.kyc_provider:
            self.kyc_provider = "sumsub"

        if not self.kyc_state_internal:
            self.kyc_state_internal = "none"

    def to_dict(self) -> dict[str, Any]:
        """Return instance as dictionary."""
        return {
            "id": self.id,
            "uuid": self.uuid,
            "kyc_provider": self.kyc_provider,
            "provider_user_id": self.provider_user_id,
            "provider_applicant_id": self.provider_applicant_id,
            "kyc_level_requested": self.kyc_level_requested,
            "kyc_level_achieved": self.kyc_level_achieved,
            "kyc_state_internal": self.kyc_state_internal,
            "provider_status_raw": self.provider_status_raw,
            "provider_review_answer": self.provider_review_answer,
            "provider_review_reject_type": self.provider_review_reject_type,
            "provider_review_reject_labels": self.provider_review_reject_labels,
            "started_at": self.started_at,
            "reviewed_at": self.reviewed_at,
            "last_provider_event_at": self.last_provider_event_at,
            "timestamp": self.timestamp,
            "raw_payload_ref": self.raw_payload_ref,
            "raw_payload_last": self.raw_payload_last,
            "disabled": self.disabled,
        }

    @classmethod
    def construct(cls, d_in: dict[str, Any]) -> "UserKYC":
        """Instantiate object from dictionary."""
        obj = cls(**d_in)
        obj.normalize()
        return obj

    def __repr__(self) -> str:
        return (
            f"UserKYC(id={self.id}, uuid={self.uuid}, provider={self.kyc_provider}, "
            f"state={self.kyc_state_internal}, level={self.kyc_level_achieved})"
        )
