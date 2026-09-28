from __future__ import annotations

from datetime import datetime
from typing import Any

from app.modules.disputes.models import DisputeRecord
from app.modules.orders.models import OrderRecord, utc_now
from app.modules.orders.overdue_dispute_rules import (
    OVERDUE_DISPUTE_DESCRIPTION,
    OVERDUE_DISPUTE_RULES,
)


class InMemoryOrderJobTransitionsMixin:
    def open_overdue_dispute_atomically(
        self,
        *,
        order_id: str,
        reason: str,
        transition_at: datetime,
        request_id: str,
        event_metadata: dict[str, Any],
    ) -> tuple[OrderRecord, DisputeRecord] | None:
        expected_status, deadline_field, event_type = OVERDUE_DISPUTE_RULES[reason]
        with self._lock:  # type: ignore[attr-defined]
            order = self.orders.get(order_id)  # type: ignore[attr-defined]
            if (
                order is None
                or order.status != expected_status
                or getattr(order, deadline_field) is None
                or getattr(order, deadline_field) > transition_at
            ):
                return None
            if self._disputes.get_open_for_order(order_id) is not None:  # type: ignore[attr-defined]
                return None
            dispute = self._disputes.create_dispute(  # type: ignore[attr-defined]
                order_id=order_id,
                opened_by_user_id=order.remitter_user_id,
                opened_by_role="remitter",
                previous_order_status=expected_status,
                reason=reason,
                description=OVERDUE_DISPUTE_DESCRIPTION,
            )
            order.status = "disputed"
            order.dispute_reason = reason
            order.updated_at = utc_now()
            self._disputes.add_event(  # type: ignore[attr-defined]
                dispute_id=dispute.id,
                order_id=order_id,
                actor_user_id=order.remitter_user_id,
                actor_role="remitter",
                event_type="dispute_opened",
                old_status=None,
                new_status=dispute.status,
                reason=reason,
                metadata_json=event_metadata,
            )
            self.add_state_event(  # type: ignore[attr-defined]
                order_id=order_id,
                from_status=expected_status,
                to_status="disputed",
                event_type=event_type,
                actor_user_id=None,
                actor_role=None,
                reason=reason,
                request_id=request_id,
                metadata_json=event_metadata,
            )
            if self._audit is not None:  # type: ignore[attr-defined]
                self._audit.write(  # type: ignore[attr-defined]
                    event_type=event_type,
                    actor_user_id=None,
                    actor_role=None,
                    resource_type="order",
                    resource_id=order_id,
                    request_id=request_id,
                    metadata_json={**event_metadata, "dispute_id": dispute.id},
                )
            return order, dispute
