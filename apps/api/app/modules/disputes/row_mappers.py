from __future__ import annotations

import json

from psycopg.types.json import Jsonb

from app.modules.disputes.models import DisputeEventRecord, DisputeRecord


def jsonb(value: dict | None) -> Jsonb | None:
    if value is None:
        return None
    return Jsonb(value, dumps=lambda payload: json.dumps(payload, default=str))


def dispute_from_row(row) -> DisputeRecord:  # type: ignore[no-untyped-def]
    return DisputeRecord(
        id=str(row["id"]),
        order_id=str(row["order_id"]),
        opened_by_user_id=str(row["opened_by_user_id"]),
        opened_by_role=row["opened_by_role"],
        previous_order_status=row["previous_order_status"],
        reason=row["reason"],
        description=row["description"],
        status=row["status"],
        resolution_type=row["resolution_type"],
        resolution_reason=row["resolution_reason"],
        resolved_by_admin_id=str(row["resolved_by_admin_id"]) if row["resolved_by_admin_id"] else None,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        resolved_at=row["resolved_at"],
        cancelled_at=row["cancelled_at"],
    )


def event_from_row(row) -> DisputeEventRecord:  # type: ignore[no-untyped-def]
    return DisputeEventRecord(
        id=str(row["id"]),
        dispute_id=str(row["dispute_id"]),
        order_id=str(row["order_id"]),
        actor_user_id=str(row["actor_user_id"]),
        actor_role=row["actor_role"],
        event_type=row["event_type"],
        old_status=row["old_status"],
        new_status=row["new_status"],
        reason=row["reason"],
        metadata_json=row["metadata_json"],
        created_at=row["created_at"],
    )
