from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


ORDER_STATUSES = {
    "waiting_payment",
    "payment_reported",
    "payment_rejected",
    "payment_confirmed",
    "delivered",
    "completed",
    "cancelled",
    "disputed",
}
CANCEL_REASONS = {
    "remitter_cancelled_before_payment",
    "payment_not_reported_in_time",
    "business_unavailable",
    "admin_cancelled",
}


@dataclass
class OrderRecord:
    id: str
    public_order_code: str
    ad_id: str
    business_id: str
    remitter_user_id: str
    status: str
    idempotency_key: str | None
    amount_usd: Decimal
    rate_snapshot: Decimal
    amount_bs_calculated: Decimal
    business_name_snapshot: str
    payment_method_snapshot: str
    delivery_method_snapshot: str
    min_amount_snapshot: Decimal
    max_amount_snapshot: Decimal
    payment_instructions_snapshot: dict
    receiver_data_json: dict
    payment_report_deadline_at: datetime
    expires_at: datetime
    extension_used: bool = False
    completion_reason: str | None = None
    cancel_reason: str | None = None
    dispute_reason: str | None = None
    payment_data_revealed_at: datetime | None = None
    payment_data_revealed_by: str | None = None
    payment_report_extension_used_at: datetime | None = None
    business_response_warning_at: datetime | None = None
    business_response_deadline_at: datetime | None = None
    delivery_warning_at: datetime | None = None
    delivery_deadline_at: datetime | None = None
    auto_complete_warning_12h_at: datetime | None = None
    auto_complete_warning_23h_at: datetime | None = None
    auto_complete_at: datetime | None = None
    paid_reported_at: datetime | None = None
    payment_confirmed_at: datetime | None = None
    delivered_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class OrderStateEventRecord:
    id: str
    order_id: str
    from_status: str | None
    to_status: str
    event_type: str
    actor_user_id: str | None
    actor_role: str | None
    reason: str | None
    request_id: str
    metadata_json: dict | None
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class PaymentReportRecord:
    id: str
    order_id: str
    reported_by_user_id: str
    status: str
    idempotency_key: str | None
    payment_type: str
    payment_amount: Decimal
    payment_reference: str | None = None
    payment_sender_name: str | None = None
    payment_sender_account_masked: str | None = None
    tx_hash: str | None = None
    network: str | None = None
    proof_file_id: str | None = None
    proof_content_sha256: str | None = None
    report_payload_hash: str | None = None
    admin_notes: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class OrderReceiverDetailsRecord:
    id: str
    order_id: str
    bank_code: str
    phone: str
    document: str
    holder: str
    payload_hash: str
    shared_by_user_id: str
    shared_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class RatingRecord:
    id: str
    order_id: str
    business_id: str
    rater_user_id: str
    stars: int
    created_at: datetime = field(default_factory=utc_now)


def new_public_order_code() -> str:
    return f"NODO-{uuid4().hex[:8].upper()}"
