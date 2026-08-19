from __future__ import annotations

from typing import Any

from app.modules.admin.presenters import mask_sensitive
from app.shared.keyset_pagination import decode_keyset_cursor, encode_keyset_cursor


class PostgresAdminAuditMixin:
    def list_audit_logs(self, *, event_type: str | None, actor_user_id: str | None, resource_type: str | None, resource_id: str | None, cursor: str | None, limit: int) -> tuple[list[dict[str, Any]], str | None]:
        sql = "select id, event_type, actor_user_id, actor_role, resource_type, resource_id, metadata_json, created_at from audit_logs where true"
        params: list[Any] = []
        for column, value in (("event_type", event_type), ("actor_user_id", actor_user_id), ("resource_type", resource_type), ("resource_id", resource_id)):
            if value:
                sql += f" and {column} = %s"
                params.append(value)
        if cursor:
            position = decode_keyset_cursor(cursor)
            sql += " and (created_at, id) < (%s, %s::uuid)"
            params.extend((position.timestamp, position.item_id))
        sql += " order by created_at desc, id desc limit %s"
        params.append(limit + 1)
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(sql, params).fetchall()
        page = rows[:limit]
        items = []
        for row in page:
            items.append(
                {
                    "id": str(row["id"]),
                    "event_type": row["event_type"],
                    "actor_user_id": str(row["actor_user_id"]) if row["actor_user_id"] else None,
                    "actor_role": row["actor_role"],
                    "resource_type": row["resource_type"],
                    "resource_id": str(row["resource_id"]) if row["resource_id"] else None,
                    "metadata_json": mask_sensitive(row["metadata_json"]),
                    "created_at": row["created_at"].isoformat(),
                }
            )
        next_cursor = encode_keyset_cursor(page[-1]["created_at"], str(page[-1]["id"])) if len(rows) > limit else None
        return items, next_cursor
