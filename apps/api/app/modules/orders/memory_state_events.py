from __future__ import annotations

from app.modules.orders.models import OrderStateEventRecord, new_id


class InMemoryOrderStateEventsMixin:
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
        event = OrderStateEventRecord(
            id=new_id(),
            order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            event_type=event_type,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            reason=reason,
            request_id=request_id,
            metadata_json=metadata_json,
        )
        with self._lock:  # type: ignore[attr-defined]
            self.events.append(event)  # type: ignore[attr-defined]
        return event

    def list_state_events_for_order(self, order_id: str) -> list[OrderStateEventRecord]:
        return sorted([event for event in self.events if event.order_id == order_id], key=lambda event: event.created_at)  # type: ignore[attr-defined]
