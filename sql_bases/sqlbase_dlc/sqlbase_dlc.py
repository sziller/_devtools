import time
import logging
from sqlalchemy import Column, Integer, String, JSON, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from typing import Dict, Optional, Any
from cryptography import HashFunctions as HaFu
import hashlib  # Replace HaFu with hashlib if needed

Base = declarative_base()

# Setting up logger                                         logger                      -   START   -
lg = logging.getLogger(__name__)
# Setting up logger                                         logger                      -   ENDED   -


class DLC:
    """Logical DLC for shared fields."""
    dlc_id: str
    tmp_cntr_id: str
    ini_pubkey: str
    ini_pubkey_funding: str
    ini_payout_spk: str
    ini_payout_serial_id: int
    ini_change_spk: str
    acc_pubkey: Optional[str]
    acc_pubkey_funding: str
    acc_payout_spk: str
    acc_payout_serial_id: int
    acc_change_spk: str
    orcl_id: str
    cntr_terms: Dict[str, Any]
    cntr_flags: int
    chain_hash: str
    ini_signatures: Optional[Dict[str, Any]]
    acc_signatures: Optional[Dict[str, Any]]
    created_at: Optional[float]
    updated_at: Optional[float]
    timeout_at: Optional[float]
    status: str
    protocol_version: int
    
    def __init__(
            self,
            dlc_id: str,
            tmp_cntr_id: str,
            ini_pubkey: str,
            ini_pubkey_funding: str,
            ini_payout_spk: str,
            ini_payout_serial_id: int,
            ini_change_spk: str,
            acc_pubkey: Optional[str],
            acc_pubkey_funding: str,
            acc_payout_spk: str,
            acc_payout_serial_id: int,
            acc_change_spk: str,
            orcl_id: str,
            cntr_terms: Dict[str, Any],
            cntr_flags: int,
            chain_hash: str,
            ini_signatures: Optional[Dict[str, Any]] = None,
            acc_signatures: Optional[Dict[str, Any]] = None,
            created_at: Optional[float] = None,
            updated_at: Optional[float] = None,
            timeout_at: Optional[float] = None,
            status: str = "created",
            protocol_version: int = 1
    ):
        self.dlc_id = dlc_id
        self.tmp_cntr_id = tmp_cntr_id
        self.ini_pubkey = ini_pubkey
        self.ini_pubkey_funding = ini_pubkey_funding
        self.ini_payout_spk = ini_payout_spk
        self.ini_payout_serial_id = ini_payout_serial_id
        self.ini_change_spk = ini_change_spk
        self.acc_pubkey = acc_pubkey
        self.acc_pubkey_funding = acc_pubkey_funding
        self.acc_payout_spk = acc_payout_spk
        self.acc_payout_serial_id = acc_payout_serial_id
        self.acc_change_spk = acc_change_spk
        self.orcl_id = orcl_id
        self.cntr_terms = cntr_terms
        self.cntr_flags = cntr_flags
        self.chain_hash = chain_hash
        self.ini_signatures = ini_signatures or {}
        self.acc_signatures = acc_signatures or {}
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or time.time()
        self.timeout_at = timeout_at
        self.status = status
        self.protocol_version = protocol_version


class DLCP(DLC):
    """DLCP adds acceptor details, pubkeys, and status."""
    ini_email: str
    acc_email: Optional[str]
    outcome_time: Optional[float]

    def __init__(self,
                 ini_email: str,
                 acc_email: Optional[str] = None,
                 outcome_time: Optional[float] = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ini_email = ini_email
        self.acc_email = acc_email
        self.outcome_time = outcome_time


class LendBorrowBTCUSD_Product(DLCP, Base):
    """Database Table for the fully extended Lend-Borrow Product."""
    __tablename__ = "lb_btcusd_products"

    dlc_id                  = Column("dlc_id",                  String, primary_key=True)
    tmp_cntr_id             = Column("tmp_cntr_id",             String)
    ini_pubkey              = Column("ini_pubkey",              String)
    ini_pubkey_funding      = Column("ini_pubkey_funding",      String,     nullable=False)
    ini_payout_spk          = Column("ini_payout_spk",          String,     nullable=False)
    ini_payout_serial_id    = Column("ini_payout_serial_id",    Integer,    nullable=False)
    ini_change_spk          = Column("ini_change_spk",          String,     nullable=True)
    ini_change_serial_id    = Column("ini_change_serial_id",    Integer,    nullable=True)
    acc_pubkey              = Column("acc_pubkey",              String,     nullable=True)
    acc_pubkey_funding      = Column("acc_pubkey_funding",      String,     nullable=False)
    acc_payout_spk          = Column("acc_payout_spk",          String,     nullable=True)
    acc_payout_serial_id    = Column("acc_payout_serial_id",    Integer,    nullable=True)
    acc_change_spk          = Column("acc_change_spk",          String,     nullable=True)
    acc_change_serial_id    = Column("acc_change_serial_id",    Integer,    nullable=True)
    orcl_id                 = Column("orcl_id",                 String)
    cntr_terms              = Column("cntr_terms",              JSON)
    cntr_flags              = Column("cntr_flags",              Integer,    nullable=False, default=0)
    chain_hash              = Column("chain_hash",              String(64), nullable=False)
    ini_signatures          = Column("ini_signatures",          JSON,       nullable=True)
    acc_signatures          = Column("acc_signatures",          JSON,       nullable=True)
    created_at              = Column("created_at",              Float,                      default=time.time)
    updated_at              = Column("updated_at",              Float,                      default=time.time)
    timeout_at              = Column("timeout_at",              Float,      nullable=True)
    status                  = Column("status",                  String,     nullable=False, default="created")
    protocol_version        = Column("protocol_version",        Integer,    nullable=False, default=1)

    ini_email               = Column("ini_email",               String)
    acc_email               = Column("acc_email",               String,     nullable=True)
    outcome_time            = Column("outcome_time",            Float,      nullable=True)  # Time of resolution

    loan_amount             = Column("loan_amount",             Float,      nullable=False)  # Loan amount
    collateral_percent      = Column("collateral_percent",      Float,      nullable=False)  # Collateral %
    duration                = Column("duration",                Integer,    nullable=False)  # Duration in days
    funding_inputs          = Column("funding_inputs",          JSON,       nullable=True)  # Funding inputs
    funding_txid            = Column("funding_txid",            String,     nullable=True)  # Funding TX ID
    outcome_txid            = Column("outcome_txid",            String,     nullable=True)  # Outcome TX ID

    def generate_id_hash(self) -> str:
        """Function generates a unique ID for the DLC row"""
        new_hash = HaFu.single_sha256_byte2byte(bytes(
            f"{self.tmp_cntr_id}{self.created_at}",
            "utf-8")).hex()[:16]
        lg.warning(f"hash OLD  : {new_hash}")
        new_hash = hashlib.sha256(
            f"{self.tmp_cntr_id}{self.created_at}".encode("utf-8")
        ).hexdigest()[:16]
        lg.warning(f"hash NEW  : {new_hash}")
        return new_hash

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
    def construct(cls, d_in: Dict[str, Any]) -> "LendBorrowBTCUSD_Product":
        """Constructs an instance of the class from a dictionary."""
        valid_keys = {c.name for c in cls.__table__.columns}
        filtered_data = {k: v for k, v in d_in.items() if k in valid_keys}
        if set(d_in.keys()) - valid_keys:
            msg = f"Invalid keys in input: {set(d_in.keys()) - valid_keys}"
            lg.critical(msg)
            raise ValueError(msg)
        return cls(**filtered_data)
    
