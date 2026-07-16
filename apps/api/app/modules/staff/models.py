from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


STAFF_ROLES = {"support_agent", "support_lead", "operations_readonly", "admin", "super_admin"}
STAFF_PROFILE_STATUSES = {"active", "suspended", "revoked"}
STAFF_INVITE_STATUSES = {"pending", "accepted", "expired", "revoked"}
STAFF_PERMISSION_STATUSES = {"active", "revoked"}
STAFF_PERMISSIONS = {
    "view_support_queue",
    "view_assigned_support_tickets",
    "reply_support_ticket",
    "assign_support_ticket",
    "escalate_support_ticket",
    "resolve_support_ticket",
    "close_support_ticket",
    "view_support_attachment",
    "view_users_masked",
    "view_businesses_masked",
    "view_orders_masked",
    "view_audit_limited",
    "view_metrics_limited",
}
STAFF_SCOPES = {"assigned_only", "queue_scope", "category_scope", "global_readonly"}
FORBIDDEN_STAFF_PERMISSIONS = {
    "block_user",
    "suspend_user",
    "change_user_role",
    "mutate_business_access_links",
    "approve_business",
    "reject_business",
    "approve_credit_payment",
    "reject_credit_payment",
    "manual_credit_adjustment",
    "resolve_dispute",
    "mutate_orders",
    "mutate_ads",
    "mutate_credits",
}


@dataclass
class StaffProfileRecord:
    id: str
    user_id: str
    staff_role: str
    status: str
    display_name: str | None
    created_by_super_admin_id: str
    activated_by_super_admin_id: str | None = None
    suspended_by_super_admin_id: str | None = None
    revoked_by_super_admin_id: str | None = None
    activated_at: datetime | None = None
    suspended_at: datetime | None = None
    revoked_at: datetime | None = None
    reason: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class StaffPermissionRecord:
    id: str
    staff_profile_id: str
    permission: str
    scope: str
    scope_value: str | None
    status: str
    granted_by_super_admin_id: str
    reason: str
    revoked_by_super_admin_id: str | None = None
    revoked_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class StaffInviteRecord:
    id: str
    target_user_id: str | None
    target_telegram_id: int | None
    target_username: str | None
    invite_code_hash: str | None
    staff_role: str
    status: str
    expires_at: datetime
    created_by_super_admin_id: str
    reason: str
    accepted_by_user_id: str | None = None
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None
    expired_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
