import time
import logging
from sqlalchemy import Column, Integer, String, JSON, Float, DateTime, Boolean
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
    dlc_id: Optional[str]
    tmp_cntr_id: str
    created_at: float
    updated_at: float
    status: str
    protocol_version: int
    chain_hash: str
    cntr_flags: int
    
    ini_pubkey: Optional[str]
    ini_pubkey_funding: Optional[str]
    ini_payout_spk: Optional[str]
    ini_payout_ser_id: Optional[int]
    ini_change_spk: Optional[str]
    ini_change_ser_id: Optional[int]
    ini_fund_output_ser_id: Optional[int]
    ini_num_funding_inputs: Optional[int]
    ini_collateral_sats: Optional[int]
    ini_signatures: Optional[Dict[str, Any]]
    
    acc_pubkey: Optional[str]
    acc_pubkey_funding: Optional[str]
    acc_payout_spk: Optional[str]
    acc_payout_ser_id: Optional[int]
    acc_change_spk: Optional[str]
    acc_change_ser_id: Optional[int]
    acc_fund_output_ser_id: Optional[int]
    acc_num_funding_inputs: Optional[int]
    acc_collateral_sats: Optional[int]
    acc_signatures: Optional[Dict[str, Any]]
    
    orcl_id: Optional[str]
    cntr_terms: Dict[str, Any]
    feerate_per_vb: Optional[int]
    cet_locktime: Optional[int]
    refund_locktime: Optional[int]
    
    offered_at: Optional[float]
    attest_at: Optional[float]
    refund_at: Optional[float]
    
    def __init__(
            self,
            tmp_cntr_id: str,                       # created
            created_at: Optional[float] = None,     # created
            updated_at: Optional[float] = None,     #               ALWAYS
            status: str = "created",                #               ALWAYS
            protocol_version: int = 1,              # created
            chain_hash: str = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",   # created, offer_dlc
            cntr_flags: int = 0,                                                                    # created, offer_dlc
            dlc_id: Optional[str] = None,                                                           # created, offer_dlc
            
            ini_pubkey: Optional[str] = None,
            ini_pubkey_funding: Optional[str] = None,
            ini_payout_spk: Optional[str] = None,
            ini_payout_ser_id: Optional[int] = None,
            ini_change_spk: Optional[str] = None,
            ini_change_ser_id: Optional[int] = None,
            ini_fund_output_ser_id: Optional[int] = None,
            ini_num_funding_inputs: Optional[int] = None,
            ini_collateral_sats: Optional[int] = None,
            ini_signatures: Optional[Dict[str, Any]] = None,
            
            acc_pubkey: Optional[str] = None,
            acc_pubkey_funding: Optional[str] = None,
            acc_payout_spk: Optional[str] = None,
            acc_payout_ser_id: Optional[int] = None,
            acc_change_spk: Optional[str] = None,
            acc_change_ser_id: Optional[int] = None,
            acc_fund_output_ser_id: Optional[int] = None,
            acc_num_funding_inputs: Optional[int] = None,
            acc_collateral_sats: Optional[int] = None,
            acc_signatures: Optional[Dict[str, Any]] = None,
            
            orcl_id: Optional[str] = None,                                                          # offer_, offer_dlc
            cntr_terms: Dict[str, Any] = None,
            feerate_per_vb: Optional[int] = None,
            cet_locktime: Optional[int] = None,
            refund_locktime: Optional[int] = None,
            
            offered_at: Optional[float] = None,
            attest_at: Optional[float] = None,
            refund_at: Optional[float] = None,
            *args, **kwargs
    ):
        if not tmp_cntr_id:
            raise ValueError("tmp_cntr_id is required and cannot be empty.")
        self.dlc_id = dlc_id
        self.tmp_cntr_id = tmp_cntr_id
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or time.time()
        self.status = status
        self.protocol_version = protocol_version
        self.chain_hash = chain_hash
        self.cntr_flags = cntr_flags
        
        self.ini_pubkey = ini_pubkey
        self.ini_pubkey_funding = ini_pubkey_funding
        self.ini_payout_spk = ini_payout_spk
        self.ini_payout_ser_id = ini_payout_ser_id
        self.ini_change_spk = ini_change_spk
        self.ini_change_ser_id = ini_change_ser_id
        self.ini_fund_output_ser_id = ini_fund_output_ser_id
        self.ini_num_funding_inputs = ini_num_funding_inputs
        self.ini_collateral_sats = ini_collateral_sats
        self.ini_signatures = ini_signatures or {}
        
        self.acc_pubkey = acc_pubkey
        self.acc_pubkey_funding = acc_pubkey_funding
        self.acc_payout_spk = acc_payout_spk
        self.acc_payout_ser_id = acc_payout_ser_id
        self.acc_change_spk = acc_change_spk
        self.acc_change_ser_id = acc_change_ser_id
        self.acc_fund_output_ser_id = acc_fund_output_ser_id
        self.acc_num_funding_inputs = acc_num_funding_inputs
        self.acc_collateral_sats = acc_collateral_sats
        self.acc_signatures = acc_signatures or {}
        
        self.orcl_id = orcl_id
        self.cntr_terms = cntr_terms
        self.feerate_per_vb = feerate_per_vb
        self.cet_locktime = cet_locktime
        self.refund_locktime = refund_locktime
        
        self.offered_at = offered_at
        self.attest_at = attest_at
        self.refund_at = refund_at
        

class DLCP(DLC):
    """DLCP adds acceptor details, pubkeys, and status."""
    product_id: str
    expiry_offer: Optional[int]
    ini_email: Optional[str]
    acc_email: Optional[str]
    
    def __init__(self,
                 product_id: str = "dlcp",
                 expiry_offer: Optional[int] = None,
                 ini_email: Optional[str] = None,
                 acc_email: Optional[str] = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.product_id     = product_id
        self.expiry_offer   = expiry_offer
        self.ini_email      = ini_email
        self.acc_email      = acc_email


class LendBorrowBTCUSD_Product(DLCP, Base):
    """Database Table for the fully extended Lend-Borrow Product."""
    __tablename__ = "lb_btcusd_products"

    dlc_id                  = Column("dlc_id",                  String,     nullable=False, primary_key=True)
    tmp_cntr_id             = Column("tmp_cntr_id",             String,     nullable=False)
    created_at              = Column("created_at",              Float,      nullable=False, default=lambda: time.time())
    updated_at              = Column("updated_at",              Float,      nullable=False, default=lambda: time.time())
    status                  = Column("status",                  String,     nullable=False, default="created")
    protocol_version        = Column("protocol_version",        Integer,    nullable=False, default=1)
    chain_hash              = Column("chain_hash",              String(64), nullable=False,
                                     default="000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f")
    cntr_flags              = Column("cntr_flags", Integer, nullable=False, default=0)
    
    ini_pubkey              = Column("ini_pubkey",              String,     nullable=True)
    ini_pubkey_funding      = Column("ini_pubkey_funding",      String,     nullable=True)
    ini_payout_spk          = Column("ini_payout_spk",          String,     nullable=True)
    ini_payout_ser_id       = Column("ini_payout_ser_id",       Integer,    nullable=True)
    ini_change_spk          = Column("ini_change_spk",          String,     nullable=True)
    ini_change_ser_id       = Column("ini_change_ser_id",       Integer,    nullable=True)
    ini_fund_output_ser_id  = Column("ini_fund_output_ser_id",  Integer,    nullable=True)
    ini_num_funding_inputs  = Column("ini_num_funding_inputs",  Integer,    nullable=True)
    ini_collateral_sats     = Column("ini_collateral_sats",     Integer,    nullable=True)
    ini_signatures          = Column("ini_signatures",          JSON,       nullable=True, default=dict)
    
    acc_pubkey              = Column("acc_pubkey",              String,     nullable=True)
    acc_pubkey_funding      = Column("acc_pubkey_funding",      String,     nullable=True)
    acc_payout_spk          = Column("acc_payout_spk",          String,     nullable=True)
    acc_payout_ser_id       = Column("acc_payout_ser_id",       Integer,    nullable=True)
    acc_change_spk          = Column("acc_change_spk",          String,     nullable=True)
    acc_change_ser_id       = Column("acc_change_ser_id",       Integer,    nullable=True)
    acc_fund_output_ser_id  = Column("acc_fund_output_ser_id",  Integer,    nullable=True)
    acc_num_funding_inputs  = Column("acc_num_funding_inputs",  Integer,    nullable=True)
    acc_collateral_sats     = Column("acc_collateral_sats",     Integer,    nullable=True)
    acc_signatures          = Column("acc_signatures",          JSON,       nullable=True, default=dict)
    
    orcl_id                 = Column("orcl_id",                 String,     nullable=True)
    cntr_terms              = Column("cntr_terms",              JSON,       nullable=True)
    feerate_per_vb          = Column("feerate_per_vb",          Integer,    nullable=True)
    cet_locktime            = Column("cet_locktime",            Integer,    nullable=True)
    refund_locktime         = Column("refund_locktime",         Integer,    nullable=True)

    offered_at              = Column("offered_at",              Float,      nullable=True)
    attest_at               = Column("attest_at",               Float,      nullable=True)
    refund_at               = Column("refund_at",               Float,      nullable=True)
    
    product_id              = Column("product_id",              String,     nullable=False)
    expiry_offer            = Column("expiry_offer",            Integer,    nullable=True)
    ini_email               = Column("ini_email",               String,     nullable=True)
    acc_email               = Column("acc_email",               String,     nullable=True)
    
    ini_role                = Column("ini_role",                String,     nullable=True)  # 0: lend 1: borrow
    # loan_sats               = Column("loan_sats",               Integer,    nullable=True)  # Loan amount
    # collateral_sats         = Column("collateral_sats",         Integer,    nullable=True)  # Collateral amount
    duration                = Column("duration",                Integer,    nullable=True)  # Duration in days
    interest                = Column("interest",                Float,      nullable=True)
    interest_ear            = Column("interest_ear",            Float,      nullable=True)
    interest_b              = Column("interest_b",              Float,      nullable=True)
    interest_b_ear          = Column("interest_b_ear",          Float,      nullable=True)
    funding_inputs          = Column("funding_inputs",          JSON,       nullable=True, default=dict)
    funding_txid            = Column("funding_txid",            String,     nullable=True)  # Funding TX ID
    outcome_txid            = Column("outcome_txid",            String,     nullable=True)  # Outcome TX ID
    timer_a_start           = Column("timer_a_start",           Float,      nullable=True)  # Timestamp for Timer_A
    timer_b_start           = Column("timer_b_start",           Float,      nullable=True)  # Timestamp for Timer_B
    timer_b_duration        = Column("timer_b_duration",        Integer,    nullable=False, default=300)  # Duration in seconds (default: 5 minutes)
    timer_b_active          = Column("timer_b_active",          Boolean,    nullable=False, default=True)  # Indicates if Timer_B is active

    def __init__(self,
                 tmp_cntr_id: str,
                 product_id: str,
                 expiry_offer: Optional[int]                = None,
                 ini_role: Optional[str]                    = None,
                 # loan_sats: Optional[int]                   = None,
                 # collateral_sats: Optional[int]             = None,
                 duration: Optional[int]                    = None,
                 interest: Optional[float]                  = None,
                 interest_ear: Optional[float]              = None,
                 interest_b: Optional[float]                = None,
                 interest_b_ear: Optional[float]            = None,
                 funding_inputs: Optional[Dict[str, Any]]   = None,
                 funding_txid: Optional[str]                = None,
                 outcome_txid: Optional[str]                = None,
                 timer_a_start: Optional[float]             = None,  # Timestamp for Timer_A
                 timer_b_start: Optional[float]             = None,  # Timestamp for Timer_B
                 timer_b_duration: int                      = 300,
                 timer_b_active: bool                       = True,
                 *args,
                 **kwargs):
        """
        Override the constructor to ensure dlc_id gets the value of tmp_cntr_id if not provided.
        """
        # mandatory argument passing
        kwargs["tmp_cntr_id"]       = tmp_cntr_id
        kwargs["dlc_id"]            = tmp_cntr_id  # Assign tmp_cntr_id to dlc_id if dlc_id not explicitly provided!!!
        kwargs["product_id"]        = product_id
        super().__init__(*args, **kwargs)
        
        # Initialize LendBorrowBTCUSD_Product-specific attributes
        self.expiry_offer       = expiry_offer
        self.ini_role           = ini_role
        self.duration           = duration
        self.interest           = interest
        self.interest_ear       = interest_ear
        self.interest_b         = interest_b
        self.interest_b_ear     = interest_b_ear
        self.funding_inputs     = funding_inputs
        self.funding_txid       = funding_txid
        self.outcome_txid       = outcome_txid
        self.timer_a_start      = timer_a_start
        self.timer_b_start      = timer_b_start
        self.timer_b_duration   = timer_b_duration
        self.timer_b_active     = timer_b_active

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

    def __repr__(self) -> str:
        return (f"LendBorrowProduct | DLC ID: {self.dlc_id} | Status: {self.status} | "
                f"Duration: {self.duration} days")

    @classmethod
    def construct(cls, d_in: Dict[str, Any]) -> "LendBorrowBTCUSD_Product":
        """Construct an instance from a dictionary."""
        valid_keys = {c.name for c in cls.__table__.columns}
        filtered_data = {k: v for k, v in d_in.items() if k in valid_keys}

        # Enforce tmp_cntr_id presence
        if "tmp_cntr_id" not in filtered_data or not filtered_data["tmp_cntr_id"]:
            raise ValueError("Missing required field: tmp_cntr_id")

        # Derive dlc_id from tmp_cntr_id
        filtered_data["dlc_id"] = filtered_data["tmp_cntr_id"]

        return cls(**filtered_data)
    
