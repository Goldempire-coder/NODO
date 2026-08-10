from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


ALLOWED_DISPUTE_ORDER_STATES = {"payment_reported", "payment_rejected", "payment_confirmed", "delivered"}
BUSINESS_PAYMENT_PROBLEM_DISPUTE_REASON = "payment_not_received_or_incomplete"
DISPUTE_REASONS = {
    "business_no_payment_confirmation",
    "business_confirmed_payment_but_not_delivered",
    BUSINESS_PAYMENT_PROBLEM_DISPUTE_REASON,
    "payment_mobile_not_received",
    "amount_incorrect",
    "wrong_receiver_data",
    "other",
}
DISPUTE_STATUSES = {"open", "in_review", "resolved", "cancelled"}
DISPUTE_RESOLUTION_TYPES = {"remitter_favored", "business_favored", "cancelled", "completed", "keep_under_review"}
DISPUTE_RESOLUTION_TERMINAL_TYPES = {"remitter_favored", "business_favored", "cancelled", "completed"}


@dataclass
class DisputeRecord:
    id: str
    order_id: str
    opened_by_user_id: str
    opened_by_role: str
    previous_order_status: str
    reason: str
    description: str | None
    status: str = "open"
    resolution_type: str | None = None
    resolution_reason: str | None = None
    resolved_by_admin_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    resolved_at: datetime | None = None
    cancelled_at: datetime | None = None


@dataclass
class DisputeEventRecord:
    id: str
    dispute_id: str
    order_id: str
    actor_user_id: str
    actor_role: str
    event_type: str
    old_status: str | None
    new_status: str | None
    reason: str | None
    metadata_json: dict | None
    created_at: datetime = field(default_factory=utc_now)
