"""
SQLAlchemy powered DB Bases: test, and production code.
by Sziller
"""

# imports for general Base handling START                                                   -   START   -
from sqlalchemy import Column, Integer, String, JSON, Float, BOOLEAN, BigInteger
from sqlalchemy.orm import declarative_base
from sqlalchemy import ForeignKey
# imports for general Base handling ENDED                                                   -   ENDED   -

# imports for liquidity bucket handling START                                               -   START   -
from sqlalchemy import UniqueConstraint, CheckConstraint, Index
# imports for liquidity bucket handling ENDED                                               -   ENDED   -

# imports for local Base handling   START                                                   -   START   -

# imports for local Base handling   ENDED                                                   -   ENDED   -

Base = declarative_base()


class User(Base):
    """=== Classname: User(Base) =======================================================================================
    Class represents general user who's data is to be stored and processed by the DB
    ============================================================================================== by Sziller ==="""
    __tablename__ = "users"
    username: str           = Column("username", String, primary_key=True)
    psswd_hsh: str          = Column("psswd_hsh", String)
    email: str              = Column("email", String, unique=True)
    usr_fn: str             = Column("usr_fn", String)
    usr_ln: str             = Column("usr_ln", String)
    auth_code: int          = Column("auth_code", Integer)
    pubkey: str             = Column("pubkey", String)
    email_arch: list        = Column("email_arch", JSON)
    uuid: str               = Column("uuid", String, unique=True, nullable=False, index=True)
    timestamp: float        = Column("timestamp", Float)
    disabled: bool          = Column("disabled", BOOLEAN)

    def __init__(self,
                 username: str,
                 psswd_hsh: str,
                 email: str,
                 uuid: str,
                 usr_fn: str                = "",
                 usr_ln: str                = "",
                 auth_code: int             = 0,
                 pubkey: str                = "",
                 email_arch: list | None    = None,
                 timestamp: float           = 0.0,
                 disabled: bool             = False,
                 **kwargs):
        self.username: str      = username
        self.psswd_hsh: str     = psswd_hsh
        self.email: str         = email
        self.usr_fn: str        = usr_fn
        self.usr_ln: str        = usr_ln
        self.auth_code: int     = auth_code
        self.pubkey: str        = pubkey
        self.email_arch         = email_arch or []
        self.uuid: str          = uuid
        self.timestamp: float   = timestamp
        self.disabled: bool     = disabled

    def return_as_dict(self):
        """=== Method name: return_as_dict =============================================================================
        Returns instance as a dictionary
        @return : dict - parameter: argument pairs in a dict
        ========================================================================================== by Sziller ==="""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @ classmethod
    def construct(cls, d_in):
        """=== Classmethod: construct ==================================================================================
        Input necessary class parameters to instantiate object of the class!
        @param d_in: dict - format data to instantiate new object
        @return: an instance of the class
        ========================================================================================== by Sziller ==="""
        return cls(**d_in)

    def __repr__(self):
        return "user: {:<20} - {:<35} called: {:<15}, {:<15} - added: {}".format(self.username,
                                                                                 self.email,
                                                                                 self.usr_ln,
                                                                                 self.usr_fn,
                                                                                 self.timestamp)


class LiquidityBucket(Base):
    """=== Classname: LiquidityBucket(Base) ==============================================================
    Represents a strictly defined liquidity allocation bucket.

    Identity of a bucket is defined by the exact combination of:
        - uuid (user identifier)
        - service_type
        - oracle_hash
        - interest_bp
        - ini_role
        - ltv_percent
        - duration_days

    Liquidity is aggregated ONLY if all identity parameters match perfectly.

    No field is optional. Backend must validate before insertion.
    ======================================================================================= by Sziller ==="""

    __tablename__ = "liquidity_buckets"
    
    id: int                    = Column("id", Integer, primary_key=True)

    # --- User identity (UUID based) ---
    uuid: str                   = Column("uuid", String, ForeignKey("users.uuid"), nullable=False, index=True)

    # --- Bucket identity parameters ---
    service_type: str          = Column("service_type", String, nullable=False)

    oracle_hash: str           = Column("oracle_hash", String(64), nullable=False)
    oracle_serialized: str     = Column("oracle_serialized", String, nullable=False, index=True)

    interest_bp: int           = Column("interest_bp", Integer, nullable=False)
    ini_role: str              = Column("ini_role", String, nullable=False)

    ltv_percent: int           = Column("ltv_percent", Integer, nullable=False)
    duration_days: int         = Column("duration_days", Integer, nullable=False)

    # --- Liquidity ---
    liquidity_sat: int         = Column("liquidity_sat", BigInteger, nullable=False)

    # --- Timestamp ---
    timestamp: float           = Column("timestamp", Float, nullable=False)

    __table_args__ = (

        # Identity uniqueness constraint
        UniqueConstraint(
            "uuid",
            "service_type",
            "oracle_hash",
            "interest_bp",
            "ini_role",
            "ltv_percent",
            "duration_days",
            name="uq_liquidity_bucket_identity"
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

        self.uuid: str                  = uuid
        self.service_type: str          = service_type
        self.oracle_hash: str           = oracle_hash
        self.oracle_serialized: str    = oracle_serialized
        self.interest_bp: int           = interest_bp
        self.ini_role: str              = ini_role
        self.ltv_percent: int           = ltv_percent
        self.duration_days: int         = duration_days
        self.liquidity_sat: int         = liquidity_sat
        self.timestamp: float           = timestamp

    def return_as_dict(self):
        """Returns instance as dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def construct(cls, d_in):
        """Construct instance from dict."""
        return cls(**d_in)

    def __repr__(self):
        return (
            f"LiquidityBucket("
            f"uuid={self.uuid}, "
            f"service={self.service_type}, "
            f"role={self.ini_role}, "
            f"ltv={self.ltv_percent}, "
            f"dur={self.duration_days}, "
            f"interest_bp={self.interest_bp}, "
            f"liq_sat={self.liquidity_sat})"
        )
