from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.errors import ApiError
from app.modules.orders.models import OrderReceiverDetailsRecord, OrderRecord, new_id, utc_now


class InMemoryOrderReceiverCompletionMixin:
    def create_receiver_details_atomically(
        self,
        *,
        order_id: str,
        remitter_user_id: str,
        payload: dict[str, str],
        payload_hash: str,
        request_id: str,
        audit_metadata: dict[str, Any],
    ) -> tuple[OrderReceiverDetailsRecord, bool]:
        with self._lock:  # type: ignore[attr-defined]
            order = self.orders.get(order_id)  # type: ignore[attr-defined]
            if order is None or order.remitter_user_id != remitter_user_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            existing = self.receiver_details.get(order_id)  # type: ignore[attr-defined]
            if existing is not None:
                if existing.payload_hash == payload_hash:
                    return existing, False
                raise ApiError("ORDER_RECEIVER_DETAILS_ALREADY_SHARED", status_code=409)
            if order.status != "payment_confirmed":
                raise ApiError("ORDER_STATUS_INVALID", status_code=409)
            record = OrderReceiverDetailsRecord(
                id=new_id(),
                order_id=order.id,
                bank_code=payload["bank"],
                phone=payload["phone"],
                document=payload["document"],
                holder=payload["holder"],
                payload_hash=payload_hash,
                shared_by_user_id=remitter_user_id,
            )
            if self._audit is not None:  # type: ignore[attr-defined]
                self._audit.write(  # type: ignore[attr-defined]
                    event_type="order_receiver_details_shared",
                    actor_user_id=remitter_user_id,
                    actor_role="remitter",
                    resource_type="order_receiver_details",
                    resource_id=record.id,
                    request_id=request_id,
                    metadata_json=audit_metadata,
                )
            self.receiver_details[order_id] = record  # type: ignore[attr-defined]
            return record, True

    def has_receiver_details(self, order_id: str) -> bool:
        return order_id in self.receiver_details  # type: ignore[attr-defined]

    def receiver_details_order_ids(self, order_ids: list[str]) -> set[str]:
        return set(order_ids).intersection(self.receiver_details)  # type: ignore[attr-defined]

    def get_receiver_details(self, order_id: str) -> OrderReceiverDetailsRecord | None:
        return self.receiver_details.get(order_id)  # type: ignore[attr-defined]

    def reveal_receiver_details_with_audit(
        self,
        *,
        order_id: str,
        actor_user_id: str,
        actor_role: str,
        business_owner_user_id: str | None,
        request_id: str,
        audit_metadata: dict[str, Any],
    ) -> OrderReceiverDetailsRecord:
        with self._lock:  # type: ignore[attr-defined]
            order = self.orders.get(order_id)  # type: ignore[attr-defined]
            if order is None:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            is_remitter = actor_role == "remitter" and order.remitter_user_id == actor_user_id
            is_business_owner = actor_role == "business_owner" and business_owner_user_id == actor_user_id
            if not (is_remitter or is_business_owner):
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if order.status not in {"payment_confirmed", "delivered", "disputed"}:
                raise ApiError("ORDER_STATUS_INVALID", status_code=409)
            record = self.receiver_details.get(order_id)  # type: ignore[attr-defined]
            if record is None:
                raise ApiError("ORDER_RECEIVER_DETAILS_NOT_FOUND", status_code=404)
            if self._audit is None:  # type: ignore[attr-defined]
                raise ApiError("INTERNAL_ERROR", status_code=500)
            self._audit.write(  # type: ignore[attr-defined]
                event_type="order_receiver_details_viewed",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                resource_type="order_receiver_details",
                resource_id=record.id,
                request_id=request_id,
                metadata_json=audit_metadata,
            )
            return record

    def mark_delivered_atomically(
        self,
        *,
        order_id: str,
        business_id: str,
        actor_user_id: str,
        actor_role: str,
        delivered_at: datetime,
        warning_12h_at: datetime,
        warning_23h_at: datetime,
        auto_complete_at: datetime,
        reason: str | None,
        request_id: str,
        event_metadata: dict[str, Any],
        audit_metadata: dict[str, Any],
    ) -> OrderRecord:
        with self._lock:  # type: ignore[attr-defined]
            order = self.orders.get(order_id)  # type: ignore[attr-defined]
            if order is None or order.business_id != business_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if order.status != "payment_confirmed":
                raise ApiError("DELIVERY_NOT_ALLOWED", status_code=409)
            if order_id not in self.receiver_details:  # type: ignore[attr-defined]
                raise ApiError("ORDER_RECEIVER_DETAILS_REQUIRED", status_code=409)
            order.status = "delivered"
            order.delivered_at = delivered_at
            order.auto_complete_warning_12h_at = warning_12h_at
            order.auto_complete_warning_23h_at = warning_23h_at
            order.auto_complete_at = auto_complete_at
            order.updated_at = utc_now()
            self.add_state_event(  # type: ignore[attr-defined]
                order_id=order.id,
                from_status="payment_confirmed",
                to_status="delivered",
                event_type="order_delivered",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                reason=reason,
                request_id=request_id,
                metadata_json=event_metadata,
            )
            if self._audit is not None:  # type: ignore[attr-defined]
                self._audit.write(  # type: ignore[attr-defined]
                    event_type="order_delivered",
                    actor_user_id=actor_user_id,
                    actor_role=actor_role,
                    resource_type="order",
                    resource_id=order.id,
                    request_id=request_id,
                    metadata_json=audit_metadata,
                )
            return order

    def confirm_received_atomically(
        self,
        *,
        order_id: str,
        remitter_user_id: str,
        completed_at: datetime,
        request_id: str,
        event_metadata: dict[str, Any],
        audit_metadata: dict[str, Any],
    ) -> OrderRecord:
        with self._lock:  # type: ignore[attr-defined]
            order = self.orders.get(order_id)  # type: ignore[attr-defined]
            if order is None or order.remitter_user_id != remitter_user_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if order.status != "delivered":
                raise ApiError("ORDER_RECEIPT_CONFIRMATION_NOT_ALLOWED", status_code=409)
            disputes = getattr(self, "_disputes", None)
            if disputes is not None and disputes.get_open_for_order(order.id) is not None:
                raise ApiError("ORDER_COMPLETION_BLOCKED_BY_DISPUTE", status_code=409)
            if self._capacity is None or not self._capacity.consume(  # type: ignore[attr-defined]
                order_id=order.id,
                reason="manual_confirmed",
            ):
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            order.status = "completed"
            order.completion_reason = "manual_confirmed"
            order.completed_at = completed_at
            order.updated_at = utc_now()
            self.add_state_event(  # type: ignore[attr-defined]
                order_id=order.id,
                from_status="delivered",
                to_status="completed",
                event_type="order_completed",
                actor_user_id=remitter_user_id,
                actor_role="remitter",
                reason="manual_confirmed",
                request_id=request_id,
                metadata_json=event_metadata,
            )
            if self._audit is not None:  # type: ignore[attr-defined]
                self._audit.write(  # type: ignore[attr-defined]
                    event_type="order_completed",
                    actor_user_id=remitter_user_id,
                    actor_role="remitter",
                    resource_type="order",
                    resource_id=order.id,
                    request_id=request_id,
                    metadata_json=audit_metadata,
                )
                self._audit.write(  # type: ignore[attr-defined]
                    event_type="business_capacity_consumed",
                    actor_user_id=remitter_user_id,
                    actor_role="remitter",
                    resource_type="order",
                    resource_id=order.id,
                    request_id=request_id,
                    metadata_json={"reason": "manual_confirmed"},
                )
            return order

    def update_order_if_status(
        self,
        order_id: str,
        *,
        expected_status: str,
        **fields: Any,
    ) -> OrderRecord | None:
        with self._lock:  # type: ignore[attr-defined]
            order = self.orders.get(order_id)  # type: ignore[attr-defined]
            if order is None or order.status != expected_status:
                return None
            for key, value in fields.items():
                setattr(order, key, value)
            order.updated_at = utc_now()
            return order
