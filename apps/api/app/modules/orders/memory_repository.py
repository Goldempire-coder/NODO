from __future__ import annotations

from threading import RLock
from typing import Any

from app.modules.businesses.models import FileAssetRecord
from app.modules.orders.memory_payment_reports import InMemoryOrderPaymentReportsMixin
from app.modules.orders.memory_queries import InMemoryOrderQueriesMixin
from app.modules.orders.memory_state_events import InMemoryOrderStateEventsMixin
from app.modules.orders.models import OrderRecord, OrderStateEventRecord, PaymentReportRecord, new_id, new_public_order_code, utc_now


class InMemoryOrderRepository(InMemoryOrderPaymentReportsMixin, InMemoryOrderQueriesMixin, InMemoryOrderStateEventsMixin):
    moves_ad_on_create_order = False
    creates_initial_state_event_on_create_order = False

    def __init__(self) -> None:
        self._lock = RLock()
        self.orders: dict[str, OrderRecord] = {}
        self.events: list[OrderStateEventRecord] = []
        self.payment_reports: dict[str, PaymentReportRecord] = {}
        self.files: dict[str, FileAssetRecord] = {}

    def get_by_id(self, order_id: str) -> OrderRecord | None:
        return self.orders.get(order_id)

    def get_by_idempotency_key(self, *, remitter_user_id: str, idempotency_key: str) -> OrderRecord | None:
        for order in self.orders.values():
            if order.remitter_user_id == remitter_user_id and order.idempotency_key == idempotency_key:
                return order
        return None

    def count_active_for_business(self, business_id: str) -> int:
        return sum(1 for order in self.orders.values() if order.business_id == business_id and order.status == "waiting_payment")

    def create_order(self, **fields: Any) -> OrderRecord:
        with self._lock:
            now = utc_now()
            order = OrderRecord(
                id=new_id(),
                public_order_code=new_public_order_code(),
                created_at=now,
                updated_at=now,
                **fields,
            )
            self.orders[order.id] = order
            return order

    def update_order(self, order: OrderRecord, **fields: Any) -> OrderRecord:
        with self._lock:
            for key, value in fields.items():
                setattr(order, key, value)
            order.updated_at = utc_now()
            return order

