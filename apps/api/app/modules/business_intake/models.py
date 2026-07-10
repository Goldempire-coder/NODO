from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


INTAKE_STATUSES = {"draft", "submitted", "accepted", "rejected"}
INTAKE_OPERATIONS = {"buy_usd", "sell_usd", "both"}
INTAKE_DOCUMENT_KINDS = {"identity_document", "rif_document", "local_image", "social_reference", "other_reference"}
INTAKE_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
INTAKE_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
INTAKE_FINAL_CONFIRMATION = "Solicitud recibida. Revisaremos tu informacion y te avisaremos el siguiente paso."
INTAKE_STEPS = {
    "start",
    "awaiting_referral_code",
    "awaiting_whatsapp_phone",
    "awaiting_contact",
    "awaiting_business_name",
    "awaiting_responsible_name",
    "awaiting_city",
    "awaiting_business_phone",
    "awaiting_operation",
    "awaiting_banks",
    "awaiting_methods",
    "awaiting_min_amount",
    "awaiting_max_amount",
    "awaiting_schedule",
    "awaiting_references",
    "awaiting_documents",
    "submitted",
}


@dataclass
class BusinessIntakeRequestRecord:
    id: str
    telegram_user_id: int
    telegram_chat_id: int
    status: str = "draft"
    last_step: str = "start"
    last_update_id: int | None = None
    contact_phone: str | None = None
    business_phone: str | None = None
    referral_code: str | None = None
    business_name: str | None = None
    responsible_name: str | None = None
    city: str | None = None
    operation: str | None = None
    banks_json: list[str] = field(default_factory=list)
    methods_json: list[str] = field(default_factory=list)
    min_amount_usd: str | None = None
    max_amount_usd: str | None = None
    schedule_text: str | None = None
    references_json: list[str] = field(default_factory=list)
    submitted_at: datetime | None = None
    reviewed_by_admin_id: str | None = None
    reviewed_at: datetime | None = None
    admin_reason: str | None = None
    created_business_id: str | None = None
    linked_telegram_user_id: int | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    archived_at: datetime | None = None


@dataclass
class BusinessIntakeDocumentRecord:
    id: str
    owner_user_id: str
    resource_type: str
    resource_id: str
    file_type: str
    storage_path: str
    mime_type: str
    size_bytes: int
    document_kind: str
    telegram_update_id: int | None = None
    telegram_file_id: str | None = None
    telegram_file_unique_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    deleted_at: datetime | None = None
