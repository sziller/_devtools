"""
SQLAlchemy powered DB Bases: idempotency tracking
by Sziller
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    UniqueConstraint,
    Index,
    Text,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class IdempotencyRecord(Base):
    """=== Classname: IdempotencyRecord(Base) ===========================================================
    Represents a single executed (or in-progress) request for idempotency control.

    This table ensures that:
        - the same request (Idempotency-Key) is executed at most once
        - retries return the exact same response
        - mismatched payload reuse is rejected

    Each record corresponds to ONE logical client action.

    ======================================================================================= by Sziller ==="""

    __tablename__ = "idempotency_records"

    id: int = Column("id", Integer, primary_key=True)

    # --- Idempotency key (global uniqueness) ---
    idempotency_key: str = Column("idempotency_key", String(64), nullable=False)

    # --- Endpoint scope (debugging / audit) ---
    endpoint: str = Column("endpoint", String(128), nullable=False)

    # --- User context ---
    uuid: str = Column("uuid", String(32), nullable=False, index=True)

    # --- Payload consistency ---
    payload_hash: str = Column("payload_hash", String(64), nullable=False)

    # --- Response snapshot (JSON string) ---
    # Empty string = request in progress
    response_json: str = Column("response_json", Text, nullable=False, default="")

    # --- Timestamp ---
    created_at: float = Column("created_at", Float, nullable=False)

    __table_args__ = (

        # Enforce global uniqueness of idempotency key
        UniqueConstraint(
            "idempotency_key",
            name="uq_idempotency_key"
        ),

        # Fast lookup by key
        Index(
            "ix_idempotency_key",
            "idempotency_key"
        ),

        # Cleanup / TTL support
        Index(
            "ix_idempotency_created_at",
            "created_at"
        ),

        # Debug / audit
        Index(
            "ix_idempotency_uuid",
            "uuid"
        ),
    )

    def __init__(self,
                 idempotency_key: str,
                 endpoint: str,
                 uuid: str,
                 payload_hash: str,
                 response_json: str,
                 created_at: float,
                 **kwargs):

        self.idempotency_key = idempotency_key
        self.endpoint = endpoint
        self.uuid = uuid
        self.payload_hash = payload_hash
        self.response_json = response_json
        self.created_at = created_at

    def return_as_dict(self):
        """Returns record as dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self):
        return (
            f"IdempotencyRecord("
            f"key={self.idempotency_key}, "
            f"endpoint={self.endpoint}, "
            f"uuid={self.uuid}, "
            f"created_at={self.created_at})"
        )
