from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.core.errors import ApiError
from app.modules.orders.business_order_action_builder import (
    delivered_audit_event,
    delivered_response,
    delivered_state_metadata,
)
from app.modules.orders.helpers import require_uuid
from app.modules.orders.order_copy import ORDER_DISCLAIMER
from app.modules.orders.schemas import OrderActionRequest
from app.modules.orders.serializers import business_order_payload
from app.modules.orders.state_machine import now_utc
from app.modules.users.models import UserRecord


class OrderBusinessActionsMixin:
    def business_cannot_attend(
        self,
        *,
        user: UserRecord,
        order_id: str,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        business = self._approved_business_for_owner(user)  # type: ignore[attr-defined]
        self._rate_limit("business_cannot_attend", user)  # type: ignore[attr-defined]
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND") or order_id

        def compute() -> dict[str, Any]:
            order = self._repository.get_by_id_for_business(  # type: ignore[attr-defined]
                order_id=order_id,
                business_id=business.id,
            )
            if order is None:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            result = self._repository.cancel_waiting_payment_atomically(  # type: ignore[attr-defined]
                order_id=order.id,
                expected_remitter_user_id=None,
                expected_business_id=business.id,
                transition_at=now_utc(),
                require_expired=False,
                enforce_payment_not_sent_confirmation=False,
                payment_not_sent_confirmed=False,
                cancel_reason="business_unavailable",
                event_type="order_cancelled_business_unavailable",
                actor_user_id=user.id,
                actor_role=user.role,
                event_reason="business_unavailable",
                request_id=request_id,
                event_metadata={"cancel_reason": "business_unavailable"},
                audit_event_type="order_cancelled_business_unavailable",
                audit_metadata={"reason": "business_unavailable"},
            )
            if (
                not self._repository.moves_ad_on_atomic_cancel  # type: ignore[attr-defined]
                or result.ad_requires_expiration
            ):
                ad = self._ads.get_ad(order.ad_id)  # type: ignore[attr-defined]
                if ad is not None:
                    self._return_or_expire_ad(  # type: ignore[attr-defined]
                        ad,
                        actor=user,
                        request_id=request_id,
                        related_order_id=order.id,
                    )
            else:
                self._clear_marketplace_cache()  # type: ignore[attr-defined]
            self._notifications.order_cancelled_business_unavailable_client(  # type: ignore[attr-defined]
                order=result.order,
                request_id=request_id,
            )
            return {
                "order": business_order_payload(result.order),
                "disclaimer": ORDER_DISCLAIMER,
            }

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"orders:business_cannot_attend:{user.id}:{order_id}:{idempotency_key}",
            payload={"order_id": order_id, "action": "business_unavailable"},
            compute=compute,
        )

    def reject_business_payment_report(self, *, user: UserRecord, order_id: str, payload: OrderActionRequest | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        business = self._approved_business_for_owner(user)  # type: ignore[attr-defined]
        self._rate_limit("business_reject_payment", user)  # type: ignore[attr-defined]
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND") or order_id
        order = self._repository.get_by_id_for_business(order_id=order_id, business_id=business.id)  # type: ignore[attr-defined]
        if order is None:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        raise ApiError("PAYMENT_REJECTION_NOT_ALLOWED", status_code=409)

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
            now = now_utc()
            reason = payload.reason if payload else None
            audit_event = delivered_audit_event(
                user=user,
                order=order,
                reason=reason,
                request_id=request_id,
            )
            updated = self._repository.mark_delivered_atomically(  # type: ignore[attr-defined]
                order_id=order.id,
                business_id=business.id,
                actor_user_id=user.id,
                actor_role=user.role,
                delivered_at=now,
                warning_12h_at=now + timedelta(hours=12),
                warning_23h_at=now + timedelta(hours=23),
                auto_complete_at=now + timedelta(hours=24),
                reason=reason,
                request_id=request_id,
                event_metadata=delivered_state_metadata(idempotency_key=idempotency_key),
                audit_metadata=audit_event["metadata_json"],
            )
            self._notifications.order_delivered_client(order=updated, request_id=request_id)  # type: ignore[attr-defined]
            return delivered_response(order=updated, disclaimer=ORDER_DISCLAIMER)

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"orders:business_deliver:{user.id}:{order_id}:{idempotency_key}",
            payload={"order_id": order_id, "reason": payload.reason if payload else None},
            compute=compute,
        )
