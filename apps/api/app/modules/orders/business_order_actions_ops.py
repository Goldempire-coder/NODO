from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.core.errors import ApiError
from app.modules.orders.business_order_action_builder import (
    delivered_audit_event,
    delivered_response,
    delivered_state_metadata,
    payment_rejected_audit_event,
    payment_rejected_response,
    payment_rejected_state_metadata,
)
from app.modules.orders.helpers import require_uuid
from app.modules.orders.order_copy import ORDER_DISCLAIMER
from app.modules.orders.schemas import OrderActionRequest
from app.modules.orders.state_machine import now_utc, require_business_delivery_allowed, require_business_payment_rejection_allowed
from app.modules.users.models import UserRecord


class OrderBusinessActionsMixin:
    def reject_business_payment_report(self, *, user: UserRecord, order_id: str, payload: OrderActionRequest | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        business = self._approved_business_for_owner(user)  # type: ignore[attr-defined]
        self._rate_limit("business_reject_payment", user)  # type: ignore[attr-defined]
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        reason = (payload.reason if payload else None) or ""
        if not reason.strip():
            raise ApiError("ADMIN_REASON_REQUIRED", status_code=400)
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND") or order_id

        def compute() -> dict[str, Any]:
            order = self._repository.get_by_id_for_business(order_id=order_id, business_id=business.id)  # type: ignore[attr-defined]
            if order is None:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            require_business_payment_rejection_allowed(order)
            report = self._repository.get_submitted_payment_report_for_order(order.id)  # type: ignore[attr-defined]
            if report is None:
                raise ApiError("PAYMENT_REPORT_NOT_FOUND", status_code=404)
            updated_report = self._repository.update_payment_report(report, status="rejected")  # type: ignore[attr-defined]
            updated = self._repository.update_order(order, status="payment_rejected")  # type: ignore[attr-defined]
            self._repository.add_state_event(  # type: ignore[attr-defined]
                order_id=order.id,
                from_status="payment_reported",
                to_status="payment_rejected",
                event_type="payment_report_rejected",
                actor_user_id=user.id,
                actor_role=user.role,
                reason=reason,
                request_id=request_id,
                metadata_json=payment_rejected_state_metadata(report=report, idempotency_key=idempotency_key),
            )
            self._audit.write(**payment_rejected_audit_event(user=user, order=order, report=report, reason=reason, request_id=request_id))  # type: ignore[attr-defined]
            self._notifications.payment_rejected_client(order=updated, request_id=request_id)  # type: ignore[attr-defined]
            return payment_rejected_response(order=updated, report=updated_report, disclaimer=ORDER_DISCLAIMER)

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"orders:business_reject:{user.id}:{order_id}:{idempotency_key}",
            payload={"order_id": order_id, "reason": reason},
            compute=compute,
        )

    def mark_business_delivered(self, *, user: UserRecord, order_id: str, payload: OrderActionRequest | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        business = self._approved_business_for_owner(user)  # type: ignore[attr-defined]
        self._rate_limit("business_mark_delivered", user)  # type: ignore[attr-defined]
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND") or order_id

        def compute() -> dict[str, Any]:
            order = self._repository.get_by_id_for_business(order_id=order_id, business_id=business.id)  # type: ignore[attr-defined]
            if order is None:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            require_business_delivery_allowed(order)
            now = now_utc()
            updated = self._repository.update_order(  # type: ignore[attr-defined]
                order,
                status="delivered",
                delivered_at=now,
                auto_complete_warning_12h_at=now + timedelta(hours=12),
                auto_complete_warning_23h_at=now + timedelta(hours=23),
                auto_complete_at=now + timedelta(hours=24),
            )
            reason = payload.reason if payload else None
            self._repository.add_state_event(  # type: ignore[attr-defined]
                order_id=order.id,
                from_status="payment_confirmed",
                to_status="delivered",
                event_type="order_delivered",
                actor_user_id=user.id,
                actor_role=user.role,
                reason=reason,
                request_id=request_id,
                metadata_json=delivered_state_metadata(idempotency_key=idempotency_key),
            )
            self._audit.write(**delivered_audit_event(user=user, order=order, reason=reason, request_id=request_id))  # type: ignore[attr-defined]
            self._notifications.order_delivered_client(order=updated, request_id=request_id)  # type: ignore[attr-defined]
            return delivered_response(order=updated, disclaimer=ORDER_DISCLAIMER)

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"orders:business_deliver:{user.id}:{order_id}:{idempotency_key}",
            payload={"order_id": order_id, "reason": payload.reason if payload else None},
            compute=compute,
        )
