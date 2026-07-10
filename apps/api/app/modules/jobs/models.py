from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


JOB_TYPE_EXPIRE_AND_ESCALATE = "expire_and_escalate_orders"
JOB_LOCK_EXPIRE_AND_ESCALATE = "jobs:expire_and_escalate_orders"
JOB_LOCK_TTL_SECONDS = 300

JOB_RUN_STATUSES = {"started", "finished", "failed", "skipped", "lock_not_acquired"}
NOTIFICATION_JOB_STATUSES = {"pending", "sent", "failed", "skipped", "cancelled"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


@dataclass
class JobRunRecord:
    id: str
    job_type: str
    status: str
    lock_key: str | None = None
    lock_acquired: bool = False
    attempts: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    processed_count: int = 0
    changed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    error_code: str | None = None
    error_message_safe: str | None = None
    metadata_json: dict | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class NotificationJobRecord:
    id: str
    notification_type: str
    status: str
    scheduled_for: datetime
    dedupe_key: str
    recipient_user_id: str | None = None
    recipient_role: str | None = None
    order_id: str | None = None
    business_id: str | None = None
    dispute_id: str | None = None
    sent_at: datetime | None = None
    failed_at: datetime | None = None
    attempts: int = 0
    max_attempts: int = 3
    last_error_code: str | None = None
    metadata_json: dict | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


def mask_metadata(metadata: dict | None) -> dict:
    if not metadata:
        return {}
    forbidden_keys = {"storage_path", "account_value", "payment_instructions_snapshot", "token", "secret", "signed_url"}
    masked: dict = {}
    for key, value in metadata.items():
        lowered = key.lower()
        if lowered in forbidden_keys or "secret" in lowered or "token" in lowered:
            continue
        if isinstance(value, dict):
            masked[key] = mask_metadata(value)
        elif isinstance(value, list):
            masked[key] = ["[masked]" if isinstance(item, dict) else item for item in value]
        else:
            masked[key] = value
    return masked
