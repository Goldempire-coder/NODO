from __future__ import annotations

from typing import Any

from app.modules.admin_notifications.models import AdminNotificationRecord
from app.shared.db.connection import pooled_connect
from app.shared.keyset_pagination import decode_keyset_cursor, encode_keyset_cursor


def _jsonb_metadata(value: dict | None) -> Any:
    try:
        from psycopg.types.json import Jsonb

        return Jsonb(value or {})
    except Exception:
        return value or {}


def _record_from_row(row) -> AdminNotificationRecord:  # type: ignore[no-untyped-def]
    return AdminNotificationRecord(
        id=str(row["id"]),
        notification_type=row["notification_type"],
        priority=row["priority"],
        status=row["status"],
        source_surface=row["source_surface"],
        resource_type=row["resource_type"],
        resource_id=str(row["resource_id"]) if row["resource_id"] else None,
        business_id=str(row["business_id"]) if row["business_id"] else None,
        actor_user_id=str(row["actor_user_id"]) if row["actor_user_id"] else None,
        title=row["title"],
        summary=row["summary"],
        action_route=row["action_route"],
        dedupe_key=row["dedupe_key"],
        metadata_json=row["metadata_json"] or {},
        first_seen_at=row["first_seen_at"],
        last_seen_at=row["last_seen_at"],
        read_at=row["read_at"],
        read_by_user_id=str(row["read_by_user_id"]) if row["read_by_user_id"] else None,
        dismissed_at=row["dismissed_at"],
        dismissed_by_user_id=str(row["dismissed_by_user_id"]) if row["dismissed_by_user_id"] else None,
        resolved_at=row["resolved_at"],
        resolved_by_user_id=str(row["resolved_by_user_id"]) if row["resolved_by_user_id"] else None,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PostgresAdminNotificationRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def upsert_notification(self, **fields: Any) -> tuple[AdminNotificationRecord, bool]:
        with self._connect() as conn:
            row = conn.execute(
                """
                insert into admin_notifications (
                    notification_type, priority, status, source_surface, resource_type,
                    resource_id, business_id, actor_user_id, title, summary,
                    action_route, dedupe_key, metadata_json, created_at, updated_at,
                    first_seen_at, last_seen_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now(), now(), now())
                on conflict (dedupe_key) do update
                set priority = excluded.priority,
                    source_surface = excluded.source_surface,
                    resource_type = excluded.resource_type,
                    resource_id = excluded.resource_id,
                    business_id = excluded.business_id,
                    actor_user_id = excluded.actor_user_id,
                    title = excluded.title,
                    summary = excluded.summary,
                    action_route = excluded.action_route,
                    metadata_json = excluded.metadata_json,
                    last_seen_at = now(),
                    updated_at = now()
                returning *, (xmax = 0) as created
                """,
                (
                    fields["notification_type"],
                    fields["priority"],
                    fields.get("status", "unread"),
                    fields.get("source_surface"),
                    fields["resource_type"],
                    fields.get("resource_id"),
                    fields.get("business_id"),
                    fields.get("actor_user_id"),
                    fields["title"],
                    fields["summary"],
                    fields.get("action_route"),
                    fields["dedupe_key"],
                    _jsonb_metadata(fields.get("metadata_json")),
                ),
            ).fetchone()
            conn.commit()
        return _record_from_row(row), bool(row["created"])

    def get(self, notification_id: str) -> AdminNotificationRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from admin_notifications where id = %s", (notification_id,)).fetchone()
        return _record_from_row(row) if row else None

    def list_notifications(
        self,
        *,
        status: str | None,
        priority: str | None,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[AdminNotificationRecord], str | None]:
        sql = "select * from admin_notifications where true"
        params: list[Any] = []
        if status:
            sql += " and status = %s"
            params.append(status)
        if priority:
            sql += " and priority = %s"
            params.append(priority)
        if cursor:
            position = decode_keyset_cursor(cursor)
            sql += " and (last_seen_at, id) < (%s, %s::uuid)"
            params.extend((position.timestamp, position.item_id))
        sql += " order by last_seen_at desc, id desc limit %s"
        params.append(limit + 1)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        page = rows[:limit]
        items = [_record_from_row(row) for row in page]
        next_cursor = (
            encode_keyset_cursor(items[-1].last_seen_at, items[-1].id)
            if len(rows) > limit and items
            else None
        )
        return items, next_cursor

    def unread_count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("select count(*) as c from admin_notifications where status = 'unread'").fetchone()
        return int(row["c"])

    def unread_count_by_resource_type(self, resource_type: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "select count(*) as c from admin_notifications where status = 'unread' and resource_type = %s",
                (resource_type,),
            ).fetchone()
        return int(row["c"])

    def update_notification(self, notification: AdminNotificationRecord, **fields: Any) -> AdminNotificationRecord:
        assignments: list[str] = []
        params: list[Any] = []
        for key, value in fields.items():
            assignments.append(f"{key} = %s")
            params.append(_jsonb_metadata(value) if key == "metadata_json" else value)
        assignments.append("updated_at = now()")
        params.append(notification.id)
        with self._connect() as conn:
            row = conn.execute(f"update admin_notifications set {', '.join(assignments)} where id = %s returning *", params).fetchone()
            conn.commit()
        return _record_from_row(row)
