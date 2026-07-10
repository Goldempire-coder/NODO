from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


VERIFICATION_STATUSES = {"pending", "approved", "rejected", "suspended", "blocked"}
RISK_LEVELS = {"normal", "watch", "under_review", "restricted", "high_risk"}
TRUST_LEVELS = {"new", "basic", "plus", "pro", "premium"}
BUSINESS_ACCESS_ROLES = {"owner", "operator"}
BUSINESS_ACCESS_STATUSES = {"active", "suspended", "revoked", "blocked"}
SUBMISSION_STATUSES = {"pending", "approved", "rejected"}
DOCUMENT_TYPES = {"rif_document", "business_license", "owner_identity", "address_proof"}
REQUIRED_DOCUMENT_TYPES = DOCUMENT_TYPES
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_DOCUMENT_SIZE_BYTES = 5 * 1024 * 1024


@dataclass
class BusinessRecord:
    id: str
    owner_user_id: str
    business_name: str
    rif: str | None
    address: str | None
    phone: str | None
    country: str = "VE"
    verification_status: str = "pending"
    trust_level: str = "new"
    risk_level: str = "normal"
    max_order_amount_usd: Decimal = Decimal("100.00")
    daily_limit_usd: Decimal = Decimal("300.00")
    active_order_limit: int = 1
    rating_avg: Decimal | None = None
    completed_orders_count: int = 0
    disputes_count: int = 0
    evasion_reports_count: int = 0
    referral_code: str | None = None
    referral_credits_earned: int = 0
    founder_status: str | None = None
    founder_started_at: datetime | None = None
    founder_expires_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    approved_at: datetime | None = None


@dataclass
class BusinessVerificationSubmissionRecord:
    id: str
    business_id: str
    submitted_by_user_id: str
    status: str
    submitted_data_json: dict
    submitted_at: datetime
    admin_reviewed_by_user_id: str | None = None
    admin_reason: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class BusinessPaymentMethodRecord:
    id: str
    business_id: str
    method_type: str
    network: str | None
    account_value: str
    account_masked: str
    holder_name: str
    verified_status: str = "pending"
    active: bool = False
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class BusinessAccessLinkRecord:
    id: str
    business_id: str
    user_id: str
    telegram_id_snapshot: int
    role_in_business: str = "owner"
    status: str = "active"
    linked_by_admin_id: str | None = None
    linked_at: datetime = field(default_factory=utc_now)
    suspended_at: datetime | None = None
    blocked_at: datetime | None = None
    revoked_at: datetime | None = None
    reason: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class FileAssetRecord:
    id: str
    owner_user_id: str
    resource_type: str
    resource_id: str
    file_type: str
    storage_path: str
    mime_type: str
    size_bytes: int
    created_at: datetime = field(default_factory=utc_now)
    deleted_at: datetime | None = None
