from __future__ import annotations

from typing import Any

from app.modules.admin.presenters import mask_sensitive


class PostgresAdminAuditMixin:
    def list_audit_logs(self, *, event_type: str | None, actor_user_id: str | None, resource_type: str | None, resource_id: str | None, cursor: str | None, limit: int) -> tuple[list[dict[str, Any]], str | None]:
        sql = "select event_type, actor_user_id, actor_role, resource_type, resource_id, metadata_json, created_at from audit_logs where true"
        params: list[Any] = []
        for column, value in (("event_type", event_type), ("actor_user_id", actor_user_id), ("resource_type", resource_type), ("resource_id", resource_id)):
            if value:
                sql += f" and {column} = %s"
                params.append(value)
        if cursor:
            sql += " and created_at < %s"
            params.append(cursor)
        sql += " order by created_at desc limit %s"
        params.append(limit)
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(sql, params).fetchall()
        items = []
        for row in rows:
            items.append(
                {
                    "event_type": row["event_type"],
                    "actor_user_id": str(row["actor_user_id"]) if row["actor_user_id"] else None,
                    "actor_role": row["actor_role"],
                    "resource_type": row["resource_type"],
                    "resource_id": str(row["resource_id"]) if row["resource_id"] else None,
                    "metadata_json": mask_sensitive(row["metadata_json"]),
                    "created_at": row["created_at"].isoformat(),
                }
            )
        return items, rows[-1]["created_at"].isoformat() if len(rows) == limit else None
