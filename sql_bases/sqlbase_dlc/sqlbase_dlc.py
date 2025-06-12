"""
DLCP used DLC Base(es)
by Sziller """

import time
import logging
from sqlalchemy import Column, Integer, String, JSON, Float
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
    
    ini_pubkey_funding: Optional[str]
    ini_payout_spk: Optional[str]
    ini_payout_ser_id: Optional[int]
    ini_change_spk: Optional[str]
    ini_change_ser_id: Optional[int]
    ini_fund_output_ser_id: Optional[int]
    ini_num_funding_inputs: Optional[int]
    ini_collateral_sats: Optional[int]
    ini_signatures: Optional[Dict[str, Any]]
    
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
    orcl_pubkey: Optional[str]
    digit_string_template: Optional[str]
    nonces: Optional[str]
    interval_wildcards: Optional[str]
    num_digits: Optional[int]
    # -----------------------------------------------------------
    orcl_event_id: Optional[str]
    orcl_event_time: Optional[int]
    orcl_poll_at: Optional[int]
    orcl_final_value: Optional[int]
    orcl_outcome_time: Optional[int]
    orcl_signatures: Optional[str]
    orcl_outcome_digits_json: Optional[Dict[str, Any]]
    orcl_outcome_url: Optional[str]
    orcl_outcome_at: Optional[str]

    final_interval: Optional[str]
    
    cntr_terms: Optional[Dict[str, Any]]
    feerate_per_vb: Optional[int]
    cet_locktime: Optional[int]
    refund_locktime: Optional[int]

    ftx_id: Optional[str]
    rtx_id: Optional[str]
    cet_id: Optional[str]
    funding_inputs: Optional[Dict[str, Any]]
    
    offered_at: Optional[float]  # when the odder is placed by the Initiator
    accepted_at: Optional[float]  # when the offer is accepted by the Acceptor
    signed_ini_at: Optional[float]  # when the deal (accepted offer) is signed by the Initiator
    signed_acc_at: Optional[float]  # when the deal (accepted offer) is signed by the Acceptor
    broadcast_ftx_at: Optional[int]
    broadcast_cet_at: Optional[int]
    broadcast_rtx_at: Optional[int]
    confirmed_cet_at: Optional[int]
    confirmed_ftx_at: Optional[int]
    confirmed_rtx_at: Optional[int]
    attest_at: Optional[float]  # when the Oracle attested to the result
    refund_at: Optional[float]  # when possible refund is due
    
    def __init__(
            self,
            tmp_cntr_id: str,                       # created
            created_at: Optional[float] = None,     # created
            updated_at: Optional[float] = None,     # ALWAYS
            status: str = "created",                # ALWAYS
            protocol_version: int = 1,              # created
            chain_hash: str = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",   # created, offer_dlc
            cntr_flags: int = 0,                                                                    # created, offer_dlc
            dlc_id: Optional[str] = None,                                                           # created, offer_dlc
            
            ini_pubkey_funding: Optional[str] = None,
            ini_payout_spk: Optional[str] = None,
            ini_payout_ser_id: Optional[int] = None,
            ini_change_spk: Optional[str] = None,
            ini_change_ser_id: Optional[int] = None,
            ini_fund_output_ser_id: Optional[int] = None,
            ini_num_funding_inputs: Optional[int] = None,
            ini_collateral_sats: Optional[int] = None,
            ini_signatures: Optional[Dict[str, Any]] = None,
            
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
            orcl_pubkey: Optional[str] = None,
            digit_string_template: Optional[str] = None,
            nonces: Optional[str] = None,
            interval_wildcards: Optional[str] = None,
            num_digits: Optional[int] = None,
            # ---------------------------------------------------------------
            orcl_event_id: Optional[str] = None,
            orcl_event_time: Optional[int] = None,

            orcl_poll_at: Optional[int] = None,
            orcl_final_value: Optional[int] = None,
            orcl_outcome_time: Optional[int] = None,
            orcl_signatures: Optional[str] = None,
            orcl_outcome_digits_json: Optional[Dict[str, Any]] = None,
            orcl_outcome_url: Optional[str] = None,
            orcl_outcome_at: Optional[str] = None,

            final_interval: Optional[str] = None,
            
            cntr_terms: Optional[Dict[str, Any]] = None,
            feerate_per_vb: Optional[int] = None,
            cet_locktime: Optional[int] = None,
            refund_locktime: Optional[int] = None,

            ftx_id: Optional[str] = None,
            rtx_id: Optional[str] = None,
            cet_id: Optional[str] = None,
            funding_inputs: Optional[Dict[str, Any]] = None,
            
            offered_at: Optional[float] = None,
            accepted_at: Optional[float] = None,
            signed_ini_at: Optional[float] = None,
            signed_acc_at: Optional[float] = None,
            broadcast_ftx_at: Optional[int] = None,
            broadcast_cet_at: Optional[int] = None,
            broadcast_rtx_at: Optional[int] = None,
            confirmed_cet_at: Optional[int] = None,
            confirmed_ftx_at: Optional[int] = None,
            confirmed_rtx_at: Optional[int] = None,
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
        
        self.ini_pubkey_funding = ini_pubkey_funding
        self.ini_payout_spk = ini_payout_spk
        self.ini_payout_ser_id = ini_payout_ser_id
        self.ini_change_spk = ini_change_spk
        self.ini_change_ser_id = ini_change_ser_id
        self.ini_fund_output_ser_id = ini_fund_output_ser_id
        self.ini_num_funding_inputs = ini_num_funding_inputs
        self.ini_collateral_sats = ini_collateral_sats
        self.ini_signatures = ini_signatures or {}
        
        self.acc_pubkey_funding = acc_pubkey_funding
        self.acc_payout_spk = acc_payout_spk
        self.acc_payout_ser_id = acc_payout_ser_id
        self.acc_change_spk = acc_change_spk
        self.acc_change_ser_id = acc_change_ser_id
        self.acc_fund_output_ser_id = acc_fund_output_ser_id
        self.acc_num_funding_inputs = acc_num_funding_inputs
        self.acc_collateral_sats = acc_collateral_sats
        self.acc_signatures = acc_signatures or {}
        
        self.orcl_id                    = orcl_id
        self.orcl_pubkey                = orcl_pubkey
        self.digit_string_template      = digit_string_template
        self.nonces                     = nonces
        self.interval_wildcards         = interval_wildcards
        self.num_digits                 = num_digits

        self.orcl_event_id              = orcl_event_id
        self.orcl_event_time            = orcl_event_time

        self.orcl_poll_at               = orcl_poll_at
        self.orcl_final_value           = orcl_final_value
        self.orcl_outcome_time          = orcl_outcome_time
        self.orcl_signatures            = orcl_signatures
        self.orcl_outcome_digits_json   = orcl_outcome_digits_json or {}
        self.orcl_outcome_url           = orcl_outcome_url
        self.orcl_outcome_at            = orcl_outcome_at

        self.final_interval             = final_interval
        
        self.cntr_terms             = cntr_terms or {}
        self.feerate_per_vb         = feerate_per_vb
        self.cet_locktime           = cet_locktime
        self.refund_locktime        = refund_locktime

        self.ftx_id                 = ftx_id
        self.rtx_id                 = rtx_id
        self.cet_id                 = cet_id
        self.funding_inputs         = funding_inputs or {}
        
        self.offered_at             = offered_at
        self.accepted_at            = accepted_at
        self.signed_ini_at          = signed_ini_at
        self.signed_acc_at          = signed_acc_at
        self.broadcast_ftx_at       = broadcast_ftx_at
        self.broadcast_cet_at       = broadcast_cet_at
        self.broadcast_rtx_at       = broadcast_rtx_at
        self.confirmed_cet_at       = confirmed_cet_at
        self.confirmed_ftx_at       = confirmed_ftx_at
        self.confirmed_rtx_at       = confirmed_rtx_at
        self.attest_at              = attest_at
        self.refund_at              = refund_at
        

class DLCP(DLC):
    """DLCP adds acceptor details, pubkeys, and status."""
    product_id: str
    expiry_offer: Optional[int]
    ini_email: Optional[str]
    acc_email: Optional[str]
    ini_pubkey_index: Optional[int]
    acc_pubkey_index: Optional[int]
    
    def __init__(self,
                 product_id: str = "dlcp",
                 expiry_offer: Optional[int] = None,
                 ini_email: Optional[str] = None,
                 acc_email: Optional[str] = None,
                 ini_pubkey_index: Optional[int] = None,
                 acc_pubkey_index: Optional[int] = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.product_id         = product_id
        self.expiry_offer       = expiry_offer
        self.ini_email          = ini_email
        self.acc_email          = acc_email
        self.ini_pubkey_index   = ini_pubkey_index
        self.acc_pubkey_index   = acc_pubkey_index


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
    
    ini_pubkey_funding          = Column("ini_pubkey_funding",          String,     nullable=True)
    ini_pubkey_index            = Column("ini_pubkey_index",            Integer,    nullable=True)
    ini_payout_spk              = Column("ini_payout_spk",              String,     nullable=True)
    ini_payout_ser_id           = Column("ini_payout_ser_id",           Integer,    nullable=True)
    ini_change_spk              = Column("ini_change_spk",              String,     nullable=True)
    ini_change_ser_id           = Column("ini_change_ser_id",           Integer,    nullable=True)
    ini_fund_output_ser_id      = Column("ini_fund_output_ser_id",      Integer,    nullable=True)
    ini_num_funding_inputs      = Column("ini_num_funding_inputs",      Integer,    nullable=True)
    ini_collateral_sats         = Column("ini_collateral_sats",         Integer,    nullable=True)
    ini_signatures              = Column("ini_signatures",              JSON,       nullable=True, default=dict)
            
    acc_pubkey_funding          = Column("acc_pubkey_funding",          String,     nullable=True)
    acc_pubkey_index            = Column("acc_pubkey_index",            Integer,    nullable=True)
    acc_payout_spk              = Column("acc_payout_spk",              String,     nullable=True)
    acc_payout_ser_id           = Column("acc_payout_ser_id",           Integer,    nullable=True)
    acc_change_spk              = Column("acc_change_spk",              String,     nullable=True)
    acc_change_ser_id           = Column("acc_change_ser_id",           Integer,    nullable=True)
    acc_fund_output_ser_id      = Column("acc_fund_output_ser_id",      Integer,    nullable=True)
    acc_num_funding_inputs      = Column("acc_num_funding_inputs",      Integer,    nullable=True)
    acc_collateral_sats         = Column("acc_collateral_sats",         Integer,    nullable=True)
    acc_signatures              = Column("acc_signatures",              JSON,       nullable=True, default=dict)
        
    orcl_id                     = Column("orcl_id",                     String,     nullable=True)
    orcl_pubkey                 = Column("orcl_pubkey",                 String,     nullable=True)
    digit_string_template       = Column("digit_string_template",       String,     nullable=True)
    nonces                      = Column("nonces",                      String,     nullable=True)
    interval_wildcards          = Column("interval_wildcards",          String,     nullable=True)
    num_digits                  = Column("num_digits",                  Integer,    nullable=True)
        
    orcl_event_id               = Column("orcl_event_id",               String,     nullable=True)
    orcl_event_time             = Column("orcl_event_time",             String,     nullable=True)
    orcl_poll_at                = Column("orcl_poll_at",                String,     nullable=True)
    orcl_final_value            = Column("orcl_final_value",            String,     nullable=True)
    orcl_outcome_time           = Column("orcl_outcome_time",           String,     nullable=True)
    orcl_signatures             = Column("orcl_signatures",             String,     nullable=True)
    orcl_outcome_digits_json    = Column("orcl_outcome_digits_json",    JSON,       nullable=True, default=dict)
    orcl_outcome_url            = Column("orcl_outcome_url",            String,     nullable=True)
    orcl_outcome_at             = Column("orcl_outcome_at",             String,     nullable=True)
        
    cntr_terms                  = Column("cntr_terms",                  JSON,       nullable=True, default=dict)
    feerate_per_vb              = Column("feerate_per_vb",              Integer,    nullable=True)
    cet_locktime                = Column("cet_locktime",                Integer,    nullable=True)
    refund_locktime             = Column("refund_locktime",             Integer,    nullable=True)
        
    offered_at                  = Column("offered_at",                  Float,      nullable=True)
    accepted_at                 = Column("accepted_at",                 Float,      nullable=True)
    signed_ini_at               = Column("signed_ini_at",               Float,      nullable=True)
    signed_acc_at               = Column("signed_acc_at",               Float,      nullable=True)
    attest_at                   = Column("attest_at",                   Float,      nullable=True)
    refund_at                   = Column("refund_at",                   Float,      nullable=True)
        
    product_id                  = Column("product_id",                  String,     nullable=False)
    expiry_offer                = Column("expiry_offer",                Integer,    nullable=True)
    ini_email                   = Column("ini_email",                   String,     nullable=True)
    acc_email                   = Column("acc_email",                   String,     nullable=True)

    ftx_id                      = Column("ftx_id",                      String,     nullable=True)  # Funding TX ID
    rtx_id                      = Column("rtx_id",                      String,     nullable=True)  # Refund TX ID
    cet_id                      = Column("cet_id",                      String,     nullable=True)  # CET (valid) TX ID
    funding_inputs              = Column("funding_inputs",              JSON,       nullable=True, default=dict)
    broadcast_ftx_at            = Column("broadcast_ftx_at",            Integer,    nullable=True)
    broadcast_cet_at            = Column("broadcast_cet_at",            Integer,    nullable=True)
    broadcast_rtx_at            = Column("broadcast_rtx_at",            Integer,    nullable=True)
    confirmed_cet_at            = Column("confirmed_cet_at",            Integer,    nullable=True)
    confirmed_ftx_at            = Column("confirmed_ftx_at",            Integer,    nullable=True)
    confirmed_rtx_at            = Column("confirmed_rtx_at",            Integer,    nullable=True)
        
    ini_role                    = Column("ini_role",                    String,     nullable=True)  # 0: lend 1: borrow
    duration                    = Column("duration",                    Float,    nullable=True)  # Duration in days
    interest                    = Column("interest",                    Float,      nullable=True)
    interest_ear                = Column("interest_ear",                Float,      nullable=True)
    interest_b                  = Column("interest_b",                  Float,      nullable=True)
    interest_b_ear              = Column("interest_b_ear",              Float,      nullable=True)
    
    def __init__(self,
                 tmp_cntr_id: str,
                 product_id: str,
                 expiry_offer: Optional[int]                = None,
                 ini_role: Optional[str]                    = None,
                 duration: Optional[float]                  = None,
                 interest: Optional[float]                  = None,
                 interest_ear: Optional[float]              = None,
                 interest_b: Optional[float]                = None,
                 interest_b_ear: Optional[float]            = None,
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
    
