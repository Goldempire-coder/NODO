from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.modules.jobs.models import JobRunRecord, NotificationJobRecord, mask_metadata
from app.modules.jobs.row_mappers import job_run_from_row, jsonb_metadata, notification_from_row
from app.shared.db.connection import pooled_connect
from app.shared.keyset_pagination import decode_keyset_cursor, encode_keyset_cursor


class PostgresJobRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def create_job_run(self, **fields: Any) -> JobRunRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                insert into job_runs (
                    job_type, status, lock_key, lock_acquired, attempts, started_at,
                    finished_at, duration_ms, processed_count, changed_count,
                    skipped_count, failed_count, error_code, error_message_safe,
                    metadata_json, created_at, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                returning *
                """,
                (
                    fields["job_type"],
                    fields["status"],
                    fields.get("lock_key"),
                    fields.get("lock_acquired", False),
                    fields.get("attempts", 0),
                    fields.get("started_at"),
                    fields.get("finished_at"),
                    fields.get("duration_ms"),
                    fields.get("processed_count", 0),
                    fields.get("changed_count", 0),
                    fields.get("skipped_count", 0),
                    fields.get("failed_count", 0),
                    fields.get("error_code"),
                    fields.get("error_message_safe"),
                    jsonb_metadata(fields.get("metadata_json")),
                ),
            ).fetchone()
            conn.commit()
        return job_run_from_row(row)

    def update_job_run(self, run: JobRunRecord, **fields: Any) -> JobRunRecord:
        assignments: list[str] = []
        params: list[Any] = []
        for key, value in fields.items():
            assignments.append(f"{key} = %s")
            params.append(jsonb_metadata(value) if key == "metadata_json" else value)
        assignments.append("updated_at = now()")
        params.append(run.id)
        with self._connect() as conn:
            row = conn.execute(f"update job_runs set {', '.join(assignments)} where id = %s returning *", params).fetchone()
            conn.commit()
        return job_run_from_row(row)

    def list_job_runs(self, *, job_type: str | None, status: str | None, cursor: str | None, limit: int) -> tuple[list[JobRunRecord], str | None]:
        sql = "select * from job_runs where true"
        params: list[Any] = []
        if job_type:
            sql += " and job_type = %s"
            params.append(job_type)
        if status:
            sql += " and status = %s"
            params.append(status)
        if cursor:
            position = decode_keyset_cursor(cursor)
            sql += " and (created_at, id) < (%s, %s::uuid)"
            params.extend((position.timestamp, position.item_id))
        sql += " order by created_at desc, id desc limit %s"
        params.append(limit + 1)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        page = rows[:limit]
        items = [job_run_from_row(row) for row in page]
        next_cursor = (
            encode_keyset_cursor(items[-1].created_at, items[-1].id)
            if len(rows) > limit and items
            else None
        )
        return items, next_cursor

    def get_job_run(self, run_id: str) -> JobRunRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from job_runs where id = %s", (run_id,)).fetchone()
        return job_run_from_row(row) if row else None

    def enqueue_notification(self, **fields: Any) -> tuple[NotificationJobRecord, bool]:
        with self._connect() as conn:
            notification, created = self.enqueue_notification_in_transaction(conn, **fields)
            conn.commit()
        return notification, created

    def enqueue_notification_in_transaction(self, conn, **fields: Any) -> tuple[NotificationJobRecord, bool]:  # type: ignore[no-untyped-def]
        row = conn.execute(
                """
                insert into notification_jobs (
                    notification_type, recipient_user_id, recipient_role, order_id,
                    business_id, dispute_id, status, scheduled_for, attempts,
                    max_attempts, dedupe_key, metadata_json, created_at, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s, %s, %s, now(), now())
                on conflict (dedupe_key) do nothing
                returning *
                """,
                (
                    fields["notification_type"],
                    fields.get("recipient_user_id"),
                    fields.get("recipient_role"),
                    fields.get("order_id"),
                    fields.get("business_id"),
                    fields.get("dispute_id"),
                    fields["scheduled_for"],
                    fields.get("attempts", 0),
                    fields.get("max_attempts", 3),
                    fields["dedupe_key"],
                    jsonb_metadata(fields.get("metadata_json")),
                ),
        ).fetchone()
        created = row is not None
        if row is None:
            row = conn.execute(
                "select * from notification_jobs where dedupe_key = %s",
                (fields["dedupe_key"],),
            ).fetchone()
        return notification_from_row(row), created

    def list_due_notifications(self, *, now: datetime, limit: int) -> list[NotificationJobRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                with due as (
                    select id
                    from notification_jobs
                    where status = 'pending'
                      and scheduled_for <= %s
                    order by scheduled_for asc
                    limit %s
                    for update skip locked
                )
                update notification_jobs
                set scheduled_for = %s,
                    metadata_json = coalesce(metadata_json, '{}'::jsonb) || %s::jsonb,
                    updated_at = now()
                from due
                where notification_jobs.id = due.id
                returning notification_jobs.*
                """,
                (now, limit, now + timedelta(minutes=5), jsonb_metadata({"delivery_state": "processing"})),
            ).fetchall()
            conn.commit()
        return [notification_from_row(row) for row in rows]

    def list_due_telegram_notifications(self, *, now: datetime, limit: int, notification_types: set[str]) -> list[NotificationJobRecord]:
        notification_types_tuple = tuple(sorted(notification_types))
        type_placeholders = ", ".join(["%s"] * len(notification_types_tuple))
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                with due as (
                    select id
                    from notification_jobs
                    where status = 'pending'
                      and scheduled_for <= %s
                      and recipient_user_id is not null
                      and notification_type in ({type_placeholders})
                      and metadata_json->>'channel' = 'telegram'
                      and metadata_json->>'target_surface' in ('business_mini_app', 'client_mini_app')
                      and nullif(trim(metadata_json->>'message_text'), '') is not null
                    order by scheduled_for asc
                    limit %s
                    for update skip locked
                )
                update notification_jobs
                set scheduled_for = %s,
                    metadata_json = coalesce(metadata_json, '{{}}'::jsonb) || %s::jsonb,
                    updated_at = now()
                from due
                where notification_jobs.id = due.id
                returning notification_jobs.*
                """,
                (
                    now,
                    *notification_types_tuple,
                    limit,
                    now + timedelta(minutes=5),
                    jsonb_metadata({"delivery_state": "processing", "claimed_at": now.isoformat()}),
                ),
            ).fetchall()
            conn.commit()
        return [notification_from_row(row) for row in rows]

    def update_notification(self, notification: NotificationJobRecord, **fields: Any) -> NotificationJobRecord:
        assignments: list[str] = []
        params: list[Any] = []
        for key, value in fields.items():
            assignments.append(f"{key} = %s")
            params.append(jsonb_metadata(value) if key == "metadata_json" else value)
        assignments.append("updated_at = now()")
        params.append(notification.id)
        with self._connect() as conn:
            row = conn.execute(f"update notification_jobs set {', '.join(assignments)} where id = %s returning *", params).fetchone()
            conn.commit()
        return notification_from_row(row)

    def notification_incident_summary(self, *, limit: int) -> dict[str, Any]:
        with self._connect() as conn:
            counts = conn.execute("select status, count(*) as c from notification_jobs group by status").fetchall()
            pending_due = conn.execute("select count(*) as c from notification_jobs where status = 'pending' and scheduled_for <= now()").fetchone()["c"]
            rows = conn.execute(
                """
                select id, notification_type, status, recipient_user_id, recipient_role,
                       order_id, business_id, attempts, last_error_code, metadata_json,
                       created_at, updated_at
                from notification_jobs
                where status = 'failed'
                   or attempts > 0
                   or last_error_code is not null
                order by updated_at desc
                limit %s
                """,
                (limit,),
            ).fetchall()
        status_counts = {status: 0 for status in ["pending", "sent", "failed", "skipped", "cancelled"]}
        status_counts.update({row["status"]: row["c"] for row in counts})
        return {
            "status_counts": status_counts,
            "pending_due": pending_due,
            "recent_problems": [
                {
                    "id": str(row["id"]),
                    "notification_type": row["notification_type"],
                    "status": row["status"],
                    "recipient_role": row["recipient_role"],
                    "recipient_user_id": str(row["recipient_user_id"]) if row["recipient_user_id"] else None,
                    "order_id": str(row["order_id"]) if row["order_id"] else None,
                    "business_id": str(row["business_id"]) if row["business_id"] else None,
                    "attempts": row["attempts"],
                    "last_error_code": row["last_error_code"],
                    "metadata": mask_metadata(row["metadata_json"]),
                    "created_at": row["created_at"].isoformat(),
                    "updated_at": row["updated_at"].isoformat(),
                }
                for row in rows
            ],
        }
