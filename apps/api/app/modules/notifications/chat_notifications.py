from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.modules.jobs.models import mask_metadata
from app.modules.notifications.notification_types import CHAT_NOTIFICATION_TYPES
from app.modules.orders.models import OrderRecord


logger = get_logger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ChatNotificationService:
    def __init__(
        self,
        *,
        settings: Settings,
        job_repository,
        business_repository,
        correlation_id: str | None = None,
        operation_id: str | None = None,
    ) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._jobs = job_repository
        self._businesses = business_repository
        self._correlation_id = correlation_id
        self._operation_id = operation_id

    def message_created(
        self,
        *,
        order: OrderRecord,
        message,
        sender_role: str,
        request_id: str,
    ) -> None:  # type: ignore[no-untyped-def]
        if sender_role in {"remitter", "client"}:
            business = self._businesses.get_business(order.business_id)
            if business is None:
                self._log_skipped(order=order, message_id=message.id, error_code="BUSINESS_NOT_FOUND", request_id=request_id)
                return
            notification_type = "order_message_created_business"
            recipient_user_id = business.owner_user_id
            target_surface = "business_mini_app"
            action_url = self._business_chat_url(order.id)
        elif sender_role == "business_owner":
            notification_type = "order_message_created_client"
            recipient_user_id = order.remitter_user_id
            target_surface = "client_mini_app"
            action_url = self._client_chat_url(order.id)
        else:
            self._log_skipped(order=order, message_id=message.id, error_code="SENDER_NOT_NOTIFYABLE", request_id=request_id)
            return

        if notification_type not in CHAT_NOTIFICATION_TYPES:
            raise ValueError(f"unsupported chat notification type: {notification_type}")
        metadata = mask_metadata(
            {
                "channel": "telegram",
                "delivery_state": "pending",
                "event": notification_type,
                "target_surface": target_surface,
                "public_order_code": order.public_order_code,
                "message_text": (
                    f"Tienes un mensaje nuevo en la orden {order.public_order_code}. "
                    "Abre el chat para revisarlo."
                ),
                "action_text": "Abrir chat",
                "action_url": action_url,
                "request_id": request_id,
                "correlation_id": self._correlation_id,
                "operation_id": self._operation_id,
            }
        )
        try:
            notification, created = self._jobs.enqueue_notification(
                notification_type=notification_type,
                recipient_user_id=recipient_user_id,
                recipient_role=None,
                order_id=order.id,
                business_id=order.business_id,
                dispute_id=None,
                scheduled_for=_now(),
                dedupe_key=(
                    f"order:{order.id}:message:{message.id}:event:{notification_type}:"
                    f"recipient:{recipient_user_id}"
                ),
                metadata_json=metadata,
            )
        except Exception as exc:
            logger.warning(
                "order_chat_notification_enqueue_failed",
                extra={
                    "event": "order_chat_notification_enqueue_failed",
                    "notification_type": notification_type,
                    "order_id": order.id,
                    "message_id": message.id,
                    "recipient": recipient_user_id,
                    "request_id": request_id,
                    "error_code": getattr(exc, "code", type(exc).__name__),
                },
            )
            return
        logger.info(
            "order_chat_notification_enqueued",
            extra={
                "event": "order_chat_notification_enqueued",
                "notification_job_id": notification.id,
                "notification_type": notification_type,
                "order_id": order.id,
                "message_id": message.id,
                "recipient": recipient_user_id,
                "notification_created": created,
                "request_id": request_id,
            },
        )

    def _business_chat_url(self, order_id: str) -> str:
        base_url = self._settings.telegram_web_app_url.rstrip("/")
        return f"{base_url}/business/?view=business-chat&order_id={order_id}"

    def _client_chat_url(self, order_id: str) -> str:
        base_url = self._settings.telegram_web_app_url.rstrip("/")
        return f"{base_url}/?view=order-chat&order_id={order_id}"

    @staticmethod
    def _log_skipped(*, order: OrderRecord, message_id: str, error_code: str, request_id: str) -> None:
        logger.warning(
            "order_chat_notification_skipped",
            extra={
                "event": "order_chat_notification_skipped",
                "order_id": order.id,
                "message_id": message_id,
                "error_code": error_code,
                "request_id": request_id,
            },
        )


class NoopChatNotificationService:
    def message_created(self, **_: Any) -> None:
        return
