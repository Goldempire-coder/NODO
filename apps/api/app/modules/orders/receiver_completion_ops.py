from __future__ import annotations

from typing import Any, Callable

from app.core.errors import ApiError
from app.modules.notifications.order_notifications import NoopOrderNotificationService
from app.modules.orders.helpers import require_uuid
from app.modules.orders.receiver_details import (
    receiver_details_created_payload,
    receiver_details_reveal_payload,
    receiver_payload_hash,
)
from app.modules.orders.schemas import ReceiverDetailsRequest
from app.modules.orders.serializers import public_order_payload
from app.modules.orders.state_machine import now_utc
from app.modules.users.models import UserRecord


class OrderReceiverCompletionOps:
    def __init__(
        self,
        *,
        repository,
        business_repository,
        idempotency_store,
        rate_limit: Callable[[str, UserRecord], None],
        notification_service=None,
        rating_ops=None,
    ) -> None:  # type: ignore[no-untyped-def]
        self._repository = repository
        self._businesses = business_repository
        self._idempotency = idempotency_store
        self._rate_limit = rate_limit
        self._notifications = notification_service or NoopOrderNotificationService()
        self._rating_ops = rating_ops

    def share_receiver_details(
        self,
        *,
        user: UserRecord,
        order_id: str,
        payload: ReceiverDetailsRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        self._require_remitter(user)
        self._rate_limit("share_receiver_details", user)
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND") or order_id
        normalized = payload.model_dump()
        payload_hash = receiver_payload_hash(normalized)

        def compute() -> dict[str, Any]:
            record, created = self._repository.create_receiver_details_atomically(
                order_id=order_id,
                remitter_user_id=user.id,
                payload=normalized,
                payload_hash=payload_hash,
                request_id=request_id,
                audit_metadata={
                    "schema": "pago_movil_receiver_v1",
                    "result": "created",
                    "fields_present": {
                        "bank": True,
                        "phone": True,
                        "document": True,
                        "holder": True,
                    },
                },
            )
            if created:
                order = self._repository.get_by_id(order_id)
                if order is not None:
                    self._notifications.order_receiver_details_shared_business(
                        order=order,
                        request_id=request_id,
                    )
            return receiver_details_created_payload(record)

        return self._idempotency.replay_or_store(
            f"orders:receiver_details:{user.id}:{order_id}:{idempotency_key}",
            payload={"order_id": order_id, **normalized},
            compute=compute,
        )

    def reveal_receiver_details(
        self,
        *,
        user: UserRecord,
        order_id: str,
        request_id: str,
    ) -> dict[str, Any]:
        if user.status != "active" or user.role not in {"remitter", "business_owner"}:
            raise ApiError("FORBIDDEN", status_code=403)
        self._rate_limit("reveal_receiver_details", user)
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND") or order_id
        order = self._repository.get_by_id(order_id)
        if order is None:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        business = self._businesses.get_business(order.business_id)
        business_owner_user_id = business.owner_user_id if business is not None else None
        record = self._repository.reveal_receiver_details_with_audit(
            order_id=order_id,
            actor_user_id=user.id,
            actor_role=user.role,
            business_owner_user_id=business_owner_user_id,
            request_id=request_id,
            audit_metadata={
                "schema": "pago_movil_receiver_v1",
                "result": "revealed",
                "purpose": "order_fulfillment",
            },
        )
        return receiver_details_reveal_payload(record)

    def confirm_received(
        self,
        *,
        user: UserRecord,
        order_id: str,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        self._require_remitter(user)
        self._rate_limit("confirm_received", user)
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND") or order_id

        def compute() -> dict[str, Any]:
            order = self._repository.confirm_received_atomically(
                order_id=order_id,
                remitter_user_id=user.id,
                completed_at=now_utc(),
                request_id=request_id,
                event_metadata={
                    "completion_reason": "manual_confirmed",
                    "credit_consumed": False,
                },
                audit_metadata={
                    "completion_reason": "manual_confirmed",
                    "capacity_transition": "consumed",
                    "credit_consumed": False,
                },
            )
            self._notifications.order_completed_business(
                order=order,
                request_id=request_id,
            )
            response = {"order": public_order_payload(order)}
            if self._rating_ops is not None:
                response["rating"] = self._rating_ops.state(
                    order_id=order.id,
                    user_id=user.id,
                )
            return response

        return self._idempotency.replay_or_store(
            f"orders:confirm_received:{user.id}:{order_id}:{idempotency_key}",
            payload={"order_id": order_id, "action": "manual_confirmed"},
            compute=compute,
        )

    @staticmethod
    def _require_remitter(user: UserRecord) -> None:
        if user.status != "active" or user.role != "remitter":
            raise ApiError("FORBIDDEN", status_code=403)
