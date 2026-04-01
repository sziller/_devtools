"""=== Module: sqlbase_ap_command.py ============================================================
Canonical command log model for the Aquaponics Engine.

This module stores immutable command intents.

Design decisions:
- Append-only command log
- No status mutation
- Commands represent intent, not execution
- Absolute timestamps only
- Supports scheduling, replay, and idempotency

================================================================================ by Sziller ==="""

from __future__ import annotations

import time
from typing import Any, Optional


from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Integer, String, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# -------------------------------------------------------------------------------------------------
# SQLAlchemy base
# -------------------------------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# -------------------------------------------------------------------------------------------------
# SQLAlchemy model
# -------------------------------------------------------------------------------------------------

class Command(Base):
    """=== Classname: Command ================================================================
    Immutable command intent.
    One row = one decision to act.
    This table is append-only.
    ========================================================================================"""

    __tablename__ = "commands"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    cmd_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Command type (e.g. waterstream, feeding, schedule_one_shot)"
    )

    cmd_payload: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        doc="Optional structured payload (parameters)"
    )

    timestamp: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        default=lambda: int(time.time()),
        doc="Absolute creation timestamp"
    )

    loop_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc="Engine loop id at creation"
    )

    origin_type: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="Origin: policy_schedule | one_shot | manual | system"
    )

    origin_command_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc="Link to originating command (e.g. schedule_one_shot)"
    )

    schedule_timestamp: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc="Absolute timestamp of scheduled slot (for idempotency)"
    )

    def return_as_dict(self) -> dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def construct(cls, d_in: dict[str, Any]) -> "Command":
        return cls(**d_in)

    def __repr__(self) -> str:
        return (
            f"Command("
            f"id={self.id}, "
            f"type='{self.cmd_type}', "
            f"timestamp={self.timestamp}, "
            f"origin={self.origin_type}, "
            f"schedule_ts={self.schedule_timestamp})"
        )


# -------------------------------------------------------------------------------------------------
# Pydantic 2 schemas
# -------------------------------------------------------------------------------------------------

class CommandBaseSchema(BaseModel):
    cmd_type: str = Field(..., min_length=1, max_length=64)

    cmd_payload: dict | None = None

    timestamp: int = Field(
        default_factory=lambda: int(time.time())
    )

    loop_id: int | None = None

    origin_type: str | None = Field(
        default=None,
        description="policy_schedule | one_shot | manual | system"
    )

    origin_command_id: int | None = None

    schedule_timestamp: int | None = Field(
        default=None,
        description="Absolute timestamp of scheduled slot"
    )

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("timestamp must be positive")
        return v

    @field_validator("cmd_type")
    @classmethod
    def normalize_cmd_type(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("cmd_type must not be empty")
        return v

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )


class CommandCreateSchema(CommandBaseSchema):
    pass


class CommandReadSchema(CommandBaseSchema):
    id: int

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )


class CommandFilterSchema(BaseModel):
    cmd_type: str | None = None
    origin_type: str | None = None
    timestamp_from: int | None = None
    timestamp_to: int | None = None
    loop_id_from: int | None = None
    loop_id_to: int | None = None
    limit: int = Field(default=100, ge=1, le=10000)

    model_config = ConfigDict(
        extra="forbid"
    )
