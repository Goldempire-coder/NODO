from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from psycopg.types.json import Jsonb

from app.core.errors import ApiError
from app.modules.business_intake.models import (
    BusinessIntakeDocumentRecord,
    BusinessIntakeRequestRecord,
)


def jsonb(value: list[str] | dict | None) -> Jsonb | None:
    if value is None:
        return None
    return Jsonb(value, dumps=lambda payload: json.dumps(payload, default=str))


def decimal_text(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(Decimal(value))
    except (InvalidOperation, ValueError) as exc:
        raise ApiError("VALIDATION_ERROR", status_code=422) from exc


def intake_from_row(row) -> BusinessIntakeRequestRecord:  # type: ignore[no-untyped-def]
    return BusinessIntakeRequestRecord(
        id=str(row["id"]),
        telegram_user_id=int(row["telegram_user_id"]),
        telegram_chat_id=int(row["telegram_chat_id"]),
        status=row["status"],
        last_step=row["last_step"],
        last_update_id=int(row["last_update_id"]) if row["last_update_id"] is not None else None,
        contact_phone=row["contact_phone"],
        business_phone=row["business_phone"],
        referral_code=row["referral_code"],
        business_name=row["business_name"],
        responsible_name=row["responsible_name"],
        city=row["city"],
        operation=row["operation"],
        banks_json=list(row["banks_json"] or []),
        methods_json=list(row["methods_json"] or []),
        min_amount_usd=str(row["min_amount_usd"]) if row["min_amount_usd"] is not None else None,
        max_amount_usd=str(row["max_amount_usd"]) if row["max_amount_usd"] is not None else None,
        schedule_text=row["schedule_text"],
        references_json=list(row["references_json"] or []),
        submitted_at=row["submitted_at"],
        reviewed_by_admin_id=str(row["reviewed_by_admin_id"]) if row["reviewed_by_admin_id"] else None,
        reviewed_at=row["reviewed_at"],
        admin_reason=row["admin_reason"],
        created_business_id=str(row["created_business_id"]) if row["created_business_id"] else None,
        linked_telegram_user_id=int(row["linked_telegram_user_id"]) if row["linked_telegram_user_id"] is not None else None,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        archived_at=row["archived_at"],
    )


def document_from_row(row) -> BusinessIntakeDocumentRecord:  # type: ignore[no-untyped-def]
    metadata = row["metadata_json"] or {}
    return BusinessIntakeDocumentRecord(
        id=str(row["id"]),
        owner_user_id=str(row["owner_user_id"]),
        resource_type=row["resource_type"],
        resource_id=str(row["resource_id"]),
        file_type=row["file_type"],
        storage_path=row["storage_path"],
        mime_type=row["mime_type"],
        size_bytes=row["size_bytes"],
        document_kind=metadata.get("document_kind", "other_reference"),
        telegram_update_id=int(metadata["telegram_update_id"]) if metadata.get("telegram_update_id") is not None else None,
        telegram_file_id=metadata.get("telegram_file_id"),
        telegram_file_unique_id=metadata.get("telegram_file_unique_id"),
        created_at=row["created_at"],
        deleted_at=row["deleted_at"],
    )
