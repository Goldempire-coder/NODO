from __future__ import annotations

from app.core.errors import ApiError
from app.modules.orders.models import OrderRecord
from app.modules.orders.row_mappers import jsonb, order_from_row
from app.modules.orders.state_machine import (
    extended_deadline,
    now_utc,
    require_extend_allowed,
)


class PostgresDeadlineExtensionMixin:
    def extend_payment_deadline_atomically(
        self,
        *,
        order_id: str,
        remitter_user_id: str,
        reason: str | None,
        request_id: str,
    ) -> OrderRecord:
        with self._connect() as conn:
            row = conn.execute(
                "select * from orders where id = %s for update",
                (order_id,),
            ).fetchone()
            if row is None or str(row["remitter_user_id"]) != remitter_user_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            order = order_from_row(row)
            require_extend_allowed(order)
            deadline, transition_at = extended_deadline(order), now_utc()
            updated = conn.execute(
                """
                update orders set extension_used = true, payment_report_extension_used_at = %s,
                    payment_report_deadline_at = %s, expires_at = %s, updated_at = now()
                where id = %s and status = 'waiting_payment' and extension_used = false
                    and paid_reported_at is null and payment_report_deadline_at > %s
                returning *
                """,
                (transition_at, deadline, deadline, order_id, transition_at),
            ).fetchone()
            if updated is None:
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            conn.execute(
                """
                insert into order_state_events (
                    order_id, from_status, to_status, event_type, actor_user_id,
                    actor_role, reason, request_id, metadata_json, created_at
                ) values (%s, 'waiting_payment', 'waiting_payment', 'waiting_payment_extended',
                          %s, 'remitter', %s, %s, %s, now())
                """,
                (
                    order_id,
                    remitter_user_id,
                    reason,
                    request_id,
                    jsonb({"minutes_added": 15}),
                ),
            )
            conn.execute(
                """
                insert into audit_logs (
                    actor_user_id, actor_role, event_type, resource_type,
                    resource_id, request_id, metadata_json, created_at
                ) values (%s, 'remitter', 'payment_deadline_extended', 'order', %s, %s, %s, now())
                """,
                (remitter_user_id, order_id, request_id, jsonb({"reason": reason})),
            )
            result = order_from_row(updated)
        return result
