from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.modules.jobs.models import mask_metadata
from app.modules.notifications.notification_types import USER_STATUS_NOTIFICATION_TYPES
from app.modules.users.models import UserRecord

logger = get_logger(__name__)

USER_STATUS_MESSAGES = {
    "user_suspended_account": "Tu cuenta fue suspendida temporalmente. No podras operar en NODO mientras revisamos el caso.",
    "user_reactivated_account": "Tu cuenta fue reactivada. Ya puedes operar en NODO.",
    "user_blocked_account": "Tu cuenta fue bloqueada. No podras operar en NODO. Contacta soporte si crees que es un error.",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UserStatusNotificationService:
    def __init__(self, *, settings: Settings, job_repository) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._jobs = job_repository

    def user_status_changed(
        self,
        *,
        target: UserRecord,
        notification_type: str,
        previous_status: str,
        business_id: str | None,
        request_id: str,
    ) -> None:
        if notification_type not in USER_STATUS_NOTIFICATION_TYPES:
            raise ValueError(f"unsupported user status notification type: {notification_type}")
        if not target.telegram_id:
            self._log_enqueue_skipped(notification_type, target, "TELEGRAM_ID_REQUIRED", request_id)
            return

        is_business_owner = target.role == "business_owner"
        target_surface = "business_mini_app" if is_business_owner else "client_mini_app"
        metadata = mask_metadata(
            {
                "channel": "telegram",
                "delivery_state": "pending",
                "event": notification_type,
                "target_surface": target_surface,
                "user_status": target.status,
                "previous_user_status": previous_status,
                "message_text": USER_STATUS_MESSAGES[notification_type],
                "action_text": "Abrir NODO Negocio" if is_business_owner else "Abrir NODO",
                "action_url": self._business_home_url() if is_business_owner else self._client_home_url(),
                "request_id": request_id,
            }
        )
        try:
            notification, created = self._jobs.enqueue_notification(
                notification_type=notification_type,
                recipient_user_id=target.id,
                recipient_role=None,
                order_id=None,
                business_id=business_id,
                dispute_id=None,
                scheduled_for=_now(),
                dedupe_key=(
                    f"user:{target.id}:event:{notification_type}:"
                    f"{previous_status}->{target.status}:request:{request_id}:recipient:{target.id}"
                ),
                metadata_json=metadata,
            )
        except Exception as exc:
            logger.warning(
                "user_status_notification_enqueue_failed",
                extra={
                    "event": "user_status_notification_enqueue_failed",
                    "notification_type": notification_type,
                    "recipient": target.id,
                    "business_id": business_id,
                    "request_id": request_id,
                    "error_code": getattr(exc, "code", "NOTIFICATION_ENQUEUE_FAILED"),
                },
            )
            return
        logger.info(
            "user_status_notification_enqueued",
            extra={
                "event": "user_status_notification_enqueued",
                "notification_job_id": notification.id,
                "notification_type": notification_type,
                "recipient": target.id,
                "business_id": business_id,
                "notification_created": created,
                "request_id": request_id,
            },
        )

    def _business_home_url(self) -> str:
        return f"{self._settings.telegram_web_app_url.rstrip('/')}/business/"

    def _client_home_url(self) -> str:
        return f"{self._settings.telegram_web_app_url.rstrip('/')}/"

    def _log_enqueue_skipped(self, notification_type: str, target: UserRecord, error_code: str, request_id: str) -> None:
        logger.warning(
            "user_status_notification_enqueue_skipped",
            extra={
                "event": "user_status_notification_enqueue_skipped",
                "notification_type": notification_type,
                "recipient": target.id,
                "error_code": error_code,
                "request_id": request_id,
            },
        )


class NoopUserStatusNotificationService:
    def user_status_changed(self, **_: Any) -> None:
        return
