from __future__ import annotations

from typing import Any

from app.modules.disputes.models import DisputeEventRecord, DisputeRecord
from app.modules.disputes.row_mappers import dispute_from_row, event_from_row, jsonb
from app.shared.db.connection import pooled_connect


class PostgresDisputeRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def get_open_for_order(self, order_id: str) -> DisputeRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from disputes where order_id = %s and status in ('open', 'in_review') limit 1", (order_id,)).fetchone()
        return dispute_from_row(row) if row else None

    def list_open_order_ids(self, order_ids: list[str]) -> set[str]:
        if not order_ids:
            return set()
        with self._connect() as conn:
            rows = conn.execute(
                """
                select order_id from disputes
                where order_id = any(%s)
                  and status in ('open', 'in_review')
                """,
                (order_ids,),
            ).fetchall()
        return {str(row["order_id"]) for row in rows}

    def create_dispute(
        self,
        *,
        order_id: str,
        opened_by_user_id: str,
        opened_by_role: str,
        previous_order_status: str,
        reason: str,
        description: str | None,
    ) -> DisputeRecord:
        with self._connect() as conn:
            existing = conn.execute("select * from disputes where order_id = %s and status in ('open', 'in_review') limit 1", (order_id,)).fetchone()
            if existing:
                return dispute_from_row(existing)
            row = conn.execute(
                """
                insert into disputes (
                    order_id, opened_by_user_id, opened_by_role, previous_order_status,
                    reason, description, status, created_at, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, 'open', now(), now())
                returning *
                """,
                (order_id, opened_by_user_id, opened_by_role, previous_order_status, reason, description),
            ).fetchone()
            conn.commit()
        return dispute_from_row(row)

    def add_event(self, *, dispute_id: str, order_id: str, actor_user_id: str, actor_role: str, event_type: str, old_status: str | None, new_status: str | None, reason: str | None, metadata_json: dict | None) -> DisputeEventRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                insert into dispute_events (
                    dispute_id, order_id, actor_user_id, actor_role, event_type,
                    old_status, new_status, reason, metadata_json, created_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                returning *
                """,
                (dispute_id, order_id, actor_user_id, actor_role, event_type, old_status, new_status, reason, jsonb(metadata_json)),
            ).fetchone()
            conn.commit()
        return event_from_row(row)

    def list_disputes(self, *, status: str | None, cursor: str | None, limit: int) -> tuple[list[DisputeRecord], str | None]:
        sql = "select * from disputes where true"
        params: list[Any] = []
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
        items = [dispute_from_row(row) for row in rows]
        return items, items[-1].created_at.isoformat() if len(items) == limit else None

    def get_dispute(self, dispute_id: str) -> DisputeRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from disputes where id = %s", (dispute_id,)).fetchone()
        return dispute_from_row(row) if row else None

    def update_dispute(self, dispute: DisputeRecord, **fields: Any) -> DisputeRecord:
        assignments: list[str] = []
        params: list[Any] = []
        for key, value in fields.items():
            assignments.append(f"{key} = %s")
            params.append(value)
        assignments.append("updated_at = now()")
        params.append(dispute.id)
        with self._connect() as conn:
            row = conn.execute(f"update disputes set {', '.join(assignments)} where id = %s returning *", params).fetchone()
            conn.commit()
        return dispute_from_row(row)

    def list_events(self, dispute_id: str) -> list[DisputeEventRecord]:
        with self._connect() as conn:
            rows = conn.execute("select * from dispute_events where dispute_id = %s order by created_at asc", (dispute_id,)).fetchall()
        return [event_from_row(row) for row in rows]
