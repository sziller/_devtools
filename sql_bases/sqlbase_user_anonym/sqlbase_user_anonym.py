"""=====================================================================================================================
SQLAlchemy powered DB Bases: test, and production code.


This module defines the SQLAlchemy ORM base and the anonym user table used
by the authentication and wallet layers.

Design goals
------------
- Represent anonym users without exposing personal identity.
- Provide wallet linkage through XPUB.
- Track wallet balances derived from the UTXO subsystem.
- Maintain referral and attribution metadata.
- Keep schema compatible with both production runtime and test fixtures.

Important balance model
-----------------------
Wallet balance is decomposed into multiple observable layers:

    balance_onchain           confirmed funds
    balance_onchain_immature  low-confirmation funds
    balance_mempool           mempool observed funds
    balance_wallet            sum of the above
    balance_derived           wallet minus dynamically locked funds

Only the first four are stored directly.
`balance_derived` is derived from wallet balance minus dynamically calculated
locked funds from other system components (DLCPlaza.db, Liquidity.db).
================================================================================================== by Sziller ==="""

from typing import Optional
import logging
from sqlalchemy import (
    String,
    Float,
    Boolean,
    Integer,
    BigInteger,
    UniqueConstraint,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import event
from sqlalchemy import inspect as sqla_inspect

Base = declarative_base()

# -----------------------------------------------------------------------------
# Logger
# -----------------------------------------------------------------------------
lg = logging.getLogger(__name__)


class UserAnonym(Base):
    """=== Classname: UserAnonym(Base) ============================================================

    Represents an anonym user stored inside the authentication database.

    Core responsibilities
    ---------------------
    - Authentication metadata
    - Wallet association via XPUB
    - Wallet balance snapshot storage
    - Referral system metadata

    Identity model
    --------------
    email
        Primary identifier used by authentication flows.

    uuid
        Permanent internal identifier for the user.

    Wallet model
    ------------
    Wallet balances are periodically recalculated from the UTXO subsystem.

    balance_onchain
        Confirmed funds.

    balance_onchain_immature
        Funds with confirmation depth below maturity threshold.

    balance_mempool
        Funds observed in mempool but not yet confirmed.

    balance_wallet
        Total wallet funds (sum of the above).

    balance_derived
        Wallet funds minus dynamically locked balances.
    ============================================================================================== by Sziller ==="""

    __tablename__ = "useranonyms"

    # -------------------------------------------------------------------------
    # Identity and authorization
    # -------------------------------------------------------------------------

    email: Mapped[str] = mapped_column(String(320), primary_key=True)

    psswd_hsh: Mapped[str] = mapped_column(String, nullable=False)

    auth_code: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    conf_tkn_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # -------------------------------------------------------------------------
    # Wallet association
    # -------------------------------------------------------------------------

    xpub: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")

    # -------------------------------------------------------------------------
    # Permanent identifier
    # -------------------------------------------------------------------------

    uuid: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)

    # -------------------------------------------------------------------------
    # Wallet balance snapshot
    # -------------------------------------------------------------------------

    balance_onchain: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    balance_onchain_immature: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    balance_mempool: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    balance_wallet: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    balance_derived: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # -------------------------------------------------------------------------
    # Housekeeping
    # -------------------------------------------------------------------------

    timestamp: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # -------------------------------------------------------------------------
    # Referral system
    # -------------------------------------------------------------------------

    uuid_parent: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    referral_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    par_referral_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    referral_first_touch_ts: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    referral_src_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    visitor_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # -------------------------------------------------------------------------
    # possible KYC
    # -------------------------------------------------------------------------
    
    kyc_status: Mapped[str] = mapped_column(String, nullable=True)
    
    # -------------------------------------------------------------------------
    # Table constraints
    # -------------------------------------------------------------------------

    __table_args__ = (
        UniqueConstraint("referral_code", name="uq_useranonyms_referral_code"),
        Index("ix_useranonyms_conf_tkn_hash", "conf_tkn_hash"),
        CheckConstraint(
            "uuid_parent IS NULL OR uuid_parent <> uuid",
            name="ck_no_self_referral",
        ),
    )

    # -------------------------------------------------------------------------
    # Constructor
    # -------------------------------------------------------------------------

    def __init__(
        self,
        email: str,
        psswd_hsh: str,
        auth_code: int = 0,
        conf_tkn_hash: Optional[str] = None,
        xpub: Optional[str] = None,
        uuid: str = "",
        balance_onchain: int = 0,
        balance_onchain_immature: int = 0,
        balance_mempool: int = 0,
        balance_wallet: int = 0,
        balance_derived: int = 0,
        timestamp: float = 0.0,
        disabled: bool = False,
        uuid_parent: Optional[str] = None,
        referral_code: Optional[str] = None,
        par_referral_code: Optional[str] = None,
        referral_first_touch_ts: Optional[int] = None,
        referral_src_url: Optional[str] = None,
        visitor_id: Optional[str] = None,
        kyc_status: Optional[str] = None,
        **kwargs,
    ):

        self.email = email
        self.psswd_hsh = psswd_hsh
        self.auth_code = auth_code
        self.conf_tkn_hash = conf_tkn_hash
        self.xpub = "" if xpub is None else xpub

        if not uuid:
            raise ValueError("UserAnonym.uuid must be set and non-empty.")

        self.uuid = uuid

        self.balance_onchain = balance_onchain
        self.balance_onchain_immature = balance_onchain_immature
        self.balance_mempool = balance_mempool
        self.balance_wallet = balance_wallet
        self.balance_derived = balance_derived

        self.timestamp = timestamp
        self.disabled = disabled

        self.uuid_parent = uuid_parent

        if not referral_code:
            raise ValueError("UserAnonym.referral_code must be set.")

        self.referral_code = referral_code
        self.par_referral_code = par_referral_code
        self.referral_first_touch_ts = referral_first_touch_ts
        self.referral_src_url = referral_src_url
        self.visitor_id = visitor_id
        self.kyc_status = kyc_status

    # -------------------------------------------------------------------------
    # Convenience helpers
    # -------------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return instance as dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def construct(cls, d_in: dict):
        """Instantiate object from dictionary."""
        return cls(**d_in)

    def __repr__(self):
        return f"user: {self.email:<20} wallet={self.balance_wallet}"


# -----------------------------------------------------------------------------
# Immutable field guard
# -----------------------------------------------------------------------------

@event.listens_for(UserAnonym, "before_update", propagate=True)
def _guard_immutable_fields(mapper, connection, target: UserAnonym):

    insp = sqla_inspect(target)

    # uuid must never change
    if "uuid" in insp.attrs and insp.attrs.uuid.history.has_changes():

        old = insp.attrs.uuid.history.deleted
        new = insp.attrs.uuid.history.added

        if old and old[0] and new and new[0] != old[0]:
            raise ValueError("UserAnonym.uuid is immutable.")

    # uuid_parent must never change once set
    if "uuid_parent" in insp.attrs and insp.attrs.uuid_parent.history.has_changes():

        old = insp.attrs.uuid_parent.history.deleted
        new = insp.attrs.uuid_parent.history.added

        if old and old[0] is not None and new and new[0] != old[0]:
            raise ValueError("UserAnonym.uuid_parent is immutable once set.")


@event.listens_for(UserAnonym, "before_insert", propagate=True)
@event.listens_for(UserAnonym, "before_update", propagate=True)
def _enforce_wallet_balance_consistency(mapper, connection, target: UserAnonym):
    """
    Enforce wallet balance invariant.

    The wallet balance must always equal the sum of its components:

        balance_wallet =
            balance_onchain +
            balance_onchain_immature +
            balance_mempool

    Behavior
    --------
    - Automatically recomputes `balance_wallet`
    - Rejects negative values
    """

    conf = target.balance_onchain or 0
    immature = target.balance_onchain_immature or 0
    mempool = target.balance_mempool or 0

    if conf < 0 or immature < 0 or mempool < 0:
        raise ValueError(
            "Negative wallet balance components are not allowed."
        )

    computed_wallet = conf + immature + mempool

    # Always enforce canonical wallet value
    target.balance_wallet = computed_wallet
    

# -------------------------------------------------------------------------
# Derived balance sanity guard
# -------------------------------------------------------------------------

# @event.listens_for(UserAnonym, "before_insert", propagate=True)
# @event.listens_for(UserAnonym, "before_update", propagate=True)
# @event.listens_for(UserAnonym, "before_commit", propagate=True)
# def _enforce_derived_balance_sanity(mapper, connection, target: UserAnonym):
#     """
#     Enforce derived balance safety invariant.
# 
#     Rules
#     -----
#     1. balance_derived must never be negative
#     2. balance_derived must never exceed balance_wallet
# 
#     Rationale
#     ---------
#     balance_derived represents:
# 
#         balance_wallet - dynamically_locked_funds
# 
#     If it becomes negative or exceeds the wallet, it indicates
#     a logic error in locking or balance recalculation.
#     """
# 
#     wallet = target.balance_wallet or 0
#     derived = target.balance_derived or 0
#     email = target.email
#     
#     if derived < 0:
#         raise ValueError(
#             f"Invalid derived balance ({derived}) — cannot be negative."
#         )
# 
#     if derived > wallet:
#         raise ValueError(f"Derived balance violation for {email}: derived={derived}, wallet={wallet}")
