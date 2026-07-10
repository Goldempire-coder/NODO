from __future__ import annotations

from app.modules.orders.models import OrderStateEventRecord
from app.modules.orders.row_mappers import jsonb, state_event_from_row


class PostgresOrderStateEventsMixin:
    def add_state_event(
        self,
        *,
        order_id: str,
        from_status: str | None,
        to_status: str,
        event_type: str,
        actor_user_id: str | None,
        actor_role: str | None,
        reason: str | None,
        request_id: str,
        metadata_json: dict | None = None,
    ) -> OrderStateEventRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                insert into order_state_events (
                    order_id, from_status, to_status, event_type, actor_user_id,
                    actor_role, reason, request_id, metadata_json, created_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                returning *
                """,
                (order_id, from_status, to_status, event_type, actor_user_id, actor_role, reason, request_id, jsonb(metadata_json)),
            ).fetchone()
            conn.commit()
        return state_event_from_row(row)

    def list_state_events_for_order(self, order_id: str) -> list[OrderStateEventRecord]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(
                "select * from order_state_events where order_id = %s order by created_at asc",
                (order_id,),
            ).fetchall()
        return [state_event_from_row(row) for row in rows]
