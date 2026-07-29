from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.modules.jobs.models import mask_metadata
from app.modules.notifications.notification_types import SUPPORT_NOTIFICATION_TYPES
from app.modules.support.models import SupportTicketRecord

logger = get_logger(__name__)

SUPPORT_STATUS_MESSAGES = {
    "support_ticket_resolved_participant": "Soporte NODO resolvio tu ticket. Puedes consultar el historial en Archivados.",
    "support_ticket_closed_participant": "Tu ticket de Soporte NODO fue cerrado. El historial permanece disponible en Archivados.",
}
SUPPORT_MESSAGE_TEXT = "Soporte NODO respondio tu ticket. Abre la conversacion para revisar la respuesta."


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SupportNotificationService:
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

    def ticket_status_changed(
        self,
        *,
        ticket: SupportTicketRecord,
        notification_type: str,
        request_id: str,
    ) -> None:
        if notification_type not in SUPPORT_NOTIFICATION_TYPES:
            raise ValueError(f"unsupported support notification type: {notification_type}")
        target_surface = self._target_surface(ticket)
        metadata = mask_metadata(
            {
                "channel": "telegram",
                "delivery_state": "pending",
                "event": notification_type,
                "target_surface": target_surface,
                "support_ticket_id": ticket.id,
                "support_ticket_status": ticket.status,
                "message_text": SUPPORT_STATUS_MESSAGES[notification_type],
                "action_text": "Abrir Soporte NODO",
                "action_url": self._surface_url(target_surface, ticket.id),
                "request_id": request_id,
                "correlation_id": self._correlation_id,
                "operation_id": self._operation_id,
            }
        )
        try:
            notification, created = self._jobs.enqueue_notification(
                notification_type=notification_type,
                recipient_user_id=ticket.requester_user_id,
                recipient_role=None,
                order_id=None,
                business_id=ticket.business_id,
                dispute_id=None,
                scheduled_for=_now(),
                dedupe_key=(
                    f"support_ticket:{ticket.id}:event:{notification_type}:"
                    f"recipient:{ticket.requester_user_id}"
                ),
                metadata_json=metadata,
            )
        except Exception as exc:
            logger.warning(
                "support_participant_notification_enqueue_failed",
                extra={
                    "event": "support_participant_notification_enqueue_failed",
                    "notification_type": notification_type,
                    "ticket_id": ticket.id,
                    "recipient": ticket.requester_user_id,
                    "request_id": request_id,
                    "error_code": getattr(exc, "code", type(exc).__name__),
                },
            )
            return
        logger.info(
            "support_participant_notification_enqueued",
            extra={
                "event": "support_participant_notification_enqueued",
                "notification_job_id": notification.id,
                "notification_type": notification_type,
                "ticket_id": ticket.id,
                "recipient": ticket.requester_user_id,
                "notification_created": created,
                "request_id": request_id,
            },
        )

    def message_created_participant(
        self,
        *,
        ticket: SupportTicketRecord,
        message,
        request_id: str,
    ) -> None:  # type: ignore[no-untyped-def]
        notification_type = "support_message_created_participant"
        if notification_type not in SUPPORT_NOTIFICATION_TYPES:
            raise ValueError(f"unsupported support notification type: {notification_type}")
        target_surface = self._target_surface(ticket)
        metadata = mask_metadata(
            {
                "channel": "telegram",
                "delivery_state": "pending",
                "event": notification_type,
                "target_surface": target_surface,
                "support_ticket_id": ticket.id,
                "support_ticket_status": ticket.status,
                "message_text": SUPPORT_MESSAGE_TEXT,
                "action_text": "Abrir Soporte NODO",
                "action_url": self._surface_url(target_surface, ticket.id),
                "request_id": request_id,
                "correlation_id": self._correlation_id,
                "operation_id": self._operation_id,
            }
        )
        try:
            notification, created = self._jobs.enqueue_notification(
                notification_type=notification_type,
                recipient_user_id=ticket.requester_user_id,
                recipient_role=None,
                order_id=ticket.order_id,
                business_id=ticket.business_id,
                dispute_id=ticket.dispute_id,
                scheduled_for=_now(),
                dedupe_key=(
                    f"support_ticket:{ticket.id}:message:{message.id}:event:{notification_type}:"
                    f"recipient:{ticket.requester_user_id}"
                ),
                metadata_json=metadata,
            )
        except Exception as exc:
            logger.warning(
                "support_participant_message_notification_enqueue_failed",
                extra={
                    "event": "support_participant_message_notification_enqueue_failed",
                    "notification_type": notification_type,
                    "ticket_id": ticket.id,
                    "message_id": message.id,
                    "recipient": ticket.requester_user_id,
                    "request_id": request_id,
                    "error_code": getattr(exc, "code", type(exc).__name__),
                },
            )
            return
        logger.info(
            "support_participant_message_notification_enqueued",
            extra={
                "event": "support_participant_message_notification_enqueued",
                "notification_job_id": notification.id,
                "notification_type": notification_type,
                "ticket_id": ticket.id,
                "message_id": message.id,
                "recipient": ticket.requester_user_id,
                "notification_created": created,
                "request_id": request_id,
            },
        )

    @staticmethod
    def _target_surface(ticket: SupportTicketRecord) -> str:
        if ticket.requester_surface == "business_mini_app" or ticket.requester_role == "business_owner":
            return "business_mini_app"
        return "client_mini_app"

    def _surface_url(self, target_surface: str, ticket_id: str) -> str:
        base_url = self._settings.telegram_web_app_url.rstrip("/")
        if target_surface == "business_mini_app":
            return f"{base_url}/business/?view=business-support&ticket_id={ticket_id}"
        return f"{base_url}/?view=support&ticket_id={ticket_id}"


class NoopSupportNotificationService:
    def message_created_participant(self, **_: Any) -> None:
        return

    def ticket_status_changed(self, **_: Any) -> None:
        return
