"""
SQLAlchemy powered DB Bases: test, and production code.
by Sziller
"""
from typing import Optional

# imports for general Base handling START                                                   -   START   -
from sqlalchemy import Column, Integer, String, Float, BOOLEAN, JSON, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import event
from sqlalchemy import inspect as sqla_inspect
# imports for general Base handling ENDED                                                   -   ENDED   -

# imports for local Base handling   START                                                   -   START   -
# imports for local Base handling   ENDED                                                   -   ENDED   -

Base = declarative_base()


class UserAnonym(Base):
    """=== Classname: UserAnonym(Base) =================================================================================
    Class represents an anonym general user whose data is to be stored and processed by the DB
    ============================================================================================== by Sziller ==="""
    __tablename__ = "useranonyms"
    
    # --- Identity and authorization ---
    email: str              = Column("email",           String(320),primary_key=True,   nullable=False)
    psswd_hsh: str          = Column("psswd_hsh",       String,                         nullable=False)
    auth_code: int          = Column("auth_code",       Integer,                        nullable=False, default=0)
    conf_tkn_hash: str      = Column("conf_tkn_hash",   String(64),                     nullable=True)
    
    # --- Wallet related ---
    xpub: str               = Column("xpub",            String,                         nullable=True,  default="")
    used_addr_set: list     = Column("used_addr_set",   JSON,                           nullable=False, default=list)
    
    # --- Permanent user ID ---
    uuid: str               = Column("uuid",            String(32),                     nullable=False, unique=True)
    
    # --- Balance and bookkeeping
    balance_onchain: int    = Column("balance_onchain", Integer,                        nullable=False, default=0)
    balance_derived: int    = Column("balance_derived", Integer,                        nullable=False, default=0)
    timestamp: float        = Column("timestamp",       Float,                          nullable=False, default=0.0)
    disabled: bool          = Column("disabled",        BOOLEAN,                        nullable=False, default=False)

    # === Referrals ===

    # Parent’s permanent ID (nullable, NOT UNIQUE, NEVER CHANGES ONCE SET)
    uuid_parent: str        = Column("uuid_parent",     String(32),                     nullable=True,  index=True)

    # The user's OWN shareable referral code (UNIQUE, REQUIRED, may be rotated later)
    referral_code: str      = Column("referral_code",   String(64),                     nullable=False, unique=True)

    # The parent’s referral code as seen on arrival (nullable, NOT UNIQUE, may change)
    par_referral_code: str  = Column("par_referral_code",   String(64),                 nullable=True)

    # First-touch timestamp in ms (nullable; set when first captured)
    referral_first_touch_ts: int    = Column("referral_first_touch_ts", Integer,        nullable=True)

    # Optional debug/analytics helpers (all nullable)
    referral_src_url: str   = Column("referral_src_url",    String,                     nullable=True)  # landing URL carrying the ref
    visitor_id: str         = Column("visitor_id",          String,                     nullable=True)  # optional anon cookie/session id

    __table_args__ = (
        UniqueConstraint("uuid", name="uq_useranonyms_uuid"),
        UniqueConstraint("referral_code", name="uq_useranonyms_referral_code"),
        Index("ix_useranonyms_conf_tkn_hash", "conf_tkn_hash"),
        CheckConstraint('uuid_parent IS NULL OR uuid_parent <> uuid', name='ck_no_self_referral')
    )

    def __init__(self,
                 email: str,
                 psswd_hsh: str,
                 auth_code: int                         = 0,
                 conf_tkn_hash: Optional[str]           = None,
                 xpub: Optional[str]                    = None,
                 used_addr_set: Optional[list]          = None,
                 uuid: str                              = "",
                 balance_onchain: int                   = 0,
                 balance_derived: int                   = 0,
                 timestamp: float                       = 0.0,
                 disabled: bool                         = False,
                 # new referral args (explicit for clarity; still accept **kwargs)
                 uuid_parent: Optional[str]             = None,
                 referral_code: Optional[str]           = None,
                 par_referral_code: Optional[str]       = None,
                 referral_first_touch_ts: Optional[int] = None,
                 referral_src_url: Optional[str]        = None,
                 visitor_id: Optional[str]              = None,
                 **kwargs):
        self.email: str                 = email
        self.psswd_hsh: str             = psswd_hsh
        self.auth_code: int             = auth_code
        self.conf_tkn_hash              = conf_tkn_hash
        self.xpub: str                  = "" if xpub is None else xpub
        self.used_addr_set: list        = used_addr_set if used_addr_set is not None else []
        # enforce permanent uuid presence
        if not uuid:
            raise ValueError("UserAnonym.uuid (permanent user ID) must be set and non-empty.")
        self.uuid = uuid
        self.balance_onchain: int       = balance_onchain
        self.balance_derived: int       = balance_derived
        self.timestamp: float           = timestamp
        self.disabled: bool             = disabled

        # Referrals
        self.uuid_parent = uuid_parent
        if not referral_code:
            raise ValueError("UserAnonym.referral_code must be set (derived from uuid).")
        self.referral_code = referral_code
        self.par_referral_code = par_referral_code
        self.referral_first_touch_ts = referral_first_touch_ts
        self.referral_src_url = referral_src_url
        self.visitor_id = visitor_id

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
        return "user: {:<20} - added: {}".format(self.email, self.timestamp)


@event.listens_for(UserAnonym, "before_update", propagate=True)
def _guard_immutable_fields(mapper, connection, target: UserAnonym):
    insp = sqla_inspect(target)

    # uuid must never change once set
    if "uuid" in insp.attrs and insp.attrs.uuid.history.has_changes():
        old = insp.attrs.uuid.history.deleted
        new = insp.attrs.uuid.history.added
        if old and old[0] and new and new[0] != old[0]:
            raise ValueError("UserAnonym.uuid is immutable and cannot be changed once set.")

    # uuid_parent must never change once set (first-touch wins)
    if "uuid_parent" in insp.attrs and insp.attrs.uuid_parent.history.has_changes():
        old = insp.attrs.uuid_parent.history.deleted
        new = insp.attrs.uuid_parent.history.added
        if old and old[0] is not None and new and new[0] != old[0]:
            raise ValueError("UserAnonym.uuid_parent is immutable once set (first-touch).")
