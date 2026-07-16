from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.modules.jobs.models import JobRunRecord, NotificationJobRecord
from app.modules.jobs.row_mappers import job_run_from_row, jsonb_metadata, notification_from_row
from app.shared.db.connection import pooled_connect


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
            sql += " and created_at < %s"
            params.append(cursor)
        sql += " order by created_at desc limit %s"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        items = [job_run_from_row(row) for row in rows]
        return items, items[-1].created_at.isoformat() if len(items) == limit else None

    def get_job_run(self, run_id: str) -> JobRunRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from job_runs where id = %s", (run_id,)).fetchone()
        return job_run_from_row(row) if row else None

    def enqueue_notification(self, **fields: Any) -> tuple[NotificationJobRecord, bool]:
        with self._connect() as conn:
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
                row = conn.execute("select * from notification_jobs where dedupe_key = %s", (fields["dedupe_key"],)).fetchone()
            conn.commit()
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
                    jsonb_metadata({"delivery_state": "processing"}),
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
