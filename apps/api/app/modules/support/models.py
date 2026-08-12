from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


ACTIVE_SUPPORT_STATUSES = {"open", "waiting_support", "waiting_user", "escalated"}
ARCHIVED_SUPPORT_STATUSES = {"resolved", "closed"}
SUPPORT_STATUSES = ACTIVE_SUPPORT_STATUSES | ARCHIVED_SUPPORT_STATUSES
SUPPORT_STATUS_GROUPS = {
    "active": ACTIVE_SUPPORT_STATUSES,
    "archived": ARCHIVED_SUPPORT_STATUSES,
}
SUPPORT_SCOPES = {
    "client_general",
    "client_order",
    "business_general",
    "business_order",
    "business_ad",
    "business_credit",
    "admin_internal",
}
SUPPORT_CATEGORIES = {
    "technical_issue",
    "account_access",
    "order_help",
    "payment_report_help",
    "business_access",
    "credits_help",
    "suspicious_activity",
    "other",
}
SUPPORT_PRIORITIES = {"low", "normal", "high", "urgent"}
SUPPORT_MESSAGE_VISIBILITIES = {"participants", "support_internal", "admin_internal"}
STRUCTURED_OPERATION_REPORT = "structured_operation_report"
MAX_SUPPORT_ATTACHMENT_SIZE_BYTES = 5 * 1024 * 1024


@dataclass
class SupportTicketRecord:
    id: str
    requester_user_id: str
    requester_role: str
    requester_surface: str
    scope: str
    category: str
    status: str
    priority: str
    subject: str
    report_kind: str | None = None
    business_id: str | None = None
    order_id: str | None = None
    ad_id: str | None = None
    credit_purchase_id: str | None = None
    dispute_id: str | None = None
    assigned_support_user_id: str | None = None
    last_message_at: datetime | None = None
    escalated_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class BusinessPublicationHoldRecord:
    id: str
    business_id: str
    order_id: str
    support_ticket_id: str
    status: str = "active"
    reason_type: str = STRUCTURED_OPERATION_REPORT
    created_at: datetime = field(default_factory=utc_now)
    released_at: datetime | None = None
    released_by: str | None = None
    release_reason: str | None = None


@dataclass
class SupportMessageRecord:
    id: str
    ticket_id: str
    sender_user_id: str
    sender_role: str
    body: str
    visibility: str = "participants"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    deleted_at: datetime | None = None


@dataclass
class SupportTicketEventRecord:
    id: str
    ticket_id: str
    actor_user_id: str
    actor_role: str
    event_type: str
    from_status: str | None = None
    to_status: str | None = None
    reason: str | None = None
    metadata_json: dict | None = None
    created_at: datetime = field(default_factory=utc_now)
