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

    def __init__(self, *, capacity_repository=None, audit_writer=None) -> None:  # type: ignore[no-untyped-def]
        self._lock = RLock()
        self._capacity = capacity_repository
        self._audit = audit_writer
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
        return sum(
            1
            for order in self.orders.values()
            if order.business_id == business_id
            and order.status
            in {
                "waiting_payment",
                "payment_reported",
                "payment_rejected",
                "payment_confirmed",
                "delivered",
                "disputed",
            }
        )

    def create_order(self, **fields: Any) -> OrderRecord:
        with self._lock:
            capacity_reservation = fields.pop("capacity_reservation", None)
            now = utc_now()
            order = OrderRecord(
                id=new_id(),
                public_order_code=new_public_order_code(),
                created_at=now,
                updated_at=now,
                **fields,
            )
            if capacity_reservation is not None and self._capacity is not None:
                self._capacity.reserve(
                    order_id=order.id,
                    business=capacity_reservation["business"],
                    amount_usd=capacity_reservation["amount_usd"],
                    reason=capacity_reservation["reason"],
                )
            self.orders[order.id] = order
            return order

    def update_order(self, order: OrderRecord, **fields: Any) -> OrderRecord:
        with self._lock:
            capacity_event_context = fields.pop("capacity_event_context", None)
            target_status = fields.get("status")
            transition_event = None
            changed = False
            if self._capacity is not None and target_status == "cancelled":
                transition_event = "business_capacity_released"
                changed = self._capacity.release(
                    order_id=order.id,
                    reason=(capacity_event_context or {}).get("reason", "order_cancelled"),
                )
            elif self._capacity is not None and target_status == "completed":
                transition_event = "business_capacity_consumed"
                changed = self._capacity.consume(
                    order_id=order.id,
                    reason=(capacity_event_context or {}).get("reason", "order_completed"),
                )
            for key, value in fields.items():
                setattr(order, key, value)
            order.updated_at = utc_now()
            if changed and transition_event and self._audit is not None:
                context = capacity_event_context or {}
                self._audit.write(
                    event_type=transition_event,
                    actor_user_id=context.get("actor_user_id"),
                    actor_role=context.get("actor_role"),
                    resource_type="order",
                    resource_id=order.id,
                    request_id=context.get("request_id", "capacity_transition"),
                    metadata_json={"reason": context.get("reason")},
                )
            return order

