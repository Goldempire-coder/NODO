from __future__ import annotations

from typing import Any

from app.modules.orders.models import OrderRecord
from app.modules.orders.postgres_create_order import PostgresCreateOrderMixin
from app.modules.orders.postgres_payment_confirmation import PostgresPaymentConfirmationMixin
from app.modules.orders.postgres_payment_reports import PostgresPaymentReportsMixin
from app.modules.orders.postgres_queries import PostgresOrderQueriesMixin
from app.modules.orders.postgres_state_events import PostgresOrderStateEventsMixin
from app.modules.orders.row_mappers import jsonb, order_from_row
from app.shared.db.connection import pooled_connect


class PostgresOrderRepository(
    PostgresCreateOrderMixin,
    PostgresPaymentConfirmationMixin,
    PostgresPaymentReportsMixin,
    PostgresOrderQueriesMixin,
    PostgresOrderStateEventsMixin,
):
    moves_ad_on_create_order = True
    creates_initial_state_event_on_create_order = True

    def __init__(self, database_url: str, *, capacity_repository=None) -> None:  # type: ignore[no-untyped-def]
        self._database_url = database_url
        self._capacity = capacity_repository

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def get_by_id(self, order_id: str) -> OrderRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from orders where id = %s", (order_id,)).fetchone()
        return order_from_row(row) if row else None

    def get_by_idempotency_key(self, *, remitter_user_id: str, idempotency_key: str) -> OrderRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "select * from orders where remitter_user_id = %s and idempotency_key = %s limit 1",
                (remitter_user_id, idempotency_key),
            ).fetchone()
        return order_from_row(row) if row else None

    def count_active_for_business(self, business_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "select count(*) as count from orders where business_id = %s and status = 'waiting_payment'",
                (business_id,),
            ).fetchone()
        return int(row["count"])

    def update_order(self, order: OrderRecord, **fields: Any) -> OrderRecord:
        capacity_event_context = fields.pop("capacity_event_context", None)
        assignments: list[str] = []
        params: list[Any] = []
        for key, value in fields.items():
            assignments.append(f"{key} = %s")
            params.append(value)
        assignments.append("updated_at = now()")
        params.append(order.id)
        with self._connect() as conn:
            row = conn.execute(f"update orders set {', '.join(assignments)} where id = %s returning *", params).fetchone()
            target_status = fields.get("status")
            changed = False
            event_type = None
            if self._capacity is not None and target_status == "cancelled":
                event_type = "business_capacity_released"
                changed = self._capacity.transition_in_transaction(
                    conn,
                    order_id=order.id,
                    target_status="released",
                    reason=(capacity_event_context or {}).get("reason", "order_cancelled"),
                )
            elif self._capacity is not None and target_status == "completed":
                event_type = "business_capacity_consumed"
                changed = self._capacity.transition_in_transaction(
                    conn,
                    order_id=order.id,
                    target_status="consumed",
                    reason=(capacity_event_context or {}).get("reason", "order_completed"),
                )
            if changed and event_type:
                self._insert_capacity_transition_audit(
                    conn,
                    order_id=order.id,
                    event_type=event_type,
                    context=capacity_event_context or {},
                )
            conn.commit()
        return order_from_row(row)

    def _insert_capacity_transition_audit(
        self,
        conn,
        *,
        order_id: str,
        event_type: str,
        context: dict[str, Any],
    ) -> None:  # type: ignore[no-untyped-def]
        conn.execute(
            """
            insert into audit_logs (
                actor_user_id, actor_role, event_type, resource_type,
                resource_id, request_id, metadata_json, created_at
            )
            values (%s, %s, %s, 'order', %s, %s, %s, now())
            """,
            (
                context.get("actor_user_id"),
                context.get("actor_role"),
                event_type,
                order_id,
                context.get("request_id", "capacity_transition"),
                jsonb({"reason": context.get("reason")}),
            ),
        )

