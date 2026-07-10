from __future__ import annotations

import json
from decimal import Decimal

from psycopg.types.json import Jsonb

from app.modules.businesses.models import (
    BusinessAccessLinkRecord,
    BusinessPaymentMethodRecord,
    BusinessRecord,
    BusinessVerificationSubmissionRecord,
    FileAssetRecord,
)


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
        max_order_amount_usd=Decimal(str(row["max_order_amount_usd"])),
        daily_limit_usd=Decimal(str(row["daily_limit_usd"])),
        active_order_limit=row["active_order_limit"],
        rating_avg=Decimal(str(row["rating_avg"])) if row["rating_avg"] is not None else None,
        completed_orders_count=row["completed_orders_count"],
        disputes_count=row["disputes_count"],
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
