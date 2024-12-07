import time
from sqlalchemy import Column, Integer, String, JSON, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from typing import Dict, Optional, Any
from cryptography import HashFunctions as HaFu

Base = declarative_base()


class BaseDLC:
    """Logical Base Class for shared fields."""
    dlc_id: str                     = Column(String, primary_key=True)  # Unique ID for the DLC
    temporary_contract_id: str      = Column(String)  # Temporary contract ID
    initiator_email: str            = Column(String)  # Email of the initiator
    initiator_pubkey: str           = Column(String)  # Public key of the initiator
    oracle_id: str                  = Column(String)  # Identifier of the oracle
    contract_terms: Dict[str, Any]  = Column(JSON)  # Contract terms in JSON format
    created_at: float               = Column(Float)  # Timestamp for creation
    updated_at: float               = Column(Float)  # Timestamp for the last update

    def __init__(
        self,
        temporary_contract_id: str,
        initiator_email: str,
        initiator_pubkey: str,
        oracle_id: str,
        contract_terms: Dict[str, Any],
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
    ):
        self.dlc_id = f"{temporary_contract_id}-{oracle_id}"  # Example ID generation
        self.temporary_contract_id = temporary_contract_id
        self.initiator_email = initiator_email
        self.initiator_pubkey = initiator_pubkey
        self.oracle_id = oracle_id
        self.contract_terms = contract_terms
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or time.time()


class DLCP(BaseDLC):
    """DLCP adds acceptor details, pubkeys, and status."""
    acceptor_email: Optional[str] = Column(String, nullable=True)  # Email of the acceptor
    acceptor_pubkey: Optional[str] = Column(String, nullable=True)  # Public key of the acceptor
    status: str = Column(String, default="created")  # Status of the DLC
    initiator_signatures: Optional[Dict[str, Any]] = Column(JSON, nullable=True)  # Initiator's signatures
    acceptor_signatures: Optional[Dict[str, Any]] = Column(JSON, nullable=True)  # Acceptor's signatures

    def __init__(
        self,
        temporary_contract_id: str,
        initiator_email: str,
        initiator_pubkey: str,
        oracle_id: str,
        contract_terms: Dict[str, Any],
        status: str = "created",
        acceptor_email: Optional[str] = None,
        acceptor_pubkey: Optional[str] = None,
        initiator_signatures: Optional[Dict[str, Any]] = None,
        acceptor_signatures: Optional[Dict[str, Any]] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
    ):
        super().__init__(
            temporary_contract_id, initiator_email, initiator_pubkey, oracle_id, contract_terms, created_at, updated_at
        )
        self.status = status
        self.acceptor_email = acceptor_email
        self.acceptor_pubkey = acceptor_pubkey
        self.initiator_signatures = initiator_signatures or {}
        self.acceptor_signatures = acceptor_signatures or {}


class LendBorrowProduct(DLCP, Base):
    """Database Table for the fully extended Lend-Borrow Product."""
    __tablename__ = "lend_borrow_products"

    loan_amount: float = Column(Float, nullable=False)  # Loan amount
    collateral_percent: float = Column(Float, nullable=False)  # Collateral percentage
    duration: int = Column(Integer, nullable=False)  # Duration in days
    funding_inputs: Optional[Dict[str, Any]] = Column(JSON, nullable=True)  # Funding inputs
    funding_txid: Optional[str] = Column(String, nullable=True)  # Funding transaction ID
    outcome_txid: Optional[str] = Column(String, nullable=True)  # Outcome transaction ID
    timeout_at: Optional[float] = Column(Float, nullable=True)  # Timeout timestamp

    def __init__(
        self,
        temporary_contract_id: str,
        initiator_email: str,
        initiator_pubkey: str,
        oracle_id: str,
        contract_terms: Dict[str, Any],
        loan_amount: float,
        collateral_percent: float,
        duration: int,
        status: str = "created",
        acceptor_email: Optional[str] = None,
        acceptor_pubkey: Optional[str] = None,
        initiator_signatures: Optional[Dict[str, Any]] = None,
        acceptor_signatures: Optional[Dict[str, Any]] = None,
        funding_inputs: Optional[Dict[str, Any]] = None,
        funding_txid: Optional[str] = None,
        outcome_txid: Optional[str] = None,
        timeout_at: Optional[float] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
    ):
        super().__init__(
            temporary_contract_id,
            initiator_email,
            initiator_pubkey,
            oracle_id,
            contract_terms,
            status,
            acceptor_email,
            acceptor_pubkey,
            initiator_signatures,
            acceptor_signatures,
            created_at,
            updated_at,
        )
        self.loan_amount = loan_amount
        self.collateral_percent = collateral_percent
        self.duration = duration
        self.funding_inputs = funding_inputs or {}
        self.funding_txid = funding_txid
        self.outcome_txid = outcome_txid
        self.timeout_at = timeout_at
    
    def generate_id_hash(self):
        """Function generates a unique ID for the DLC row"""
        return HaFu.single_sha256_byte2byte(bytes(
            f"{self.temporary_contract_id}{self.created_at}",
            "utf-8")).hex()[:16]
    
    def return_as_dict(self) -> Dict[str, Any]:
        """Returns the instance as a dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def update(self, **kwargs) -> None:
        """Updates the instance attributes."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = time.time()  # Automatically update the timestamp
    
    def calculate_collateral(self) -> float:
        """Calculates the collateral amount based on loan and collateral percentage."""
        return self.loan_amount * (self.collateral_percent / 100)

    def __repr__(self) -> str:
        return (f"LendBorrowProduct | DLC ID: {self.dlc_id} | Status: {self.status} | "
                f"Loan: {self.loan_amount}, Collateral: {self.collateral_percent}%, "
                f"Duration: {self.duration} days")
    
    @classmethod
    def construct(cls, d_in):
        """Constructs an instance of the class from a dictionary"""
        return cls(**d_in)
    
