from __future__ import annotations

from typing import Any

from app.modules.orders.models import OrderRecord
from app.modules.orders.postgres_create_order import PostgresCreateOrderMixin
from app.modules.orders.postgres_payment_confirmation import PostgresPaymentConfirmationMixin
from app.modules.orders.postgres_payment_reports import PostgresPaymentReportsMixin
from app.modules.orders.postgres_queries import PostgresOrderQueriesMixin
from app.modules.orders.postgres_state_events import PostgresOrderStateEventsMixin
from app.modules.orders.row_mappers import order_from_row
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

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

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
        assignments: list[str] = []
        params: list[Any] = []
        for key, value in fields.items():
            assignments.append(f"{key} = %s")
            params.append(value)
        assignments.append("updated_at = now()")
        params.append(order.id)
        with self._connect() as conn:
            row = conn.execute(f"update orders set {', '.join(assignments)} where id = %s returning *", params).fetchone()
            conn.commit()
        return order_from_row(row)

