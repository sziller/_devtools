"""
SQLAlchemy powered DB Bases: test, and production code.
by Sziller
"""

# imports for general Base handling START                                                   -   START   -
from sqlalchemy import Column, Integer, String, Float, UniqueConstraint, Index, CheckConstraint, BigInteger
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class LiquidityAllocation(Base):
    """=== Classname: LiquidityAllocation(Base) ===========================================================
    Represents a single user's liquidity allocation within the marketplace.

    Each allocation defines the amount of liquidity a specific user provides
    for an exact product template and interest rate.

    Identity of an allocation is defined by the exact combination of:
        - uuid (user identifier)
        - service_type
        - oracle_hash
        - interest_bp
        - ini_role
        - ltv_percent
        - duration_days

    Multiple allocations across users sharing the same parameters are aggregated
    by the Engine into **market buckets** for public market depth representation.

    Liquidity is aggregated ONLY if all identity parameters match perfectly.

    No field is optional. Backend must validate before insertion.
    ======================================================================================= by Sziller ==="""

    __tablename__ = "liquidity_allocations"

    id: int = Column("id", Integer, primary_key=True)

    product_id: str = Column("product_id", String, nullable=False, index=True)
    
    # --- User identity (UUID based) ---
    uuid: str = Column("uuid", String(32), nullable=False, index=True)
    # --- Allocation identity parameters ---
    service_type: str = Column("service_type", String, nullable=False)

    oracle_hash: str = Column("oracle_hash", String(64), nullable=False)
    oracle_serialized: str = Column("oracle_serialized", String, nullable=False, index=True)

    interest_bp: int = Column("interest_bp", Integer, nullable=False)
    ini_role: str = Column("ini_role", String, nullable=False)

    ltv_percent: int = Column("ltv_percent", Integer, nullable=False)
    duration_days: int = Column("duration_days", Integer, nullable=False)

    # --- Liquidity amount provided by this allocation ---
    liquidity_sat: int = Column("liquidity_sat", BigInteger, nullable=False)

    # --- Timestamp of last modification ---
    timestamp: float = Column("timestamp", Float, nullable=False)

    __table_args__ = (

        # Allocation identity uniqueness constraint
        UniqueConstraint(
            "uuid",
            "product_id",
            # "service_type",  # <-- included and encoded in product_id
            "oracle_hash",
            "interest_bp",
            "ini_role",
            # "ltv_percent",  # <-- included and encoded in product_id
            # "duration_days",  # <-- included and encoded in product_id
            name="uq_liquidity_allocation_identity"
        ),

        Index(
            "ix_liquidity_market_lookup",
            "service_type",
            "oracle_hash",
            "ini_role",
            "ltv_percent",
            "duration_days",
            "interest_bp"
        ),

        # Role validation
        CheckConstraint(
            "ini_role IN ('lend','borrow')",
            name="chk_ini_role_valid"
        ),

        # LTV bounds
        CheckConstraint(
            "ltv_percent >= 0 AND ltv_percent <= 100",
            name="chk_ltv_bounds"
        ),

        # Allowed durations
        CheckConstraint(
            "duration_days IN (30, 90, 180, 365)",
            name="chk_duration_allowed"
        ),

        # Interest bounds (0.00% – 100.00% in basis points)
        CheckConstraint(
            "interest_bp >= 0 AND interest_bp <= 10000",
            name="chk_interest_bounds"
        ),

        # Liquidity must not be negative
        CheckConstraint(
            "liquidity_sat >= 0",
            name="chk_liquidity_non_negative"
        ),
    )

    def __init__(self,
                 uuid: str,
                 product_id: str,              # ✅ ADD
                 service_type: str,
                 oracle_hash: str,
                 oracle_serialized: str,
                 interest_bp: int,
                 ini_role: str,
                 ltv_percent: int,
                 duration_days: int,
                 liquidity_sat: int,
                 timestamp: float,
                 **kwargs):
        self.uuid: str = uuid
        self.product_id = product_id  # ✅ ADD
        self.service_type: str = service_type
        self.oracle_hash: str = oracle_hash
        self.oracle_serialized: str = oracle_serialized
        self.interest_bp: int = interest_bp
        self.ini_role: str = ini_role
        self.ltv_percent: int = ltv_percent
        self.duration_days: int = duration_days
        self.liquidity_sat: int = liquidity_sat
        self.timestamp: float = timestamp

    def return_as_dict(self):
        """Returns allocation instance as dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def construct(cls, d_in):
        """Construct instance from dict."""
        return cls(**d_in)

    def __repr__(self):
        return (
            f"LiquidityAllocation("
            f"uuid={self.uuid}, "
            f"product_id={self.product_id}, "
            f"service={self.service_type}, "
            f"role={self.ini_role}, "
            f"ltv={self.ltv_percent}, "
            f"dur={self.duration_days}, "
            f"interest_bp={self.interest_bp}, "
            f"liq_sat={self.liquidity_sat})"
        )
