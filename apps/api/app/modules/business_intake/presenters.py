from __future__ import annotations

from typing import Any

from app.modules.business_intake.models import BusinessIntakeDocumentRecord, BusinessIntakeRequestRecord


def mask_phone(value: str | None) -> str | None:
    if not value:
        return None
    compact = "".join(ch for ch in value if ch.isdigit() or ch == "+")
    if len(compact) <= 4:
        return "*" * len(compact)
    return f"{compact[:3]}*****{compact[-3:]}"


def public_intake_payload(intake: BusinessIntakeRequestRecord, *, admin: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": intake.id,
        "status": intake.status,
        "last_step": intake.last_step,
        "business_name": intake.business_name,
        "responsible_name": intake.responsible_name if admin else None,
        "city": intake.city,
        "operation": intake.operation,
        "contact_phone_masked": mask_phone(intake.contact_phone),
        "business_phone_masked": mask_phone(intake.business_phone),
        "submitted_at": intake.submitted_at.isoformat() if intake.submitted_at else None,
        "created_at": intake.created_at.isoformat(),
        "updated_at": intake.updated_at.isoformat(),
    }
    if admin:
        payload |= {
            "referral_code": intake.referral_code,
            "contact_phone": intake.contact_phone,
            "business_phone": intake.business_phone,
            "banks": intake.banks_json,
            "methods": intake.methods_json,
            "min_amount_usd": intake.min_amount_usd,
            "max_amount_usd": intake.max_amount_usd,
            "schedule": intake.schedule_text,
            "references": intake.references_json,
            "reviewed_at": intake.reviewed_at.isoformat() if intake.reviewed_at else None,
            "admin_reason": intake.admin_reason,
            "created_business_id": intake.created_business_id,
            "linked_telegram_user_id": intake.linked_telegram_user_id,
        }
    return payload


def public_business_intake_document(document: BusinessIntakeDocumentRecord) -> dict[str, Any]:
    return {
        "id": document.id,
        "file_type": document.file_type,
        "document_kind": document.document_kind,
        "mime_type": document.mime_type,
        "size_bytes": document.size_bytes,
        "created_at": document.created_at.isoformat(),
    }
