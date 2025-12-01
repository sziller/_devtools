"""
SQLAlchemy powered DB Bases: test, and production code.
by Sziller
"""
import logging
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Text, TIMESTAMP, func, UniqueConstraint,
    Integer, BigInteger, Boolean, Enum,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Setting up logger                                         logger                      -   START   -
lg = logging.getLogger(__name__)
# Setting up logger                                         logger                      -   ENDED   -


class OriginState(PyEnum):
    """TX-origin certainty for this UTXO.

    - local_draft : created by a locally constructed TX that is not yet broadcast
    - mempool     : created by a broadcast TX that is in mempool (0 conf)
    - confirmed   : created by a TX that has at least 1 confirmation

    NOTE:
    CONFIRM_DEPTH is applied OUTSIDE this enum: you will typically split
    'confirmed' into 'shallow' vs 'mature' based on depth, not with more DB states.
    """
    LOCAL_DRAFT = "local_draft"
    MEMPOOL = "mempool"
    CONFIRMED = "confirmed"


class UTXO(Base):
    """=== Classname: UTXO(Base) ================================================================
    Class representing an Unspent Transaction Output tracked by the engine.

    Stores:
      - Bitcoin-standard outpoint (txid, vout)
      - Value, script, address, and optional chain metadata
      - DLC / funding reservation metadata
      - Origin-state of the UTXO in the TX lifecycle (local_draft / mempool / confirmed)

    Lifecycle view
    --------------
    * Origin (how this UTXO came to exist for us):
      - origin_state      : local_draft | mempool | confirmed
      - origin_txid_local : local handle of the TX that (will) create it
        (for confirmed UTXOs, txid itself is the on-chain txid; origin_txid_local may be NULL)

    * Spend lifecycle:
      - is_spent  : False = still UTXO; True = we consider it consumed
      - spend_txid: on-chain txid that consumed it (when known)

    * DLC / funding reservations:
      - reserved_for_dlc_id     : DLC this UTXO is (soft) earmarked for
      - reserved_for_txid_local : local funding-TX draft that hard-locks this UTXO
      - reserved_at             : when we reserved it
      - reservation_expires_at  : when reservation should be considered stale

    * Wallet provenance:
      - xpub, derivation_path, wallet_tag

    Invariants (enforced at service level, not DB):
      - A UTXO with reserved_for_txid_local is considered HARD reserved
        and not available for new contracts.
      - OriginState + block_height/confirm_depth drive liquidity decisions.
    ==================================================================================== by Sziller ==="""
    __tablename__ = "utxos"

    # --- Bitcoin-standard identifiers (composite primary key = outpoint)
    txid: str = Column(String, primary_key=True)   # TXID that created this output (on-chain when confirmed)
    vout: int = Column(Integer, primary_key=True)  # Output index in that TX

    # --- Output data
    value: int = Column(BigInteger, nullable=False)      # Satoshis
    script_pubkey: str = Column(Text, nullable=False)
    address: str = Column(String, nullable=True)         # Derived/recognized address (if available)
    script_type: str = Column(String, nullable=True)     # e.g. 'p2wpkh', 'p2tr', 'p2wsh', ...

    # --- Chain metadata (optional but handy)
    block_height: int = Column(Integer, nullable=True)
    block_time = Column(TIMESTAMP, nullable=True)

    # --- Spend lifecycle (soft state so we can keep history if we want)
    is_spent: bool = Column(Boolean, nullable=False, default=False)
    spend_txid: str = Column(String, nullable=True)      # TXID that spent this UTXO (when known)

    # --- Origin / TX lifecycle
    origin_state = Column(
        Enum(OriginState, native_enum=False),
        nullable=False,
        default=OriginState.CONFIRMED.value,
        server_default=OriginState.CONFIRMED.value,
    )
    # Local handle for the TX that (will) create this output.
    # For on-chain UTXOs, txid is already the real on-chain txid, so this may be NULL.
    origin_txid_local: str = Column(String, nullable=True)

    # --- DLC / funding reservation layer
    # Soft reservation: UTXO earmarked for a DLC offer.
    # NOTE: conceptually this could be 1:N (UTXO backing multiple offers),
    # but here we keep a single DLC id; a join table would be the "proper" N:M later.
    reserved_for_dlc_id: str = Column(String, nullable=True)

    # Hard reservation: UTXO is actually used in a concrete funding TX draft.
    reserved_for_txid_local: str = Column(String, nullable=True)

    reserved_at = Column(TIMESTAMP, nullable=True)
    reservation_expires_at = Column(TIMESTAMP, nullable=True)

    # --- Wallet provenance
    xpub: str = Column(String, nullable=True)            # Origin XPUB of the address
    derivation_path: str = Column(String, nullable=True) # m/purpose'/coin'/account'/change/index
    wallet_tag: str = Column(String, nullable=True)      # optional grouping label (e.g. "hot", "cold", "oracle")

    # --- Housekeeping
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("txid", "vout", name="unique_outpoint"),
    )

    # --- Convenience properties (not stored) -----------------------------------------
    @property
    def is_soft_reserved(self) -> bool:
        """True if this UTXO is earmarked for a DLC (offer-level)."""
        return self.reserved_for_dlc_id is not None

    @property
    def is_hard_reserved(self) -> bool:
        """True if this UTXO is locked into a concrete funding TX draft."""
        return self.reserved_for_txid_local is not None

    @property
    def is_currently_available_for_new_work(self) -> bool:
        """Available for new coin selection?

        Rule of thumb:
        - must NOT be spent
        - must NOT be hard reserved
        Soft reservation is handled at a higher level (you may still choose
        to avoid using soft-reserved UTXOs for new offers).
        """
        return (self.is_spent is False) and (self.is_hard_reserved is False)

    def return_as_dict(self):
        """Returns instance as a dictionary for API / debugging."""
        return {
            "txid": self.txid,
            "vout": self.vout,
            "value": self.value,
            "script_pubkey": self.script_pubkey,
            "address": self.address,
            "script_type": self.script_type,
            "block_height": self.block_height,
            "block_time": self.block_time,
            "is_spent": self.is_spent,
            "spend_txid": self.spend_txid,
            "origin_state": self.origin_state.value if isinstance(self.origin_state, OriginState) else self.origin_state,
            "origin_txid_local": self.origin_txid_local,
            "reserved_for_dlc_id": self.reserved_for_dlc_id,
            "reserved_for_txid_local": self.reserved_for_txid_local,
            "reserved_at": self.reserved_at,
            "reservation_expires_at": self.reservation_expires_at,
            "xpub": self.xpub,
            "derivation_path": self.derivation_path,
            "wallet_tag": self.wallet_tag,
            "is_soft_reserved": self.is_soft_reserved,
            "is_hard_reserved": self.is_hard_reserved,
            "is_currently_available_for_new_work": self.is_currently_available_for_new_work,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def __repr__(self):
        return (
            f"UTXO({self.txid}:{self.vout}, value={self.value}, "
            f"state={self.origin_state}, spent={self.is_spent}, "
            f"soft={self.is_soft_reserved}, hard={self.is_hard_reserved}, "
            f"wallet={self.wallet_tag})"
        )
