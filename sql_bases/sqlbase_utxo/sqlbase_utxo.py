"""
SQLAlchemy powered DB Bases: test, and production code.
by Sziller
"""
import logging
from sqlalchemy import (
    Column, String, Text, TIMESTAMP, func, UniqueConstraint,
    Integer, BigInteger, Boolean
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Setting up logger                                         logger                      -   START   -
lg = logging.getLogger(__name__)
# Setting up logger                                         logger                      -   ENDED   -


class UTXO(Base):
    """=== Classname: UTXO(Base) =======================================================================================
    Class representing an Unspent Transaction Output tracked by the engine.
    Stores the Bitcoin-standard outpoint data and minimal chain metadata, plus custom wallet-origin info.

    Standard fields:
      - (txid, vout): composite PK for the UTXO outpoint
      - value (sats), script_pubkey, optional address/script_type
      - block_height / block_time (if known)

    Custom fields:
      - xpub:           XPUB that originated the address holding this UTXO
      - derivation_path Derivation path for the key (e.g., m/84'/0'/0'/0/15)
      - reserved_for_dlc_id: If set, the UTXO is temporarily reserved for a specific DLC flow

    Notes:
      - Keep only *currently* unspent UTXOs here. When spent, set `is_spent=True`, `spend_txid` and keep the row
        for auditability (or delete if you prefer a strictly-current view).
    ============================================================================================== by Sziller ==="""
    __tablename__ = "utxos"

    # --- Bitcoin-standard identifiers (composite primary key = outpoint)
    txid: str = Column(String, primary_key=True)         # TXID that created this output
    vout: int = Column(Integer, primary_key=True)        # Output index in that TX

    # --- Output data
    value: int = Column(BigInteger, nullable=False)      # Satoshis
    script_pubkey: str = Column(Text, nullable=False)
    address: str = Column(String, nullable=True)         # Derived/recognized address (if available)
    script_type: str = Column(String, nullable=True)     # e.g. 'p2wpkh', 'p2tr', 'p2wsh', ...

    # --- Chain metadata (optional but handy)
    block_height: int = Column(Integer, nullable=True)
    block_time = Column(TIMESTAMP, nullable=True)

    # --- Lifecycle / spending info (soft state so we can keep history if we want)
    is_spent: bool = Column(Boolean, nullable=False, default=False)
    spend_txid: str = Column(String, nullable=True)      # TXID that spent this UTXO (when known)

    # --- Custom wallet-origin info
    xpub: str = Column(String, nullable=True)            # Origin XPUB of the address
    derivation_path: str = Column(String, nullable=True) # m/purpose'/coin'/account'/change/index
    reserved_for_dlc_id: str = Column(String, nullable=True)

    # --- Housekeeping
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Helpful uniqueness guard if you decide to keep addresses unique in your system (optional):
    __table_args__ = (
        UniqueConstraint("txid", "vout", name="unique_outpoint"),
    )

    # --- Serialization helpers -------------------------------------------------
    def return_as_dict(self):
        """Returns instance as a dictionary"""
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
            "xpub": self.xpub,
            "derivation_path": self.derivation_path,
            "reserved_for_dlc_id": self.reserved_for_dlc_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def __repr__(self):
        return (
            f"UTXO({self.txid}:{self.vout}, value={self.value}, "
            f"addr={self.address}, spent={self.is_spent})"
        )
