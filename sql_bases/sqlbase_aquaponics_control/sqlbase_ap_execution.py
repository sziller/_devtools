"""=== Module: sqlbase_ap_execution.py =========================================================
Execution log model for Aquaponics Engine.

Stores append-only records of execution attempts and outcomes.

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

class Execution(Base):
    """=== Classname: Execution ===============================================================

    Immutable execution event.

    One row = one execution-related event.

    Types:
    - attempt
    - complete
    - confirmed

    ==========================================================================================="""

    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    command_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        doc="Reference to command being executed"
    )

    exec_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="attempt | complete | confirmed"
    )

    timestamp: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        default=lambda: int(time.time())
    )

    loop_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True
    )

    exec_payload: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        doc="Optional execution data (duration, error, sensor confirmation, etc.)"
    )

    def return_as_dict(self) -> dict[str, Any]:
        return {
            attr.key: getattr(self, attr.key)
            for attr in list(self.__mapper__.column_attrs)
        }

    @classmethod
    def construct(cls, d_in: dict[str, Any]) -> "Execution":
        return cls(**d_in)

    def __repr__(self) -> str:
        return (
            f"Execution("
            f"id={self.id}, "
            f"cmd_id={self.command_id}, "
            f"type='{self.exec_type}', "
            f"timestamp={self.timestamp})"
        )


# -------------------------------------------------------------------------------------------------
# Pydantic 2 schemas
# -------------------------------------------------------------------------------------------------

class ExecutionBaseSchema(BaseModel):
    command_id: int

    exec_type: str = Field(
        ...,
        description="attempt | complete | confirmed"
    )

    timestamp: int = Field(
        default_factory=lambda: int(time.time())
    )

    loop_id: int | None = None

    exec_payload: dict | None = None

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("timestamp must be positive")
        return v

    @field_validator("exec_type")
    @classmethod
    def validate_exec_type(cls, v: str) -> str:
        v = v.strip()
        allowed = {"attempt", "complete", "confirmed"}
        if v not in allowed:
            raise ValueError(f"exec_type must be one of {allowed}")
        return v

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )


class ExecutionCreateSchema(ExecutionBaseSchema):
    pass


class ExecutionReadSchema(ExecutionBaseSchema):
    id: int

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )


class ExecutionFilterSchema(BaseModel):
    command_id: int | None = None
    exec_type: str | None = None
    timestamp_from: int | None = None
    timestamp_to: int | None = None
    loop_id_from: int | None = None
    loop_id_to: int | None = None
    limit: int = Field(default=100, ge=1, le=10000)

    model_config = ConfigDict(
        extra="forbid"
    )
