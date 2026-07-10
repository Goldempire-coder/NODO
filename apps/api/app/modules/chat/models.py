from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


ALLOWED_MESSAGE_STATES = {"payment_reported", "payment_rejected", "payment_confirmed", "delivered", "disputed"}
ALLOWED_ATTACHMENT_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_ATTACHMENT_SIZE_BYTES = 5 * 1024 * 1024


@dataclass
class MessageRecord:
    id: str
    order_id: str
    sender_user_id: str
    sender_role: str
    body: str | None
    visibility: str = "parties"
    status: str = "visible"
    idempotency_key: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    deleted_at: datetime | None = None


@dataclass
class MessageAttachmentRecord:
    id: str
    message_id: str | None
    order_id: str
    file_asset_id: str
    uploaded_by_user_id: str
    file_type: str
    mime_type: str
    size_bytes: int
    status: str = "active"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    deleted_at: datetime | None = None
