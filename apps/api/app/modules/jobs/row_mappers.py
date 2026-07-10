from __future__ import annotations

import json

from psycopg.types.json import Jsonb

from app.modules.jobs.models import JobRunRecord, NotificationJobRecord, mask_metadata


def jsonb_metadata(value: dict | None) -> Jsonb | None:
    if value is None:
        return None
    return Jsonb(mask_metadata(value), dumps=lambda payload: json.dumps(payload, default=str))


def job_run_from_row(row) -> JobRunRecord:  # type: ignore[no-untyped-def]
    return JobRunRecord(
        id=str(row["id"]),
        job_type=row["job_type"],
        status=row["status"],
        lock_key=row["lock_key"],
        lock_acquired=row.get("lock_acquired", False),
        attempts=row["attempts"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        duration_ms=row.get("duration_ms"),
        processed_count=row.get("processed_count", 0),
        changed_count=row.get("changed_count", 0),
        skipped_count=row.get("skipped_count", 0),
        failed_count=row.get("failed_count", 0),
        error_code=row["error_code"],
        error_message_safe=row["error_message_safe"],
        metadata_json=row["metadata_json"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def notification_from_row(row) -> NotificationJobRecord:  # type: ignore[no-untyped-def]
    return NotificationJobRecord(
        id=str(row["id"]),
        notification_type=row["notification_type"],
        recipient_user_id=str(row["recipient_user_id"]) if row["recipient_user_id"] else None,
        recipient_role=row["recipient_role"],
        order_id=str(row["order_id"]) if row["order_id"] else None,
        business_id=str(row["business_id"]) if row["business_id"] else None,
        dispute_id=str(row["dispute_id"]) if row["dispute_id"] else None,
        status=row["status"],
        scheduled_for=row["scheduled_for"],
        sent_at=row["sent_at"],
        failed_at=row["failed_at"],
        attempts=row["attempts"],
        max_attempts=row["max_attempts"],
        last_error_code=row["last_error_code"],
        dedupe_key=row["dedupe_key"],
        metadata_json=row["metadata_json"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
