from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


AD_STATUSES = {"draft", "active", "in_order", "paused", "expired", "archived", "suspended"}
PAYMENT_METHODS = {"zelle", "usdt_trc20"}
DELIVERY_METHODS = {"pago_movil_ve"}
LEDGER_TYPES = {"purchase", "founder_free_use", "referral_bonus", "hold", "consume", "release", "expire", "admin_adjustment"}


@dataclass
class CreditWalletRecord:
    id: str
    business_id: str
    available_credits: int = 0
    blocked_credits: int = 0
    consumed_credits: int = 0
    lifetime_purchased_credits: int = 0
    lifetime_bonus_credits: int = 0
    lifetime_adjusted_credits: int = 0
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class CreditLedgerRecord:
    id: str
    business_id: str
    type: str
    amount: int
    available_before: int
    available_after: int
    blocked_before: int
    blocked_after: int
    consumed_before: int
    consumed_after: int
    reason: str
    source: str
    reference_type: str
    reference_id: str
    related_ad_id: str | None = None
    related_order_id: str | None = None
    related_referral_id: str | None = None
    related_credit_purchase_id: str | None = None
    notes: str | None = None
    created_by: str | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class AdRecord:
    id: str
    business_id: str
    payment_method_id: str
    payment_method: str
    delivery_method: str
    rate_bs_per_usd: Decimal
    amount_min_usd: Decimal
    amount_max_usd: Decimal
    required_credits: int
    status: str
    credit_hold_ledger_id: str | None
    credit_consumed_ledger_id: str | None
    created_at: datetime
    updated_at: datetime
    activated_at: datetime | None
    expires_at: datetime | None
    last_rate_updated_at: datetime | None
