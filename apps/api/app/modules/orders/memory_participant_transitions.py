from __future__ import annotations

from app.core.errors import ApiError
from app.modules.disputes.models import DisputeRecord
from app.modules.disputes.policy import (
    require_dispute_order_state,
    require_dispute_reason,
)
from app.modules.orders.models import OrderRecord
from app.modules.orders.state_machine import (
    extended_deadline,
    now_utc,
    require_extend_allowed,
)


class InMemoryParticipantTransitionsMixin:
    def open_participant_dispute_atomically(
        self,
        *,
        order_id: str,
        expected_status: str,
        actor_user_id: str,
        actor_role: str,
        business_owner_user_id: str | None,
        reason: str,
        description: str | None,
        evidence_file_ids: list[str],
        request_id: str,
    ) -> tuple[OrderRecord, DisputeRecord]:
        with self._lock:
            order = self.orders.get(order_id)
            if order is None or not (
                (actor_role == "remitter" and order.remitter_user_id == actor_user_id)
                or (
                    actor_role == "business_owner"
                    and business_owner_user_id == actor_user_id
                )
            ):
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if self._disputes is None or self._audit is None:
                raise ApiError("DISPUTE_STORAGE_UNAVAILABLE", status_code=503)
            with self._disputes._lock, self._audit._lock:
                if self._disputes.get_open_for_order(order_id) is not None:
                    raise ApiError("DISPUTE_ALREADY_OPEN", status_code=409)
                if order.status != expected_status:
                    raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
                require_dispute_order_state(order)
                require_dispute_reason(reason)
                previous_ids = set(self._disputes.disputes)
                dispute_events = len(self._disputes.events)
                order_events, audit_events = len(self.events), len(self._audit.events)
                try:
                    dispute = self._disputes.create_dispute(
                        order_id=order_id,
                        opened_by_user_id=actor_user_id,
                        opened_by_role=actor_role,
                        previous_order_status=expected_status,
                        reason=reason,
                        description=description,
                    )
                    self._disputes.add_event(
                        dispute_id=dispute.id,
                        order_id=order_id,
                        actor_user_id=actor_user_id,
                        actor_role=actor_role,
                        event_type="dispute_opened",
                        old_status=None,
                        new_status="open",
                        reason=reason,
                        metadata_json={
                            "previous_order_status": expected_status,
                            "evidence_file_ids": evidence_file_ids,
                        },
                    )
                    self.add_state_event(
                        order_id=order_id,
                        from_status=expected_status,
                        to_status="disputed",
                        event_type="dispute_opened",
                        actor_user_id=actor_user_id,
                        actor_role=actor_role,
                        reason=reason,
                        request_id=request_id,
                        metadata_json={
                            "dispute_id": dispute.id,
                            "previous_order_status": expected_status,
                        },
                    )
                    self._audit.write(
                        event_type="dispute_opened",
                        actor_user_id=actor_user_id,
                        actor_role=actor_role,
                        resource_type="dispute",
                        resource_id=dispute.id,
                        request_id=request_id,
                        metadata_json={
                            "order_id": order_id,
                            "previous_order_status": expected_status,
                            "new_order_status": "disputed",
                            "reason": reason,
                        },
                    )
                except Exception:
                    # All writers are locked; discard only this failed operation.
                    for dispute_id in set(self._disputes.disputes) - previous_ids:
                        del self._disputes.disputes[dispute_id]
                    del self._disputes.events[dispute_events:]
                    del self.events[order_events:]
                    del self._audit.events[audit_events:]
                    raise
                order.status = "disputed"
                order.dispute_reason = reason
                order.updated_at = now_utc()
                return order, dispute

    def extend_payment_deadline_atomically(
        self,
        *,
        order_id: str,
        remitter_user_id: str,
        reason: str | None,
        request_id: str,
    ) -> OrderRecord:
        with self._lock:
            order = self.orders.get(order_id)
            if order is None or order.remitter_user_id != remitter_user_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if self._audit is None:
                raise ApiError("INTERNAL_ERROR", status_code=500)
            with self._audit._lock:
                require_extend_allowed(order)
                deadline = extended_deadline(order)
                order_events, audit_events = len(self.events), len(self._audit.events)
                try:
                    self.add_state_event(
                        order_id=order_id,
                        from_status="waiting_payment",
                        to_status="waiting_payment",
                        event_type="waiting_payment_extended",
                        actor_user_id=remitter_user_id,
                        actor_role="remitter",
                        reason=reason,
                        request_id=request_id,
                        metadata_json={"minutes_added": 15},
                    )
                    self._audit.write(
                        event_type="payment_deadline_extended",
                        actor_user_id=remitter_user_id,
                        actor_role="remitter",
                        resource_type="order",
                        resource_id=order_id,
                        request_id=request_id,
                        metadata_json={"reason": reason},
                    )
                except Exception:
                    del self.events[order_events:]
                    del self._audit.events[audit_events:]
                    raise
                order.extension_used = True
                order.payment_report_extension_used_at = now_utc()
                order.payment_report_deadline_at = deadline
                order.expires_at = deadline
                order.updated_at = now_utc()
                return order
