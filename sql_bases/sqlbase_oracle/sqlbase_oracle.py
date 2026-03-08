"""
SQLAlchemy powered DB Base for Oracles used by DLCPlaza.

This table stores reference definitions for Oracle providers used by the
DLCPlaza engine. Oracle entries are static configuration data and are stored
in the `.Reference.db` database.

Compatibility
-------------
The schema is designed to work identically on:

- SQLite (development)
- PostgreSQL (production)

JSON columns automatically map to JSONB when PostgreSQL is used.

Oracles are referenced across the system by their canonical identifier
`oracle_name`, which serves as the primary key.

by Sziller
"""

from __future__ import annotations
import logging

from sqlalchemy import (
    Column,
    String,
    Boolean,
    JSON,
    DateTime,
    func
)

from sqlalchemy.orm import declarative_base

Base = declarative_base()

lg = logging.getLogger(__name__)


class Oracle(Base):
    """
    Oracle provider definition used by DLCPlaza.

    Each row represents a single oracle provider instance.

    This table is considered **reference configuration** and is not
    modified by public API endpoints.

    Primary Key
    -----------
    oracle_name
        Canonical identifier used by the engine and API.

    Example values
        oracle_dlcp
        oracle_dfx

    Fields
    ------
    oracle_name
        Canonical oracle identifier used throughout the system.

    provider
        Human readable provider name.

    endpoint
        Base HTTP endpoint used to query the oracle.

    supported_symbols
        JSON list of supported price symbols.

        Example:
            ["BTCUSD", "BTCEUR", "BTCXAU"]

    active
        Enables or disables the oracle.

    meta
        Optional JSON field for provider-specific configuration.

    created_at
        Row creation timestamp.

    updated_at
        Last modification timestamp.
    """

    __tablename__ = "oracles"

    oracle_name = Column(String(64), primary_key=True)

    provider = Column(String(128), nullable=False)

    endpoint = Column(String(256), nullable=False)

    supported_symbols = Column(JSON, nullable=False)

    active = Column(Boolean, default=True, nullable=False)

    meta = Column(JSON, nullable=True)

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    def as_dict(self) -> dict:
        """
        Convert Oracle object into dictionary representation.
        """
        return {
            "oracle_name": self.oracle_name,
            "provider": self.provider,
            "endpoint": self.endpoint,
            "supported_symbols": self.supported_symbols,
            "active": self.active,
            "meta": self.meta
        }
    
    # --- Helpers ---------------------------------------------------------------------------------------------------- #

    def __repr__(self):
        return f"Oracle(oracle_name={self.oracle_name}, endpoint={self.endpoint})"


    @classmethod
    def construct(cls, d_in: dict) -> Oracle:
        """
        Construct an instance from a dictionary.

        This method is used by the sql_access bootstrap loader
        (ADD_rows_to_table) when inserting reference data.
        """
        # keep only known columns
        column_names = {c.name for c in cls.__table__.columns}

        payload = {k: v for k, v in d_in.items() if k in column_names}

        # ensure default active flag
        if "active" not in payload:
            payload["active"] = True

        return cls(**payload)
