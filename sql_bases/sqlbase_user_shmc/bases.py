"""Dedicated SQLAlchemy base for SHMC authentication models."""

from __future__ import annotations

from typing import Annotated

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase

Str32 = Annotated[str, "str_32"]
Str64 = Annotated[str, "str_64"]
Str128 = Annotated[str, "str_128"]
Str320 = Annotated[str, "str_320"]


class BaseUserSHMC(DeclarativeBase):
    """Declarative base for SHMC authentication models."""

    type_annotation_map = {
        Str32: String(32),
        Str64: String(64),
        Str128: String(128),
        Str320: String(320),
    }
