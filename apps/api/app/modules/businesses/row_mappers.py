from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

from psycopg.types.json import Jsonb

from app.modules.businesses.models import (
    BusinessAccessLinkRecord,
    BusinessPaymentMethodRecord,
    BusinessRecord,
    BusinessVerificationSubmissionRecord,
    FileAssetRecord,
)


def _row_get(row, key: str, default=None):  # type: ignore[no-untyped-def]
    if hasattr(row, "get"):
        return row.get(key, default)
    try:
        return row[key]
    except (KeyError, IndexError):
        return default


def _datetime_from_row_value(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    return value  # type: ignore[return-value]


def business_from_row(row) -> BusinessRecord:  # type: ignore[no-untyped-def]
    return BusinessRecord(
        id=str(row["id"]),
        owner_user_id=str(row["owner_user_id"]),
        business_name=row["business_name"],
        rif=row["rif"],
        address=row["address"],
        phone=row["phone"],
        country=row["country"],
        verification_status=row["verification_status"],
        trust_level=row["trust_level"],
        risk_level=row["risk_level"],
        min_order_amount_usd=Decimal(str(row["min_order_amount_usd"])),
        max_order_amount_usd=Decimal(str(row["max_order_amount_usd"])),
        daily_limit_usd=Decimal(str(row["daily_limit_usd"])),
        active_order_limit=row["active_order_limit"],
        is_accepting_orders=bool(_row_get(row, "is_accepting_orders", True)),
        rating_avg=Decimal(str(row["rating_avg"])) if row["rating_avg"] is not None else None,
        ratings_count=int(_row_get(row, "ratings_count", 0) or 0),
        completed_orders_count=row["completed_orders_count"],
        business_failure_orders_count=int(_row_get(row, "business_failure_orders_count", 0) or 0),
        lost_disputes_count=int(_row_get(row, "lost_disputes_count", 0) or 0),
        disputes_count=row["disputes_count"],
        success_rate=Decimal(str(_row_get(row, "success_rate"))) if _row_get(row, "success_rate") is not None else None,
        average_delivery_seconds=_row_get(row, "average_delivery_seconds"),
        reputation_tier=_row_get(row, "reputation_tier", "new"),
        reputation_calculated_at=_datetime_from_row_value(_row_get(row, "reputation_calculated_at")),
        evasion_reports_count=row["evasion_reports_count"],
        referral_code=row["referral_code"],
        referral_credits_earned=row["referral_credits_earned"],
        founder_status=row["founder_status"],
        founder_started_at=row["founder_started_at"],
        founder_expires_at=row["founder_expires_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        approved_at=row["approved_at"],
    )


def jsonb(value: dict | None) -> Jsonb | None:
    if value is None:
        return None
    return Jsonb(value, dumps=lambda payload: json.dumps(payload, default=str))


def submission_from_row(row) -> BusinessVerificationSubmissionRecord:  # type: ignore[no-untyped-def]
    return BusinessVerificationSubmissionRecord(
        id=str(row["id"]),
        business_id=str(row["business_id"]),
        submitted_by_user_id=str(row["submitted_by_user_id"]),
        status=row["status"],
        submitted_data_json=row["submitted_data_json"],
        admin_reviewed_by_user_id=str(row["admin_reviewed_by_user_id"]) if row["admin_reviewed_by_user_id"] else None,
        admin_reason=row["admin_reason"],
        submitted_at=row["submitted_at"],
        reviewed_at=row["reviewed_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def access_link_from_row(row) -> BusinessAccessLinkRecord:  # type: ignore[no-untyped-def]
    return BusinessAccessLinkRecord(
        id=str(row["id"]),
        business_id=str(row["business_id"]),
        user_id=str(row["user_id"]),
        telegram_id_snapshot=int(row["telegram_id_snapshot"]),
        role_in_business=row["role_in_business"],
        status=row["status"],
        linked_by_admin_id=str(row["linked_by_admin_id"]) if row["linked_by_admin_id"] else None,
        linked_at=row["linked_at"],
        suspended_at=row["suspended_at"],
        blocked_at=row["blocked_at"],
        revoked_at=row["revoked_at"],
        reason=row["reason"],
        business_pin_hash=_row_get(row, "business_pin_hash"),
        business_pin_set_at=_datetime_from_row_value(_row_get(row, "business_pin_set_at")),
        business_pin_verified_at=_datetime_from_row_value(_row_get(row, "business_pin_verified_at")),
        business_pin_unlocked_until=_datetime_from_row_value(_row_get(row, "business_pin_unlocked_until")),
        business_pin_failed_attempts=int(_row_get(row, "business_pin_failed_attempts", 0) or 0),
        business_pin_locked_until=_datetime_from_row_value(_row_get(row, "business_pin_locked_until")),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def file_from_row(row) -> FileAssetRecord:  # type: ignore[no-untyped-def]
    return FileAssetRecord(
        id=str(row["id"]),
        owner_user_id=str(row["owner_user_id"]),
        resource_type=row["resource_type"],
        resource_id=str(row["resource_id"]),
        file_type=row["file_type"],
        storage_path=row["storage_path"],
        mime_type=row["mime_type"],
        size_bytes=row["size_bytes"],
        created_at=row["created_at"],
        deleted_at=row["deleted_at"],
    )


def payment_method_from_row(row) -> BusinessPaymentMethodRecord:  # type: ignore[no-untyped-def]
    return BusinessPaymentMethodRecord(
        id=str(row["id"]),
        business_id=str(row["business_id"]),
        method_type=row["method_type"],
        network=row["network"],
        account_value=row["account_value"],
        account_masked=row["account_masked"],
        holder_name=row["holder_name"],
        verified_status=row["verified_status"],
        active=row["active"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
