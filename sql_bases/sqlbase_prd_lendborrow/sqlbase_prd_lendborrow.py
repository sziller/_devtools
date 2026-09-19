"""
SQLAlchemy powered DB Base for Product Details used by DLCPlaza.
Portable JSON field: SQLite now, PostgreSQL JSONB later (no code changes needed).
by Sziller
"""
from __future__ import annotations
import logging
import hashlib
import json
import math
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger, SmallInteger, String,
    DateTime, func, JSON, CheckConstraint, event, select, inspect
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.engine import Connection
from sqlalchemy.orm import DeclarativeBase, Mapped, Mapper, mapped_column, Session, validates


class Base(DeclarativeBase):
    pass


# Logger setup
lg = logging.getLogger(__name__)


# Identity protocol: positions are permanent. Never remove, reorder, insert between,
# or repurpose entries. Future dimensions may ONLY be appended to this tuple.
PRODUCT_IDENTITY_FIELDS = (
    "product_function",
    "symbol",
    "ltv",
    "duration",
    "contract_value",
)


def canonicalize_product_identity(values: list[str | int | float | None]) -> str:
    """Serialize values only as compact, ASCII-escaped JSON, without trailing nulls.

    Internal nulls retain their positions. Integral floats (including negative zero)
    become integers; other finite floats use JSON's round-trip representation, with
    no rounding. Strings are exact/case-sensitive. Booleans and non-finite numbers
    are not identity values. This format is part of the permanent identity protocol.
    """
    normalized = list(values)
    while normalized and normalized[-1] is None:
        normalized.pop()
    for index, value in enumerate(normalized):
        if value is None or type(value) in (str, int):
            continue
        if type(value) is not float or not math.isfinite(value):
            raise ValueError("Product identity values must be strings, finite numbers, or None")
        if value.is_integer():
            normalized[index] = int(value)
    return json.dumps(normalized, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def hash_product_identity(values: list[str | int | float | None]) -> str:
    """Return the lowercase SHA-256 hex digest of canonical identity JSON bytes."""
    return hashlib.sha256(canonicalize_product_identity(values).encode("utf-8")).hexdigest()


def _normalize_identity_number(value: Any, field: str) -> int | float | None:
    """Respect FLOAT/BIGINT storage without silently rounding caller input.

    FLOAT fields accept finite Python ints/floats, converting exactly representable
    ints to float. BIGINT accepts ints or integral floats in its non-negative range,
    converting the latter to int. No strings, booleans or fractional satoshis.
    """
    if value is None:
        return None
    if type(value) not in (int, float):
        raise ValueError(f"{field} must be a finite number")
    if field == "contract_value":
        if type(value) is float:
            if not math.isfinite(value) or not value.is_integer():
                raise ValueError("contract_value must be an integer satoshi amount")
            value = int(value)
        if not 0 <= value <= 2**63 - 1:
            raise ValueError("contract_value must be a non-negative BIGINT satoshi amount")
        return value
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError(f"{field} cannot be represented as a finite FLOAT") from exc
    if not math.isfinite(number) or number != value:
        raise ValueError(f"{field} cannot be represented as a finite FLOAT without precision loss")
    return number


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
        CheckConstraint("contract_value IS NULL OR contract_value >= 0",
                        name="ck_products_lendborrow_contract_value_nonneg"),
        CheckConstraint("payout_boost_sats >= 0", name="ck_products_lendborrow_payout_boost_nonneg"),
        CheckConstraint("num_digits >= 0", name="ck_products_lendborrow_num_digits_nonneg"),
        CheckConstraint("length(trim(symbol)) > 0", name="ck_products_lendborrow_symbol_nonempty"),
        CheckConstraint("min_contract_value IS NULL OR min_contract_value >= 0",
                        name="ck_products_lendborrow_min_contract_value_nonneg"),
    )

    # Primary identity
    product_id: Mapped[str] = mapped_column(primary_key=True)  # e.g. 'LendBorrowBTCUSD:ltv-80_d-90'
    # Load old values on assignment even after expiration, so history can distinguish
    # real identity changes from equivalent assignments on persisted instances.
    product_function: Mapped[str] = mapped_column(nullable=False, active_history=True)
    product_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, active_history=True)
    symbol: Mapped[str] = mapped_column(nullable=False, active_history=True)

    # Core parameters (mirrors your dict keys exactly)
    ltv: Mapped[float] = mapped_column(nullable=False, active_history=True)     # 80.0
    duration: Mapped[float] = mapped_column(nullable=False, active_history=True)     # 0.02, 0.03 (NO ZERO)

    # Portable JSON: lists on SQLite today; becomes JSONB on PostgreSQL automatically
    orcl_id: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(
            JSON().with_variant(postgresql.JSONB(), "postgresql")
        ),
        nullable=False,
        default=list  # Python-side default keeps it portable across SQLite/PG
    )  # e.g. ["oracle_dlcp"]

    # Timers (match dict: integers)
    expiry_offer_default_hours: Mapped[int] = mapped_column(nullable=False)  # 168
    expiry_deal_acc_minutes: Mapped[int] = mapped_column(nullable=False)  # 60
    expiry_deal_ini_minutes: Mapped[int] = mapped_column(nullable=False)  # 120
    refund_delay_days: Mapped[int] = mapped_column(nullable=False)  # 30

    # Monetary-ish values
    contract_value: Mapped[int | None] = mapped_column(
        BigInteger(), nullable=True, active_history=True,
    )  # 100_000 (use BigInteger for headroom)
    min_contract_value: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    # Per-Oracle concrete DLC contract limits, in satoshis (not liquidity sizes).
    max_contract_value: Mapped[dict[str, int] | None] = mapped_column(
        MutableDict.as_mutable(
            JSON(none_as_null=True).with_variant(postgresql.JSONB(none_as_null=True), "postgresql")
        ),
        nullable=True,
    )
    payout_boost_sats: Mapped[int] = mapped_column(BigInteger(), nullable=False)   # 500

    # Function paths (kept as strings)
    interest_ear: Mapped[str] = mapped_column(nullable=False)       # 'dlc_plaza_engine.calcs.calc_ear_from_interest'
    interest_b: Mapped[str] = mapped_column(nullable=False)       # 'dlc_plaza_engine.calcs.calc_actual_interest'
    interest_b_ear: Mapped[str] = mapped_column(nullable=False)       # 'dlc_plaza_engine.calcs.calc_ear_from_interest'
    free_loan: Mapped[str] = mapped_column(nullable=False)  # 'dlc_plaza_engine.calcs.calc_free_loan_using_interest'
    loan_sats: Mapped[str] = mapped_column(nullable=False)       # 'dlc_plaza_engine.calcs.calc_loan_from_data'

    # Fees and display helpers
    service_fee_percent: Mapped[float] = mapped_column(nullable=False)      # 0.25
    service_fee_split_percent: Mapped[int] = mapped_column(nullable=False)      # 30
    num_digits: Mapped[int] = mapped_column(SmallInteger(), nullable=False)  # 7

    # Bookkeeping (timezone-aware)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now(), onupdate=func.now(),
    )
    active: Mapped[bool] = mapped_column(nullable=False, server_default="1")
    
    # --- Helpers ---------------------------------------------------------------------------------------------------- #
    def __init__(self, **kwargs: Any) -> None:
        # Supplied hashes are never authoritative, including serialized round-trips.
        kwargs.pop("product_hash", None)
        super().__init__(**kwargs)
        self.validate_product_reference()
        self.product_hash = self.calculate_product_hash()

    def get_product_identity_values(self) -> list[str | int | float | None]:
        """Collect authoritative values in the permanent registry order."""
        return [
            _normalize_identity_number(getattr(self, field), field)
            if field in ("ltv", "duration", "contract_value") else getattr(self, field)
            for field in PRODUCT_IDENTITY_FIELDS
        ]

    def calculate_product_hash(self) -> str:
        """Calculate identity independently of the catalog ID or supplied hash."""
        return hash_product_identity(self.get_product_identity_values())

    @validates("ltv", "duration", "contract_value")
    def _validate_identity_number(self, key: str, value: Any) -> int | float | None:
        return _normalize_identity_number(value, key)

    @staticmethod
    def _validate_satoshis(value: Any, field: str) -> None:
        # Match contract_value's non-negative convention and signed BIGINT storage.
        if type(value) is not int or not 0 <= value <= 2**63 - 1:
            raise ValueError(f"{field} must be a non-negative integer satoshi amount within BIGINT range")

    @validates("product_function", "symbol", "min_contract_value", "max_contract_value")
    def _validate_reference_field(self, key: str, value: Any) -> Any:
        if key in ("product_function", "symbol"):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{key} must be a non-empty string")
        elif key == "min_contract_value" and value is not None:
            self._validate_satoshis(value, key)
        elif key == "max_contract_value" and value is not None:
            if not isinstance(value, dict):
                raise ValueError("max_contract_value must be a dictionary of Oracle IDs to satoshi amounts")
            for oracle_id, amount in value.items():
                if not isinstance(oracle_id, str) or not oracle_id.strip():
                    raise ValueError("max_contract_value keys must be non-empty Oracle identifier strings")
                self._validate_satoshis(amount, f"max_contract_value[{oracle_id!r}]")
        return value

    def validate_product_reference(self) -> None:
        """Validate reference fields and per-Oracle limits before persistence."""
        for field in ("product_function", "symbol", "min_contract_value", "max_contract_value"):
            self._validate_reference_field(field, getattr(self, field))
        # Validate the relationship after all attributes are set, regardless of keyword order.
        if self.max_contract_value:
            for oracle_id in self.max_contract_value:
                if oracle_id not in (self.orcl_id or []):
                    raise ValueError(f"max_contract_value Oracle ID {oracle_id!r} must be present in orcl_id")

    def return_as_dict(self) -> dict[str, Any]:
        """Return instance as a plain dict (safe for JSON responses)."""
        return {
            "product_id": self.product_id,
            "product_function": self.product_function,
            "product_hash": self.product_hash,
            "symbol": self.symbol,
            "min_contract_value": self.min_contract_value,
            "max_contract_value": self.max_contract_value,
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
            "active": self.active
        }

    def __repr__(self) -> str:
        return f"ProductLendBorrow(product_id={self.product_id}, ltv={self.ltv}, duration={self.duration})"

    # Optional: convenience loader for your exact dict structure
    @classmethod
    def from_key_and_payload(cls, product_key: str, d: dict[str, Any]) -> ProductLendBorrow:
        """Create an instance from (key, dict) exactly like your provided config."""
        return cls(
            product_id=product_key,
            product_function=d["product_function"],
            symbol=d["symbol"],
            min_contract_value=d.get("min_contract_value"),
            max_contract_value=d.get("max_contract_value"),
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
            active=d.get("active", True)
        )

    # inside class ProductLendBorrow(Base):  (your columns here…)
    @classmethod
    def construct(cls, d_in: dict[str, Any]) -> ProductLendBorrow:
        """Construct an instance from a dictionary."""
        # keep only known columns; ignore extras
        column_names = {c.name for c in cls.__table__.columns}
        payload = {k: v for k, v in d_in.items() if k in column_names}

        # default behavior for active if missing
        if "active" not in payload:
            payload["active"] = True
            
        return cls(**payload)


@event.listens_for(ProductLendBorrow, "before_insert")
def _validate_product_reference_before_insert(
    mapper: Mapper[ProductLendBorrow], connection: Connection, target: ProductLendBorrow,
) -> None:
    """Recheck mutable JSON contents and Oracle membership before ORM persistence."""
    target.validate_product_reference()
    target.product_hash = target.calculate_product_hash()


@event.listens_for(ProductLendBorrow, "before_update")
def _validate_product_reference_before_update(
    mapper: Mapper[ProductLendBorrow], connection: Connection, target: ProductLendBorrow,
) -> None:
    """Keep persisted identity immutable while validating ordinary policy updates."""
    state = inspect(target)
    for field in (*PRODUCT_IDENTITY_FIELDS, "product_hash"):
        if state.attrs[field].history.has_changes():
            raise ValueError(f"ProductLendBorrow.{field} is immutable after insertion; create a new Product Definition")
    target.validate_product_reference()
    if target.product_hash != target.calculate_product_hash():
        raise ValueError("Persisted product_hash does not match the Product Definition")


# --- Tiny seeder (optional): bulk insert from your dict ----------------------------------------------------------- #
def seed_product_details(cfg: dict[str, dict[str, Any]], session: Session) -> None:
    """
    Ingests your config dict directly:
      {
        'LendBorrowBTCUSD:ltv-80_d-90': { ... },
        'LendBorrowBTCUSD:ltv-80_d-180': { ... },
      }
    Existing rows with the same product_id are skipped (no overwrite).
    """
    existing_ids: set[str] = set(
        session.scalars(select(ProductLendBorrow.product_id)).all()
    )
    to_add: list[ProductLendBorrow] = []
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
