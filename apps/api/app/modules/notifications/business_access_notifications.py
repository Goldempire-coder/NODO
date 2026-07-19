from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.modules.businesses.models import BusinessAccessLinkRecord, BusinessRecord
from app.modules.jobs.models import mask_metadata
from app.modules.notifications.notification_types import BUSINESS_ACCESS_NOTIFICATION_TYPES
from app.modules.users.models import UserRecord

logger = get_logger(__name__)

BUSINESS_ACCESS_STATUS_TO_NOTIFICATION = {
    "active": "business_access_reactivated_owner",
    "suspended": "business_access_suspended_owner",
    "blocked": "business_access_blocked_owner",
    "revoked": "business_access_revoked_owner",
}

BUSINESS_ACCESS_MESSAGES = {
    "business_access_suspended_owner": "Tu acceso a NODO Negocio fue suspendido temporalmente. No podras operar ese negocio mientras revisamos el caso.",
    "business_access_reactivated_owner": "Tu acceso a NODO Negocio fue reactivado. Ya puedes volver a operar.",
    "business_access_blocked_owner": "Tu acceso a NODO Negocio fue bloqueado. Contacta soporte si crees que es un error.",
    "business_access_revoked_owner": "Tu acceso a NODO Negocio fue retirado. Este Telegram ya no podra operar ese negocio.",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BusinessAccessNotificationService:
    def __init__(self, *, settings: Settings, job_repository) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._jobs = job_repository

    def access_link_status_changed(
        self,
        *,
        business: BusinessRecord,
        link: BusinessAccessLinkRecord,
        target: UserRecord | None,
        previous_status: str,
        request_id: str,
    ) -> None:
        notification_type = BUSINESS_ACCESS_STATUS_TO_NOTIFICATION.get(link.status)
        if notification_type not in BUSINESS_ACCESS_NOTIFICATION_TYPES:
            self._log_enqueue_skipped("unsupported", business, link, "NOTIFICATION_TYPE_UNSUPPORTED", request_id)
            return
        if target is None or not target.telegram_id:
            self._log_enqueue_skipped(notification_type, business, link, "TELEGRAM_ID_REQUIRED", request_id)
            return

        metadata = mask_metadata(
            {
                "channel": "telegram",
                "delivery_state": "pending",
                "event": notification_type,
                "target_surface": "business_mini_app",
                "access_link_status": link.status,
                "previous_access_link_status": previous_status,
                "message_text": BUSINESS_ACCESS_MESSAGES[notification_type],
                "action_text": "Abrir NODO Negocio",
                "action_url": self._business_home_url(),
                "request_id": request_id,
            }
        )
        try:
            notification, created = self._jobs.enqueue_notification(
                notification_type=notification_type,
                recipient_user_id=target.id,
                recipient_role=None,
                order_id=None,
                business_id=business.id,
                dispute_id=None,
                scheduled_for=_now(),
                dedupe_key=(
                    f"business_access:{link.id}:event:{notification_type}:"
                    f"{previous_status}->{link.status}:request:{request_id}:recipient:{target.id}"
                ),
                metadata_json=metadata,
            )
        except Exception as exc:
            logger.warning(
                "business_access_notification_enqueue_failed",
                extra={
                    "event": "business_access_notification_enqueue_failed",
                    "notification_type": notification_type,
                    "business_id": business.id,
                    "access_link_id": link.id,
                    "recipient": link.user_id,
                    "request_id": request_id,
                    "error_code": getattr(exc, "code", "NOTIFICATION_ENQUEUE_FAILED"),
                },
            )
            return
        logger.info(
            "business_access_notification_enqueued",
            extra={
                "event": "business_access_notification_enqueued",
                "notification_job_id": notification.id,
                "notification_type": notification_type,
                "business_id": business.id,
                "access_link_id": link.id,
                "recipient": target.id,
                "notification_created": created,
                "request_id": request_id,
            },
        )

    def _business_home_url(self) -> str:
        return f"{self._settings.telegram_web_app_url.rstrip('/')}/business/"

    def _log_enqueue_skipped(self, notification_type: str, business: BusinessRecord, link: BusinessAccessLinkRecord, error_code: str, request_id: str) -> None:
        logger.warning(
            "business_access_notification_enqueue_skipped",
            extra={
                "event": "business_access_notification_enqueue_skipped",
                "notification_type": notification_type,
                "business_id": business.id,
                "access_link_id": link.id,
                "recipient": link.user_id,
                "error_code": error_code,
                "request_id": request_id,
            },
        )


class NoopBusinessAccessNotificationService:
    def access_link_status_changed(self, **_: Any) -> None:
        return
