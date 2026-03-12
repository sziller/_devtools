"""
SQLAlchemy powered DB Bases: test, and production code.
by Sziller

This module defines the SQLAlchemy ORM base and the UTXO table used by the
wallet / balance engine.

Design goals
------------
- Represent wallet-relevant UTXOs in a deterministic local DB.
- Keep enough lifecycle metadata to support:
    - block-driven UTXO updates
    - reservation logic for DLC creation
    - coin selection
    - liquidity / mature-balance calculations
    - future reorg handling
- Keep the table useful both for production use and for test fixtures.

Important conceptual distinction
--------------------------------
This model stores two different kinds of "origin" information:

1) `origin_state`
   Describes the lifecycle certainty / visibility state of the TX that
   created the UTXO for us:
       local_draft -> mempool -> confirmed

2) `origin_type`
   Describes the economic provenance of the value represented by the UTXO:
       external / self_change / internal

These are intentionally separate because they answer different questions.

Example:
- A UTXO may be `origin_state = confirmed`
- and at the same time `origin_type = self_change`

This means:
- it definitely exists on-chain for us
- and economically it came from our own previously-owned coins as change

Notes on optional `origin_type`
-------------------------------
`origin_type` is intentionally nullable.

Reason:
- older rows may not have this information
- some scanning paths may not be able to classify provenance immediately

Service-level default:
- if `origin_type is NULL`, treat it as if it were `UTXOOrigin.EXTERNAL`

That keeps backward compatibility and conservative risk behavior.
"""

import logging
from enum import Enum as PyEnum
from datetime import datetime
from sqlalchemy import Index, String, Text, DateTime, func, false, Integer, BigInteger, Boolean, Enum
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

Base = declarative_base()

# Setting up logger                                         logger                      -   START   -
lg = logging.getLogger(__name__)
# Setting up logger                                         logger                      -   ENDED   -


class OriginState(PyEnum):
    """Lifecycle certainty / visibility state of the creating TX.

    This enum answers:

        "How certain are we that the TX creating this UTXO exists for us
        in the Bitcoin transaction lifecycle?"

    Values
    ------
    LOCAL_DRAFT
        The output belongs to a locally constructed transaction draft.
        The TX may not yet have been broadcast.

        Example:
        - we assembled a funding TX locally
        - we already know one of its outputs is our change output
        - but the TX is not yet on the network

    MEMPOOL
        The creating TX has been broadcast and observed in mempool, but
        is not yet confirmed in a block.

    CONFIRMED
        The creating TX has at least 1 on-chain confirmation.

    Important
    ---------
    This enum does NOT express maturity depth.
    Confirmation thresholds such as "shallow" vs "mature" are derived
    outside this enum from block_height and current chain tip.
    """
    LOCAL_DRAFT = "local_draft"
    MEMPOOL = "mempool"
    CONFIRMED = "confirmed"


class UTXOOrigin(PyEnum):
    """Economic provenance of the value represented by this UTXO.

    This enum answers:

        "Where did the VALUE in this UTXO come from, economically speaking?"

    This is intentionally different from `OriginState`.

    Why we track this
    -----------------
    A balance engine may apply different maturity / eligibility rules
    depending on provenance.

    Example policy:
    - EXTERNAL funds may require higher confirmation depth
    - SELF_CHANGE may be treated more leniently because it is the residue
      of already-owned capital reshaped by our own transaction

    Values
    ------
    EXTERNAL
        The default / conservative category.
        The UTXO came from outside the system from the perspective of the
        wallet engine.

        Examples:
        - user top-up
        - incoming payment
        - external funding

    SELF_CHANGE
        The UTXO is a change output from a transaction we ourselves
        constructed and broadcast.

        This is usually identified by the TX builder and recorded as
        metadata before / around broadcast, then matched later when the
        TX appears in mempool or a block.

    INTERNAL
        Optional future category for internal wallet reshuffling.

        Examples:
        - UTXO consolidation
        - internal treasury transfer
        - internal operational move between wallet branches

    Important
    ---------
    The DB column using this enum is nullable.
    If NULL, service-level logic should interpret it as EXTERNAL.
    """
    EXTERNAL = "external"
    SELF_CHANGE = "self_change"
    INTERNAL = "internal"


class Utxo(Base):
    """=== Classname: UTXO(Base) ================================================================
    Class representing an Unspent Transaction Output tracked by the engine.

    Core purpose
    ------------
    This table is the local wallet-side UTXO ledger maintained by the
    application. It is intended to act as the source of truth for
    balance derivation, coin selection, and reservation handling.

    The engine should ideally:
    - update this table from block / mempool observations
    - derive balances from this table
    - reserve concrete UTXOs for funding work through this table

    Stores
    ------
    - Bitcoin-standard outpoint (`txid`, `vout`)
    - Output value and script metadata
    - Block linkage metadata (`block_height`, `block_time`)
    - Spend-tracking metadata (`is_spent`, `spend_txid`, `spent_height`)
    - TX-lifecycle metadata (`origin_state`, `origin_txid_local`)
    - Economic provenance metadata (`origin_type`)
    - Reservation metadata for DLC / funding work
    - Wallet provenance (`xpub`, `derivation_path`, `wallet_tag`)

    Lifecycle view
    --------------
    * Creation / visibility:
      - origin_state      : local_draft | mempool | confirmed
      - origin_txid_local : local transaction identifier used by our own
                            engine while the TX may not yet have a final
                            on-chain txid or while we want to keep a local
                            linkage

    * Economic provenance:
      - origin_type       : external | self_change | internal | NULL
                            NULL must be interpreted conservatively as external

    * Spend lifecycle:
      - is_spent          : False = still currently unspent for wallet purposes
                            True  = known consumed / no longer an active UTXO
      - spend_txid        : TXID of the spending transaction, when known
      - spent_height      : block height where the spending TX was confirmed,
                            when known

    * Reservation layer:
      - reserved_for_dlc_id     : soft reservation / earmark at DLC level
      - reserved_for_txid_local : hard reservation into a concrete local TX draft
      - reserved_at             : reservation timestamp
      - reservation_expires_at  : optional timeout for stale reservation cleanup

    * Wallet provenance:
      - xpub              : xpub under which this output belongs
      - derivation_path   : derivation path of the address, when available
      - wallet_tag        : logical wallet grouping tag

    Service-level invariants (NOT enforced by DB)
    ---------------------------------------------
    - A UTXO with `reserved_for_txid_local` is treated as HARD reserved and
      must not be selected again for new funding work.
    - A UTXO with `is_spent = True` is no longer an active UTXO.
    - `origin_type is NULL` must be interpreted by application code as
      `UTXOOrigin.EXTERNAL`.
    - Liquidity and maturity decisions are driven from:
        * current chain tip
        * block_height
        * origin_state
        * origin_type
    ==================================================================================== by Sziller ==="""

    __tablename__ = "utxos"

    # ---------------------------------------------------------------------------------
    # Bitcoin-standard identifiers
    # ---------------------------------------------------------------------------------
    # A Bitcoin output is uniquely identified by the outpoint:
    #
    #     (txid, vout)
    #
    # Therefore we use a composite primary key.
    #
    # Notes:
    # - `txid` is the transaction that created THIS output
    # - `vout` is the output index within that transaction
    #
    txid: Mapped[str] = mapped_column(String, primary_key=True)
    vout: Mapped[int] = mapped_column(primary_key=True)

    # ---------------------------------------------------------------------------------
    # Output payload data
    # ---------------------------------------------------------------------------------
    # These fields describe the output itself.
    #
    # `value`
    #   Satoshi amount of the output.
    #
    # `script_pubkey`
    #   Raw locking script as text / hex representation used by your system.
    #
    # `address`
    #   Optional decoded / recognized address, if derivable.
    #
    # `script_type`
    #   Optional convenience tag such as:
    #   - p2wpkh
    #   - p2tr
    #   - p2wsh

    value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    script_pubkey: Mapped[str] = mapped_column(Text, nullable=False)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    script_type: Mapped[str | None] = mapped_column(String, nullable=True)

    # ---------------------------------------------------------------------------------
    # Chain metadata
    # ---------------------------------------------------------------------------------
    # These fields describe where in the chain the creating transaction sits.
    #
    # `block_height`
    #   Height of the block that confirmed the creating TX.
    #   NULL means:
    #   - local draft, or
    #   - mempool only, or
    #   - chain metadata not yet filled
    #
    # `block_time`
    #   Optional timestamp of the confirming block.
    #
    # Confirmation depth is NOT stored directly here.
    # It should be derived at query / service time from:
    #
    #     confirm_depth = current_tip_height - block_height + 1

    block_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    block_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ---------------------------------------------------------------------------------
    # Spend lifecycle
    # ---------------------------------------------------------------------------------
    # We intentionally keep spent rows instead of deleting them.
    #
    # Why:
    # - useful for historical reconstruction
    # - useful for debugging coin selection
    # - useful for future reorg handling
    # - useful for balance snapshots / audit trails
    #
    # `is_spent`
    #   False -> currently still an active UTXO
    #   True  -> known consumed
    #
    # `spend_txid`
    #   On-chain TXID that spent this UTXO, when known.
    #
    # `spent_height`
    #   Block height at which the spending TX was confirmed.
    #
    #   This is important for:
    #   - historical queries
    #   - reorg rollback logic
    #   - understanding when a coin actually left the active set
    #
    #   If the spending TX is still only in mempool, this should remain NULL.

    is_spent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false()
    )
    spend_txid: Mapped[str | None] = mapped_column(String, nullable=True)
    spent_height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ---------------------------------------------------------------------------------
    # Origin / TX lifecycle metadata
    # ---------------------------------------------------------------------------------
    # `origin_state`
    #   Describes the certainty / visibility of the TX creating this UTXO:
    #   local_draft / mempool / confirmed
    #
    #   We keep `native_enum=False` because this plays nicely with SQLite.
    #
    # `origin_txid_local`
    #   Optional local identifier for the transaction that creates this UTXO.
    #
    #   Why this exists:
    #   - during local TX construction we may want to tag outputs before they
    #     are fully known on-chain
    #   - we may want to link locally drafted outputs to draft funding work
    #   - some engine flows use internal local TX handles before final network
    #     settlement
    #
    origin_state: Mapped[OriginState] = mapped_column(
        Enum(
            OriginState,
            native_enum=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=OriginState.CONFIRMED,
        server_default=OriginState.CONFIRMED.value,
    )

    origin_txid_local: Mapped[str | None] = mapped_column(String, nullable=True)

    # ---------------------------------------------------------------------------------
    # Economic provenance metadata
    # ---------------------------------------------------------------------------------
    # `origin_type`
    #   Describes WHERE THE VALUE came from economically.
    #
    #   This is intentionally OPTIONAL (`nullable=True`).
    #
    #   If left NULL, service-level logic must treat the UTXO conservatively as:
    #
    #       UTXOOrigin.EXTERNAL
    #
    #   Why optional:
    #   - backward compatibility with old rows
    #   - some ingestion paths may not know provenance immediately
    #   - provenance may be filled later when matching locally created TXs
    #
    #   Typical values:
    #   - external
    #   - self_change
    #   - internal
    #
    #   Important distinction:
    #   `origin_state` answers: "how certain / visible is the creating TX?"
    #   `origin_type`  answers: "what economic class of value is this?"

    origin_type: Mapped[UTXOOrigin | None] = mapped_column(
        Enum(
            UTXOOrigin,
            native_enum=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=True,
        default=None,
    )
    # ---------------------------------------------------------------------------------
    # DLC / funding reservation layer
    # ---------------------------------------------------------------------------------
    # Reservations are application-level concurrency / selection guards.
    #
    # Soft reservation:
    #   `reserved_for_dlc_id`
    #   The UTXO is earmarked for a DLC-level intent / offer.
    #
    # Hard reservation:
    #   `reserved_for_txid_local`
    #   The UTXO is locked into a specific concrete TX draft and must not be
    #   re-used by another funding attempt.
    #
    # This is essential for avoiding accidental double-selection of the same UTXO.
    #
    # Note:
    # The soft reservation model here is simplified as a single DLC id.
    # A future N:M reservation model could be implemented with a join table.
    #
    reserved_for_dlc_id: Mapped[str | None] = mapped_column(String, nullable=True)
    reserved_for_txid_local: Mapped[str | None] = mapped_column(String, nullable=True)
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reservation_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ---------------------------------------------------------------------------------
    # Wallet provenance
    # ---------------------------------------------------------------------------------
    # These fields tell us WHICH wallet / branch / derivation path this UTXO belongs to.
    #
    # `xpub`
    #   The xpub under which this output was discovered / derived.
    #
    # `derivation_path`
    #   Full or partial path such as:
    #       m/purpose'/coin'/account'/change/index
    #
    # `wallet_tag`
    #   Optional logical grouping label.
    #
    #   Examples:
    #   - hot
    #   - cold
    #   - oracle
    #   - treasury
    #
    xpub: Mapped[str | None] = mapped_column(String, nullable=True)
    derivation_path: Mapped[str | None] = mapped_column(String, nullable=True)
    wallet_tag: Mapped[str | None] = mapped_column(String, nullable=True)

    # ---------------------------------------------------------------------------------
    # Housekeeping
    # ---------------------------------------------------------------------------------
    # `created_at`
    #   Row creation timestamp.
    #
    # `updated_at`
    #   Automatically refreshed when the row is updated by SQLAlchemy-supported flows.
    #
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False,
                                                 onupdate=func.now())

    seen_in_scan_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    __table_args__ = (
        Index("idx_utxo_xpub", xpub),
        Index("idx_utxo_spent", is_spent),
        Index("idx_utxo_reserved", reserved_for_txid_local),
        Index("idx_utxo_select", xpub, is_spent),
        Index("idx_utxo_coin_select", xpub, is_spent, reserved_for_txid_local),
        Index("idx_utxo_reservation_expiry", reservation_expires_at),
        Index("idx_utxo_seen_scan", seen_in_scan_at),
    )
    
    # ---------------------------------------------------------------------------------
    # Convenience properties (NOT stored)
    # ---------------------------------------------------------------------------------
    @property
    def outpoint(self) -> str:
        """convenience property used all accross Bitcoin"""
        return f"{self.txid}:{self.vout}"
    
    @property
    def is_soft_reserved(self) -> bool:
        """True if this UTXO is earmarked for a DLC at soft-reservation level."""
        return self.reserved_for_dlc_id is not None

    @property
    def is_hard_reserved(self) -> bool:
        """True if this UTXO is locked into a concrete local funding TX draft."""
        return self.reserved_for_txid_local is not None

    @property
    def effective_origin_type(self):
        """Return a safe, service-level interpretation of `origin_type`.

        Rule:
        - if DB value is NULL, interpret as EXTERNAL

        This keeps old data and partial-ingestion flows conservative.
        """
        return self.origin_type or UTXOOrigin.EXTERNAL

    @property
    def is_currently_available_for_new_work(self) -> bool:
        """Whether the UTXO is currently selectable for new coin-selection work.

        Rule of thumb:
        - must NOT be spent
        - must NOT be hard reserved

        Notes:
        - Soft reservation is intentionally NOT enforced here.
          That remains a higher-level policy decision.
        - Some flows may still decide to exclude soft-reserved UTXOs.
        """
        return (not self.is_spent) and (not self.is_hard_reserved)

    def to_dict(self) -> dict:
        """Return instance as a dictionary for API use, debugging, or logging."""

        origin_state = self.origin_state
        origin_type = self.origin_type
        effective_origin = self.effective_origin_type

        return {
            "txid": self.txid,
            "vout": self.vout,
            "outpoint": self.outpoint,
            "value": self.value,
            "script_pubkey": self.script_pubkey,
            "address": self.address,
            "script_type": self.script_type,

            "block_height": self.block_height,
            "block_time": self.block_time,

            "is_spent": self.is_spent,
            "spend_txid": self.spend_txid,
            "spent_height": self.spent_height,

            "origin_state": (
                origin_state.value if isinstance(origin_state, OriginState) else origin_state
            ),

            "origin_txid_local": self.origin_txid_local,

            "origin_type": (
                origin_type.value if isinstance(origin_type, UTXOOrigin) else origin_type
            ),

            "effective_origin_type": (
                effective_origin.value
                if isinstance(effective_origin, UTXOOrigin)
                else effective_origin
            ),

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
        origin_type_repr = getattr(self.origin_type, "value", self.origin_type)
        origin_state_repr = getattr(self.origin_state, "value", self.origin_state)

        return (
            f"UTXO({self.txid}:{self.vout}, value={self.value}, "
            f"state={origin_state_repr}, origin_type={origin_type_repr}, "
            f"spent={self.is_spent}, soft={self.is_soft_reserved}, "
            f"hard={self.is_hard_reserved}, wallet={self.wallet_tag})"
        )
