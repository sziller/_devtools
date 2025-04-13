"""
SQLAlchemy powered DB Bases: test, and production code.
by Sziller
"""
import logging
from sqlalchemy import Column, String, ForeignKey, Text, TIMESTAMP, func, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import Integer, BigInteger

Base = declarative_base()

# Setting up logger                                         logger                      -   START   -
lg = logging.getLogger(__name__)
# Setting up logger                                         logger                      -   ENDED   -


class Transaction(Base):
    """=== Classname: Transaction(Base) ================================================================================
    Class representing a Bitcoin transaction stored in the DB.
    Transactions require 2 signatures before they can be broadcasted.
    ============================================================================================== by Sziller ==="""
    __tablename__ = "transactions"

    txid: str           = Column(String, primary_key=True)  # Transaction ID from bitcoinlib
    dlc_id: str         = Column(String, nullable=False)  # DLC ID this transaction belongs to
    tx_type: str        = Column(String, nullable=False)  # Type of transaction (funding, refund, CET)
    ini_email: str      = Column(String, nullable=True)  # Email of the initiating user
    acc_email: str      = Column(String, nullable=True)  # Email of the accepting user
    tx_hex: str         = Column(Text, nullable=False)  # Raw unsigned Bitcoin transaction
    status: str         = Column(String, nullable=False, default="pending")
    # 'pending', 'partially_signed', 'signed', 'broadcast'
    created_at          = Column(TIMESTAMP, server_default=func.now())  # Auto timestamp on creation
    updated_at          = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())  # Auto timestamp on update

    # Relationship to signatures
    signatures  = relationship("Signature",         back_populates="transaction", cascade="all, delete-orphan")
    inputs      = relationship("TransactionInput",  back_populates="transaction", cascade="all, delete-orphan")

    def return_as_dict(self, include_inputs: bool = False):
        """Returns instance as a dictionary"""
        
        base = {
            "txid": self.txid,
            "dlc_id": self.dlc_id,
            "tx_type": self.tx_type,
            "ini_email": self.ini_email,
            "acc_email": self.acc_email,
            "tx_hex": self.tx_hex,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "signatures": [sig.return_as_dict() for sig in self.signatures]}
        
        if include_inputs:
            base["inputs"] = [inp.return_as_dict() for inp in self.inputs]

        return base
    
    def __repr__(self):
        return f"Transaction(txid={self.txid}, dlc_id={self.dlc_id}, tx_type={self.tx_type}, status={self.status})"


class TransactionInput(Base):
    """Stores metadata for each input in a transaction, needed for signing."""
    __tablename__ = "transaction_inputs"

    id                  = Column(String, primary_key=True)
    transaction_id      = Column(String, ForeignKey("transactions.txid", ondelete="CASCADE"), nullable=False)
    input_index         = Column(Integer, nullable=False)
    # Required for signing
    prev_txid           = Column(String, nullable=False)
    vout                = Column(Integer, nullable=False)
    value               = Column(BigInteger, nullable=False)  # satoshis
    script_pubkey       = Column(Text, nullable=False)
    script_type         = Column(String, nullable=False)  # 'p2wpkh', 'p2pkh', etc.
    # Optional extras
    address             = Column(String, nullable=True)
    pubkey              = Column(String, nullable=True)

    transaction = relationship("Transaction", back_populates="inputs")

    __table_args__ = (UniqueConstraint("transaction_id", "input_index", name="unique_tx_input"),)

    def return_as_dict(self):
        """Returns instance as a dictionary"""
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "input_index": self.input_index,
            "prev_txid": self.prev_txid,
            "vout": self.vout,
            "value": self.value,
            "script_pubkey": self.script_pubkey,
            "script_type": self.script_type,
            "address": self.address,
            "pubkey": self.pubkey}


class Signature(Base):
    """=== Classname: Signature(Base) ==================================================================================
    Class representing a partial signature for a Bitcoin transaction.
    Each transaction can have up to 2 signatures.
    ============================================================================================== by Sziller ==="""
    __tablename__ = "signatures"

    id: str             = Column(String, primary_key=True)
    transaction_id: str = Column(String, ForeignKey("transactions.txid", ondelete="CASCADE"), nullable=False)
    signer: str         = Column(String, nullable=False)  # 'app' or 'backend' (or any unique identifier)
    signature: str      = Column(Text, nullable=False)  # Partial signature

    # Relationship back to transaction
    transaction = relationship("Transaction", back_populates="signatures")

    # Ensure each signer signs only once per transaction
    __table_args__ = (UniqueConstraint("transaction_id", "signer", name="unique_transaction_signer"),)

    def return_as_dict(self):
        """Returns instance as a dictionary"""
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "signer": self.signer,
            "signature": self.signature}

    def __repr__(self):
        return f"Signature(transaction_id={self.transaction_id}, signer={self.signer})"
