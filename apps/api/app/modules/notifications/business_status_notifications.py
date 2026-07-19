from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.modules.businesses.models import BusinessRecord
from app.modules.jobs.models import mask_metadata
from app.modules.notifications.notification_types import BUSINESS_STATUS_NOTIFICATION_TYPES

logger = get_logger(__name__)

BUSINESS_STATUS_MESSAGES = {
    "business_suspended_owner": "Tu negocio fue suspendido temporalmente. No aparecera en NODO mientras revisamos el caso.",
    "business_reactivated_owner": "Tu negocio fue reactivado. Ya puedes operar en NODO.",
    "business_blocked_owner": "Tu negocio fue bloqueado. No podras operar en NODO. Contacta soporte si crees que es un error.",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BusinessStatusNotificationService:
    def __init__(
        self,
        *,
        settings: Settings,
        job_repository,
        correlation_id: str | None = None,
        operation_id: str | None = None,
    ) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._jobs = job_repository
        self._correlation_id = correlation_id
        self._operation_id = operation_id

    def business_status_changed(
        self,
        *,
        business: BusinessRecord,
        notification_type: str,
        previous_status: str,
        request_id: str,
        correlation_id: str | None = None,
        operation_id: str | None = None,
    ) -> None:
        if notification_type not in BUSINESS_STATUS_NOTIFICATION_TYPES:
            raise ValueError(f"unsupported business status notification type: {notification_type}")
        if not business.owner_user_id:
            self._log_enqueue_skipped(notification_type, business, "OWNER_REQUIRED", request_id)
            return

        action_url = self._business_home_url()
        metadata = mask_metadata(
            {
                "channel": "telegram",
                "delivery_state": "pending",
                "event": notification_type,
                "target_surface": "business_mini_app",
                "business_status": business.verification_status,
                "previous_business_status": previous_status,
                "message_text": BUSINESS_STATUS_MESSAGES[notification_type],
                "action_text": "Abrir NODO Negocio",
                "action_url": action_url,
                "request_id": request_id,
                "correlation_id": correlation_id or self._correlation_id,
                "operation_id": operation_id or self._operation_id,
            }
        )
        try:
            notification, created = self._jobs.enqueue_notification(
                notification_type=notification_type,
                recipient_user_id=business.owner_user_id,
                recipient_role=None,
                order_id=None,
                business_id=business.id,
                dispute_id=None,
                scheduled_for=_now(),
                dedupe_key=(
                    f"business:{business.id}:event:{notification_type}:"
                    f"{previous_status}->{business.verification_status}:request:{request_id}:recipient:{business.owner_user_id}"
                ),
                metadata_json=metadata,
            )
        except Exception as exc:
            logger.warning(
                "business_status_notification_enqueue_failed",
                extra={
                    "event": "business_status_notification_enqueue_failed",
                    "notification_type": notification_type,
                    "business_id": business.id,
                    "recipient": business.owner_user_id,
                    "request_id": request_id,
                    "error_code": getattr(exc, "code", "NOTIFICATION_ENQUEUE_FAILED"),
                },
            )
            return
        logger.info(
            "business_status_notification_enqueued",
            extra={
                "event": "business_status_notification_enqueued",
                "notification_job_id": notification.id,
                "notification_type": notification_type,
                "business_id": business.id,
                "recipient": business.owner_user_id,
                "notification_created": created,
                "request_id": request_id,
            },
        )

    def _business_home_url(self) -> str:
        base_url = self._settings.telegram_web_app_url.rstrip("/")
        return f"{base_url}/business/"

    def _log_enqueue_skipped(self, notification_type: str, business: BusinessRecord, error_code: str, request_id: str) -> None:
        logger.warning(
            "business_status_notification_enqueue_skipped",
            extra={
                "event": "business_status_notification_enqueue_skipped",
                "notification_type": notification_type,
                "business_id": business.id,
                "error_code": error_code,
                "request_id": request_id,
            },
        )


class NoopBusinessStatusNotificationService:
    def business_status_changed(self, **_: Any) -> None:
        return
