from __future__ import annotations

from typing import Any, Callable

from app.core.errors import ApiError
from app.modules.ads.models import AdRecord
from app.modules.notifications.order_notifications import NoopOrderNotificationService
from app.modules.orders.helpers import require_uuid
from app.modules.orders.order_copy import ORDER_DISCLAIMER
from app.modules.orders.policy import require_order_owner, require_remitter
from app.modules.orders.schemas import OrderActionRequest, OrderCancelRequest
from app.modules.orders.serializers import public_order_payload
from app.modules.orders.state_machine import (
    extended_deadline,
    now_utc,
    require_cancel_allowed,
    require_extend_allowed,
)
from app.modules.users.models import UserRecord

class OrderRemitterOps:
    def __init__(
        self,
        *,
        repository,
        ad_repository,
        audit_writer,
        idempotency_store,
        rate_limit: Callable[[str, UserRecord], None],
        materialize_order_expiration: Callable[..., Any],
        return_or_expire_ad: Callable[..., None],
        rating_ops,
        notification_service=None,
    ) -> None:  # type: ignore[no-untyped-def]
        self._repository = repository
        self._ads = ad_repository
        self._audit = audit_writer
        self._idempotency = idempotency_store
        self._rate_limit = rate_limit
        self._materialize_order_expiration = materialize_order_expiration
        self._return_or_expire_ad = return_or_expire_ad
        self._rating_ops = rating_ops
        self._notifications = notification_service or NoopOrderNotificationService()

    def detail(self, *, user: UserRecord, order_id: str, request_id: str) -> dict[str, Any]:
        require_remitter(user)
        self._rate_limit("detail", user)
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND") or order_id
        order = self._repository.get_by_id(order_id)
        if order is None:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        require_order_owner(user, order)
        order = self._materialize_order_expiration(order, actor=user, request_id=request_id)
        payload = public_order_payload(order)
        payload["rating"] = self._rating_ops.state(order_id=order.id, user_id=user.id)
        return {"order": payload, "disclaimer": ORDER_DISCLAIMER}

    def mine(self, *, user: UserRecord, status: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        require_remitter(user)
        self._rate_limit("mine", user)
        if status not in {None, "waiting_payment", "cancelled"}:
            raise ApiError("VALIDATION_ERROR", status_code=422)
        items, next_cursor = self._repository.list_for_remitter(remitter_user_id=user.id, status=status, cursor=cursor, limit=limit)
        materialized = [self._materialize_order_expiration(order, actor=user, request_id=request_id) for order in items]
        return {"items": [public_order_payload(order, list_view=True) for order in materialized], "next_cursor": next_cursor, "disclaimer": ORDER_DISCLAIMER}

    def extend(self, *, user: UserRecord, order_id: str, payload: OrderActionRequest | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        require_remitter(user)
        self._rate_limit("extend", user)
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND") or order_id

        def compute() -> dict[str, Any]:
            order = self._repository.get_by_id(order_id)
            if order is None:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            require_order_owner(user, order)
            order = self._materialize_order_expiration(order, actor=user, request_id=request_id)
            require_extend_allowed(order)
            new_deadline = extended_deadline(order)
            updated = self._repository.update_order(
                order,
                extension_used=True,
                payment_report_extension_used_at=now_utc(),
                payment_report_deadline_at=new_deadline,
                expires_at=new_deadline,
            )
            reason = payload.reason if payload else None
            self._repository.add_state_event(
                order_id=order.id,
                from_status="waiting_payment",
                to_status="waiting_payment",
                event_type="waiting_payment_extended",
                actor_user_id=user.id,
                actor_role=user.role,
                reason=reason,
                request_id=request_id,
                metadata_json={"minutes_added": 15},
            )
            self._audit.write(event_type="payment_deadline_extended", actor_user_id=user.id, actor_role=user.role, resource_type="order", resource_id=order.id, request_id=request_id, metadata_json={"reason": reason})
            return {"order": public_order_payload(updated), "disclaimer": ORDER_DISCLAIMER}

        return self._idempotency.replay_or_store(f"orders:extend:{user.id}:{order_id}:{idempotency_key}", payload={"order_id": order_id, "reason": payload.reason if payload else None}, compute=compute)

    def cancel(self, *, user: UserRecord, order_id: str, payload: OrderCancelRequest | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        require_remitter(user)
        self._rate_limit("cancel", user)
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND") or order_id

        def compute() -> dict[str, Any]:
            order = self._repository.get_by_id(order_id)
            if order is None:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            require_order_owner(user, order)
            order = self._materialize_order_expiration(order, actor=user, request_id=request_id)
            require_cancel_allowed(order)
            if order.payment_data_revealed_at is not None and not (
                payload and payload.payment_not_sent_confirmed
            ):
                raise ApiError(
                    "ORDER_PAYMENT_NOT_SENT_CONFIRMATION_REQUIRED",
                    status_code=409,
                )
            updated = self._repository.update_order(
                order,
                status="cancelled",
                cancel_reason="remitter_cancelled_before_payment",
                capacity_event_context={
                    "actor_user_id": user.id,
                    "actor_role": user.role,
                    "request_id": request_id,
                    "reason": "remitter_cancelled_before_payment",
                },
            )
            ad: AdRecord | None = self._ads.get_ad(order.ad_id)
            if ad is not None:
                self._return_or_expire_ad(ad, actor=user, request_id=request_id, related_order_id=order.id)
            reason = payload.reason if payload else "choose_another_business"
            self._repository.add_state_event(
                order_id=order.id,
                from_status="waiting_payment",
                to_status="cancelled",
                event_type="order_cancelled_by_remitter",
                actor_user_id=user.id,
                actor_role=user.role,
                reason=reason,
                request_id=request_id,
                metadata_json={"cancel_reason": "remitter_cancelled_before_payment"},
            )
            self._audit.write(event_type="order_cancelled", actor_user_id=user.id, actor_role=user.role, resource_type="order", resource_id=order.id, request_id=request_id, metadata_json={"reason": "remitter_cancelled_before_payment"})
            self._notifications.order_cancelled_before_payment_business(
                order=updated,
                request_id=request_id,
            )
            return {"order": public_order_payload(updated), "disclaimer": ORDER_DISCLAIMER}

        return self._idempotency.replay_or_store(
            f"orders:cancel:{user.id}:{order_id}:{idempotency_key}",
            payload={
                "order_id": order_id,
                "reason": payload.reason if payload else "choose_another_business",
                "payment_not_sent_confirmed": (
                    payload.payment_not_sent_confirmed if payload else False
                ),
            },
            compute=compute,
        )
