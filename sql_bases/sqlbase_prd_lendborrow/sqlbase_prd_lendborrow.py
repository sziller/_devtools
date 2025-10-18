"""
SQLAlchemy powered DB Base for Product Details used by DLCPlaza.
Portable JSON field: SQLite now, PostgreSQL JSONB later (no code changes needed).
by Sziller
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List

from sqlalchemy import (
    Column, String, Integer, Float, BigInteger, SmallInteger,
    DateTime, func, JSON, CheckConstraint
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import declarative_base, Session

Base = declarative_base()

# Logger setup
lg = logging.getLogger(__name__)


class ProductLendBorrow(Base):
    """=== Classname: ProductLendBorrow(Base) ==========================================================================
    Stores immutable/semistatic product parameter-sets for DLC products
    (e.g., 'LendBorrowBTCUSD:ltv-80_d-90').
    Each row corresponds to one product key and contains all parameters required by the engine and FE.
    ============================================================================================== by Sziller ==="""
    __tablename__ = "products_lendborrow"

    __table_args__ = (
        # Data hygiene constraints
        CheckConstraint("duration > 0", name="ck_products_lendborrow_duration_pos"),
        CheckConstraint("ltv >= 0 AND ltv <= 100", name="ck_products_lendborrow_ltv_0_100"),
        CheckConstraint("service_fee_percent >= 0 AND service_fee_percent <= 100",
                        name="ck_products_lendborrow_fee_0_100"),
        CheckConstraint("service_fee_split_percent >= 0 AND service_fee_split_percent <= 100",
                        name="ck_products_lendborrow_fee_split_0_100"),
        CheckConstraint("contract_value >= 0", name="ck_products_lendborrow_contract_value_nonneg"),
        CheckConstraint("payout_boost_sats >= 0", name="ck_products_lendborrow_payout_boost_nonneg"),
        CheckConstraint("num_digits >= 0", name="ck_products_lendborrow_num_digits_nonneg"),
    )

    # Primary identity
    product_id: str = Column(String, primary_key=True)  # e.g. 'LendBorrowBTCUSD:ltv-80_d-90'

    # Core parameters (mirrors your dict keys exactly)
    ltv: float              = Column(Float,  nullable=False)     # 80.0
    duration: float         = Column(Float,  nullable=False)     # 0.02, 0.03 (NO ZERO)

    # Portable JSON: lists on SQLite today; becomes JSONB on PostgreSQL automatically
    orcl_id: List[str] = Column(
        MutableList.as_mutable(
            JSON().with_variant(postgresql.JSONB, "postgresql")
        ),
        nullable=False,
        default=list  # Python-side default keeps it portable across SQLite/PG
    )  # e.g. ["oracle_dlcp"]

    # Timers (match dict: integers)
    expiry_offer_default_hours: int = Column(Integer, nullable=False)  # 168
    expiry_deal_acc_minutes: int    = Column(Integer, nullable=False)  # 60
    expiry_deal_ini_minutes: int    = Column(Integer, nullable=False)  # 120
    refund_delay_days: int          = Column(Integer, nullable=False)  # 30

    # Monetary-ish values
    contract_value: int         = Column(BigInteger, nullable=False)   # 100_000 (use BigInteger for headroom)
    payout_boost_sats: int      = Column(BigInteger, nullable=False)   # 500

    # Function paths (kept as strings)
    interest_ear: str           = Column(String, nullable=False)       # 'dlc_plaza_engine.calcs.calc_ear_from_interest'
    interest_b: str             = Column(String, nullable=False)       # 'dlc_plaza_engine.calcs.calc_actual_interest'
    interest_b_ear: str         = Column(String, nullable=False)       # 'dlc_plaza_engine.calcs.calc_ear_from_interest'
    free_loan: str              = Column(String, nullable=False)       # 'dlc_plaza_engine.calcs.calc_free_loan_using_interest'
    loan_sats: str              = Column(String, nullable=False)       # 'dlc_plaza_engine.calcs.calc_loan_from_data'

    # Fees and display helpers
    service_fee_percent: float      = Column(Float, nullable=False)      # 0.25
    service_fee_split_percent: int  = Column(Integer, nullable=False)      # 30
    num_digits: int                 = Column(SmallInteger, nullable=False) # 7

    # Bookkeeping (timezone-aware)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- Helpers ---------------------------------------------------------------------------------------------------- #
    def return_as_dict(self) -> Dict[str, Any]:
        """Return instance as a plain dict (safe for JSON responses)."""
        return {
            "product_id": self.product_id,
            "ltv": self.ltv,
            "duration": self.duration,
            "orcl_id": self.orcl_id,
            "expiry_offer_default_hours": self.expiry_offer_default_hours,
            "expiry_deal_acc_minutes": self.expiry_deal_acc_minutes,
            "expiry_deal_ini_minutes": self.expiry_deal_ini_minutes,
            "refund_delay_days": self.refund_delay_days,
            "contract_value": self.contract_value,
            "interest_ear": self.interest_ear,
            "interest_b": self.interest_b,
            "interest_b_ear": self.interest_b_ear,
            "free_loan": self.free_loan,
            "loan_sats": self.loan_sats,
            "service_fee_percent": self.service_fee_percent,
            "service_fee_split_percent": self.service_fee_split_percent,
            "payout_boost_sats": self.payout_boost_sats,
            "num_digits": self.num_digits,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def __repr__(self):
        return f"ProductLendBorrow(product_id={self.product_id}, ltv={self.ltv}, duration={self.duration})"

    # Optional: convenience loader for your exact dict structure
    @classmethod
    def from_key_and_payload(cls, product_key: str, d: Dict[str, Any]) -> ProductLendBorrow:
        """Create an instance from (key, dict) exactly like your provided config."""
        return cls(
            product_id=product_key,
            ltv=d["ltv"],
            duration=d["duration"],
            orcl_id=list(d.get("orcl_id", [])),
            expiry_offer_default_hours=d["expiry_offer_default_hours"],
            expiry_deal_acc_minutes=d["expiry_deal_acc_minutes"],
            expiry_deal_ini_minutes=d["expiry_deal_ini_minutes"],
            refund_delay_days=d["refund_delay_days"],
            contract_value=d["contract_value"],
            interest_ear=d["interest_ear"],
            interest_b=d["interest_b"],
            interest_b_ear=d["interest_b_ear"],
            free_loan=d["free_loan"],
            loan_sats=d["loan_sats"],
            service_fee_percent=d["service_fee_percent"],
            service_fee_split_percent=d["service_fee_split_percent"],
            payout_boost_sats=d["payout_boost_sats"],
            num_digits=d["num_digits"],
        )

# --- Tiny seeder (optional): bulk insert from your dict -------------------------------------------------------------- #
def seed_product_details(cfg: Dict[str, Dict[str, Any]], session: Session) -> None:
    """
    Ingests your config dict directly:
      {
        'LendBorrowBTCUSD:ltv-80_d-90': { ... },
        'LendBorrowBTCUSD:ltv-80_d-180': { ... },
      }
    Existing rows with the same product_id are skipped (no overwrite).
    """
    existing_ids = {pid for (pid,) in session.query(ProductLendBorrow.product_id).all()}
    to_add = []
    for k, v in cfg.items():
        if k in existing_ids:
            lg.info(f"[seed_product_details] Skipping existing product_id: {k}")
            continue
        to_add.append(ProductLendBorrow.from_key_and_payload(k, v))

    if to_add:
        session.add_all(to_add)
        session.commit()
        lg.info(f"[seed_product_details] Inserted {len(to_add)} product details.")
    else:
        lg.info("[seed_product_details] Nothing to insert.")
