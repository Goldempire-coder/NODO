from __future__ import annotations

from app.core.errors import ApiError
from app.modules.disputes.models import DisputeRecord
from app.modules.disputes.row_mappers import dispute_from_row
from app.modules.orders.models import OrderRecord
from app.modules.orders.row_mappers import jsonb, order_from_row


class PostgresAdminDisputeOpeningMixin:
    def open_admin_dispute_atomically(
        self,
        *,
        order_id: str,
        actor_user_id: str,
        actor_role: str,
        reason: str,
        request_id: str,
    ) -> tuple[OrderRecord, DisputeRecord]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            order_row = conn.execute(
                "select * from orders where id = %s for update",
                (order_id,),
            ).fetchone()
            if order_row is None:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if order_row["status"] != "payment_rejected":
                raise ApiError("ORDER_STATUS_INVALID", status_code=409)

            existing = conn.execute(
                "select id from disputes where order_id = %s and status in ('open', 'in_review') limit 1",
                (order_id,),
            ).fetchone()
            if existing is not None:
                raise ApiError("DISPUTE_ALREADY_OPEN", status_code=409)

            dispute_row = conn.execute(
                """
                insert into disputes (
                    order_id, opened_by_user_id, opened_by_role, previous_order_status,
                    reason, description, status, created_at, updated_at
                )
                values (%s, %s, %s, 'payment_rejected', 'other', %s, 'open', now(), now())
                returning *
                """,
                (order_id, actor_user_id, actor_role, reason),
            ).fetchone()
            updated_order_row = conn.execute(
                """
                update orders
                set status = 'disputed', dispute_reason = 'other', updated_at = now()
                where id = %s and status = 'payment_rejected'
                returning *
                """,
                (order_id,),
            ).fetchone()
            if updated_order_row is None:
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)

            dispute_id = str(dispute_row["id"])
            metadata = {
                "dispute_id": dispute_id,
                "previous_order_status": "payment_rejected",
                "opened_via": "admin_order_investigation",
            }
            conn.execute(
                """
                insert into dispute_events (
                    dispute_id, order_id, actor_user_id, actor_role, event_type,
                    old_status, new_status, reason, metadata_json, created_at
                )
                values (%s, %s, %s, %s, 'dispute_opened', null, 'open', %s, %s, now())
                """,
                (dispute_id, order_id, actor_user_id, actor_role, reason, jsonb(metadata)),
            )
            conn.execute(
                """
                insert into order_state_events (
                    order_id, from_status, to_status, event_type, actor_user_id,
                    actor_role, reason, request_id, metadata_json, created_at
                )
                values (%s, 'payment_rejected', 'disputed', 'dispute_opened', %s, %s, %s, %s, %s, now())
                """,
                (order_id, actor_user_id, actor_role, reason, request_id, jsonb(metadata)),
            )
            conn.execute(
                """
                insert into audit_logs (
                    actor_user_id, actor_role, event_type, resource_type,
                    resource_id, request_id, metadata_json, created_at
                )
                values (%s, %s, 'admin_order_dispute_opened', 'dispute', %s, %s, %s, now())
                """,
                (
                    actor_user_id,
                    actor_role,
                    dispute_id,
                    request_id,
                    jsonb(
                        {
                            "order_id": order_id,
                            "previous_order_status": "payment_rejected",
                            "new_order_status": "disputed",
                            "reason": reason,
                        }
                    ),
                ),
            )

        return order_from_row(updated_order_row), dispute_from_row(dispute_row)
