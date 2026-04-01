"""=== Module: sqlbase_ap_measurement.py ======================================================
Canonical measurement model for the Aquaponics Engine.

This module stores immutable measurement facts observed from the physical world.

Design decisions:
- Physical measurements are append-only facts.
- Human-readable time strings are NOT stored.
- Absolute time is stored as Unix timestamp.
- Optional loop_id supports replay/debug correlation with Engine loops.
- SQLAlchemy 2 style mappings are used.
- Pydantic 2 compatible schemas are included.

This table is intended to support:
- digital twin reconstruction,
- debugging,
- replay assistance,
- sensor history analysis.

IMPORTANT:
- This model stores observations only.
- It does NOT store commands, policy, or execution events.
- It should be written by the Engine only.

================================================================================ by Sziller ==="""

from __future__ import annotations

import time
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# -------------------------------------------------------------------------------------------------
# SQLAlchemy base
# -------------------------------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Shared SQLAlchemy declarative base."""
    pass


# -------------------------------------------------------------------------------------------------
# SQLAlchemy model
# -------------------------------------------------------------------------------------------------


class Measurement(Base):
    """=== Classname: Measurement ================================================================
    Immutable measurement fact recorded by the Engine.

    Semantic meaning:
    - one row == one observed value
    - timestamp == absolute wall-clock time (Unix seconds)
    - loop_id == optional logical Engine loop identifier
    - source == optional sensor/device/source identifier

    Notes:
    - No human-readable time string is stored; derive it when needed.
    - Measurements should not be updated in-place in normal operation.
    - This table is append-only by design philosophy.

    =============================================================================================="""

    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Monotonic database identifier.",
    )

    mea_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Measurement type, e.g. 'temperature', 'humidity', 'water_level'.",
    )

    mea_loc: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        doc="Logical or physical measurement location, e.g. 'tank_1', 'room_main'.",
    )

    mea_val: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Observed numerical value.",
    )

    mea_dim: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="Measurement unit, e.g. 'C', '%', 'cm', 'ppm'.",
    )

    timestamp: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        default=lambda: int(time.time()),
        doc="Absolute Unix timestamp in seconds.",
    )

    loop_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc="Optional Engine loop identifier for replay/debug correlation.",
    )

    source: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        doc="Optional sensor/source identifier.",
    )

    def return_as_dict(self) -> dict[str, Any]:
        """Return SQLAlchemy row as a plain dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def construct(cls, d_in: dict[str, Any]) -> "Measurement":
        """Instantiate a Measurement from a dictionary."""
        return cls(**d_in)

    def __repr__(self) -> str:
        return (
            f"Measurement("
            f"id={self.id}, "
            f"type='{self.mea_type}', "
            f"loc='{self.mea_loc}', "
            f"value={self.mea_val}, "
            f"dim='{self.mea_dim}', "
            f"timestamp={self.timestamp}, "
            f"loop_id={self.loop_id}, "
            f"source={self.source!r})"
        )


# -------------------------------------------------------------------------------------------------
# Pydantic 2 schemas
# -------------------------------------------------------------------------------------------------


class MeasurementBaseSchema(BaseModel):
    """Shared Pydantic base schema for measurement data."""

    mea_type: str = Field(..., min_length=1, max_length=64)
    mea_loc: str = Field(..., min_length=1, max_length=128)
    mea_val: float
    mea_dim: str = Field(..., min_length=1, max_length=32)
    timestamp: int = Field(
        default_factory=lambda: int(time.time()),
        description="Absolute Unix timestamp in seconds.",
    )
    loop_id: int | None = Field(
        default=None,
        description="Optional Engine loop identifier.",
    )
    source: str | None = Field(
        default=None,
        max_length=128,
        description="Optional sensor/source identifier.",
    )

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: int) -> int:
        """Ensure timestamp is a sensible Unix-second integer."""
        if v <= 0:
            raise ValueError("timestamp must be a positive Unix timestamp.")
        return v

    @field_validator("mea_type", "mea_loc", "mea_dim")
    @classmethod
    def strip_nonempty_strings(cls, v: str) -> str:
        """Normalize and validate required string fields."""
        v = v.strip()
        if not v:
            raise ValueError("field must not be empty.")
        return v

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class MeasurementCreateSchema(MeasurementBaseSchema):
    """Schema for creating a new measurement row."""
    pass


class MeasurementReadSchema(MeasurementBaseSchema):
    """Schema for reading a measurement row from SQLAlchemy."""

    id: int

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class MeasurementFilterSchema(BaseModel):
    """Optional helper schema for filtering measurement queries."""

    mea_type: str | None = None
    mea_loc: str | None = None
    source: str | None = None
    timestamp_from: int | None = None
    timestamp_to: int | None = None
    loop_id_from: int | None = None
    loop_id_to: int | None = None
    limit: int = Field(default=100, ge=1, le=10000)

    @field_validator("timestamp_from", "timestamp_to", "loop_id_from", "loop_id_to")
    @classmethod
    def validate_nonnegative_optional_ints(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("filter values must be non-negative.")
        return v

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )
