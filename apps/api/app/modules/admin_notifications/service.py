from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import ApiError
from app.core.logging import get_logger
from app.modules.admin.policy import require_admin_mutation, require_admin_read
from app.modules.admin_notifications.models import (
    ADMIN_NOTIFICATION_PRIORITIES,
    ADMIN_NOTIFICATION_STATUSES,
    AdminNotificationRecord,
    utc_now,
)
from app.modules.admin_notifications.redaction import safe_text, sanitize_admin_notification_metadata
from app.modules.admin_notifications.serializers import admin_notification_public
from app.modules.jobs.models import mask_metadata
from app.modules.users.models import UserRecord

logger = get_logger(__name__)

ADMIN_TELEGRAM_TARGET_SURFACE = "admin_alerts"
ADMIN_TELEGRAM_ALERT_TYPES = {
    "business_intake_submitted": "admin_alert_business_intake_submitted",
}


def _safe_uuid(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(value))
    except (TypeError, ValueError):
        return None


class AdminNotificationService:
    def __init__(
        self,
        *,
        repository,
        job_repository=None,
        user_repository=None,
        admin_telegram_alerts_enabled: bool = False,
        admin_app_url: str | None = None,
    ) -> None:  # type: ignore[no-untyped-def]
        self._repository = repository
        self._job_repository = job_repository
        self._user_repository = user_repository
        self._admin_telegram_alerts_enabled = admin_telegram_alerts_enabled
        self._admin_app_url = (admin_app_url or "").rstrip("/")

    def enqueue(
        self,
        *,
        notification_type: str,
        priority: str,
        resource_type: str,
        title: str,
        summary: str,
        dedupe_key: str,
        source_surface: str | None = None,
        resource_id: str | None = None,
        business_id: str | None = None,
        actor_user_id: str | None = None,
        action_route: str | None = None,
        metadata: dict[str, Any] | None = None,
        request_id: str = "request_id_unavailable",
    ) -> tuple[AdminNotificationRecord, bool]:
        if priority not in ADMIN_NOTIFICATION_PRIORITIES:
            raise ApiError("ADMIN_NOTIFICATION_PRIORITY_INVALID", status_code=400)
        title = safe_text(title, 120)
        summary = safe_text(summary, 280)
        if not title or not summary:
            raise ApiError("ADMIN_NOTIFICATION_INVALID", status_code=400)
        notification, created = self._repository.upsert_notification(
            notification_type=safe_text(notification_type, 80),
            priority=priority,
            status="unread",
            source_surface=safe_text(source_surface, 80) if source_surface else None,
            resource_type=safe_text(resource_type, 80),
            resource_id=_safe_uuid(resource_id),
            business_id=_safe_uuid(business_id),
            actor_user_id=_safe_uuid(actor_user_id),
            title=title,
            summary=summary,
            action_route=safe_text(action_route, 200) if action_route else None,
            dedupe_key=safe_text(dedupe_key, 220),
            metadata_json=sanitize_admin_notification_metadata(metadata),
        )
        logger.info(
            "admin_notification_enqueued",
            extra={
                "event": "admin_notification_enqueued",
                "admin_notification_id": notification.id,
                "notification_type": notification.notification_type,
                "resource_type": notification.resource_type,
                "resource_id": notification.resource_id,
                "business_id": notification.business_id,
                "priority": notification.priority,
                "notification_created": created,
                "request_id": request_id,
            },
        )
        if created:
            self._enqueue_admin_telegram_alerts(notification=notification, request_id=request_id)
        return notification, created

    def list_notifications(
        self,
        *,
        user: UserRecord,
        status: str | None,
        priority: str | None,
        cursor: str | None,
        limit: int,
        request_id: str,
    ) -> dict[str, Any]:
        require_admin_read(user)
        if status and status not in ADMIN_NOTIFICATION_STATUSES:
            raise ApiError("ADMIN_NOTIFICATION_STATUS_INVALID", status_code=400)
        if priority and priority not in ADMIN_NOTIFICATION_PRIORITIES:
            raise ApiError("ADMIN_NOTIFICATION_PRIORITY_INVALID", status_code=400)
        items, next_cursor = self._repository.list_notifications(status=status, priority=priority, cursor=cursor, limit=limit)
        return {"items": [admin_notification_public(item) for item in items], "next_cursor": next_cursor}

    def unread_count(self, *, user: UserRecord, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        return {
            "unread_count": self._repository.unread_count(),
            "support_unread_count": self._repository.unread_count_by_resource_type("support_ticket"),
        }

    def mark_read(self, *, user: UserRecord, notification_id: str, request_id: str) -> dict[str, Any]:
        require_admin_mutation(user)
        notification = self._require_notification(notification_id)
        if notification.status == "unread":
            notification = self._repository.update_notification(
                notification,
                status="read",
                read_at=utc_now(),
                read_by_user_id=user.id,
            )
        return {"notification": admin_notification_public(notification)}

    def dismiss(self, *, user: UserRecord, notification_id: str, request_id: str) -> dict[str, Any]:
        require_admin_mutation(user)
        notification = self._require_notification(notification_id)
        notification = self._repository.update_notification(
            notification,
            status="dismissed",
            dismissed_at=utc_now(),
            dismissed_by_user_id=user.id,
        )
        return {"notification": admin_notification_public(notification)}

    def resolve(self, *, user: UserRecord, notification_id: str, request_id: str) -> dict[str, Any]:
        require_admin_mutation(user)
        notification = self._require_notification(notification_id)
        notification = self._repository.update_notification(
            notification,
            status="resolved",
            resolved_at=utc_now(),
            resolved_by_user_id=user.id,
        )
        return {"notification": admin_notification_public(notification)}

    def business_intake_submitted(self, *, intake, request_id: str) -> None:  # type: ignore[no-untyped-def]
        self.enqueue(
            notification_type="business_intake_submitted",
            priority="attention",
            source_surface="business_intake_bot",
            resource_type="business_intake",
            resource_id=intake.id,
            business_id=None,
            actor_user_id=None,
            title="Solicitud de negocio enviada",
            summary=f"{safe_text(getattr(intake, 'business_name', '') or 'Negocio', 120)} envio solicitud para revision.",
            action_route=f"admin://business-intake/{intake.id}",
            dedupe_key=f"business_intake:{intake.id}:submitted",
            metadata={"status": getattr(intake, "status", None), "city": getattr(intake, "city", None)},
            request_id=request_id,
        )

    def business_document_uploaded(self, *, intake, document, request_id: str) -> None:  # type: ignore[no-untyped-def]
        self.enqueue(
            notification_type="business_document_uploaded",
            priority="info",
            source_surface="business_intake_bot",
            resource_type="business_intake_document",
            resource_id=document.id,
            title="Documento de negocio cargado",
            summary=f"Documento {safe_text(document.document_kind, 60)} recibido para solicitud de negocio.",
            action_route=f"admin://business-intake/{intake.id}",
            dedupe_key=f"business_intake:{intake.id}:document:{document.id}",
            metadata={"document_kind": document.document_kind, "mime_type": document.mime_type, "size_bytes": document.size_bytes},
            request_id=request_id,
        )

    def business_support_ticket_created(self, *, ticket, request_id: str) -> None:  # type: ignore[no-untyped-def]
        priority = {
            "low": "info",
            "normal": "attention",
            "high": "high",
            "urgent": "critical",
        }.get(ticket.priority, "attention")
        self.enqueue(
            notification_type="business_support_ticket_created",
            priority=priority,
            source_surface=ticket.requester_surface,
            resource_type="support_ticket",
            resource_id=ticket.id,
            business_id=ticket.business_id,
            actor_user_id=ticket.requester_user_id,
            title="Nuevo ticket de negocio",
            summary="Nuevo ticket de negocio requiere revision.",
            action_route=f"admin://support-ticket/{ticket.id}",
            dedupe_key=f"support_ticket:{ticket.id}:business_created",
            metadata={"scope": ticket.scope, "category": ticket.category, "status": ticket.status},
            request_id=request_id,
        )

    def business_support_message_created(self, *, ticket, message, request_id: str) -> None:  # type: ignore[no-untyped-def]
        priority = {
            "low": "info",
            "normal": "attention",
            "high": "high",
            "urgent": "critical",
        }.get(ticket.priority, "attention")
        self.enqueue(
            notification_type="business_support_message_created",
            priority=priority,
            source_surface=ticket.requester_surface,
            resource_type="support_ticket",
            resource_id=ticket.id,
            business_id=ticket.business_id,
            actor_user_id=message.sender_user_id,
            title="Nuevo mensaje de soporte",
            summary="Un negocio respondio una conversacion de soporte.",
            action_route=f"admin://support-ticket/{ticket.id}",
            dedupe_key=f"support_ticket:{ticket.id}:message:{message.id}:business",
            metadata={"scope": ticket.scope, "category": ticket.category, "status": ticket.status, "message_id": message.id},
            request_id=request_id,
        )

    def client_support_ticket_created(self, *, ticket, request_id: str) -> None:  # type: ignore[no-untyped-def]
        priority = {
            "low": "info",
            "normal": "attention",
            "high": "high",
            "urgent": "critical",
        }.get(ticket.priority, "attention")
        self.enqueue(
            notification_type="client_support_ticket_created",
            priority=priority,
            source_surface=ticket.requester_surface,
            resource_type="support_ticket",
            resource_id=ticket.id,
            business_id=ticket.business_id,
            actor_user_id=ticket.requester_user_id,
            title="Nuevo ticket de cliente",
            summary="Nuevo ticket de cliente requiere revision.",
            action_route=f"admin://support-ticket/{ticket.id}",
            dedupe_key=f"support_ticket:{ticket.id}:client_created",
            metadata={"scope": ticket.scope, "category": ticket.category, "status": ticket.status},
            request_id=request_id,
        )

    def client_support_message_created(self, *, ticket, message, request_id: str) -> None:  # type: ignore[no-untyped-def]
        priority = {
            "low": "info",
            "normal": "attention",
            "high": "high",
            "urgent": "critical",
        }.get(ticket.priority, "attention")
        self.enqueue(
            notification_type="client_support_message_created",
            priority=priority,
            source_surface=ticket.requester_surface,
            resource_type="support_ticket",
            resource_id=ticket.id,
            business_id=ticket.business_id,
            actor_user_id=message.sender_user_id,
            title="Nuevo mensaje de cliente",
            summary="Un cliente respondio una conversacion de soporte.",
            action_route=f"admin://support-ticket/{ticket.id}",
            dedupe_key=f"support_ticket:{ticket.id}:message:{message.id}:client",
            metadata={"scope": ticket.scope, "category": ticket.category, "status": ticket.status, "message_id": message.id},
            request_id=request_id,
        )

    def order_chat_off_platform_solicitation(self, *, order, message, match, request_id: str) -> None:  # type: ignore[no-untyped-def]
        priority = "high" if match.severity == "high" else "attention"
        self.enqueue(
            notification_type="order_chat_off_platform_solicitation",
            priority=priority,
            source_surface="order_chat",
            resource_type="order_chat_message",
            resource_id=message.id,
            business_id=order.business_id,
            actor_user_id=message.sender_user_id,
            title="Posible salida fuera de NODO",
            summary="Un mensaje de negocio requiere revision por posible salida fuera de NODO.",
            action_route=f"admin://order/{order.id}",
            dedupe_key=f"order:{order.id}:message:{message.id}:off_platform:{match.rule_id}",
            metadata={
                "order_id": order.id,
                "message_id": message.id,
                "rule_id": match.rule_id,
                "severity": match.severity,
                "matched_phrase": match.matched_phrase,
                "sender_role": message.sender_role,
            },
            request_id=request_id,
        )

    def credit_purchase_attention(self, *, purchase, reason: str, request_id: str, error_code: str | None = None) -> None:  # type: ignore[no-untyped-def]
        priority = "high" if purchase.status in {"failed", "verification_failed", "expired"} else "attention"
        self.enqueue(
            notification_type=f"base_usdc_credit_purchase_{reason}",
            priority=priority,
            source_surface="base_usdc_watcher",
            resource_type="credit_purchase",
            resource_id=purchase.id,
            business_id=purchase.business_id,
            title="Compra USDC requiere revision",
            summary=f"Compra {purchase.package_code} quedo en estado {purchase.status}.",
            action_route=f"admin://credit-purchase/{purchase.id}",
            dedupe_key=f"credit_purchase:{purchase.id}:{reason}:{purchase.status}",
            metadata={"status": purchase.status, "package_code": purchase.package_code, "error_code": error_code},
            request_id=request_id,
        )

    def telegram_failed_permanent(self, *, notification, error_code: str, request_id: str) -> None:  # type: ignore[no-untyped-def]
        self.enqueue(
            notification_type="telegram_notification_failed_permanent",
            priority="attention",
            source_surface="telegram_sender",
            resource_type="notification_job",
            resource_id=notification.id,
            business_id=notification.business_id,
            actor_user_id=notification.recipient_user_id,
            title="Notificacion Telegram fallida",
            summary=f"Telegram no pudo entregar {notification.notification_type}.",
            action_route=f"admin://notification-job/{notification.id}",
            dedupe_key=f"notification_job:{notification.id}:failed_permanent",
            metadata={"notification_type": notification.notification_type, "error_code": error_code, "target_surface": (notification.metadata_json or {}).get("target_surface")},
            request_id=request_id,
        )

    def _require_notification(self, notification_id: str) -> AdminNotificationRecord:
        notification = self._repository.get(_safe_uuid(notification_id) or "")
        if notification is None:
            raise ApiError("ADMIN_NOTIFICATION_NOT_FOUND", status_code=404)
        return notification

    def _enqueue_admin_telegram_alerts(self, *, notification: AdminNotificationRecord, request_id: str) -> None:
        if not self._admin_telegram_alerts_enabled:
            return
        if self._job_repository is None or self._user_repository is None:
            return
        alert_type = ADMIN_TELEGRAM_ALERT_TYPES.get(notification.notification_type)
        if alert_type is None:
            return
        recipients = self._user_repository.list_active_admin_telegram_recipients()
        if not recipients:
            logger.info(
                "admin_telegram_alert_skipped_no_recipients",
                extra={
                    "event": "admin_telegram_alert_skipped_no_recipients",
                    "admin_notification_id": notification.id,
                    "notification_type": notification.notification_type,
                    "request_id": request_id,
                },
            )
            return
        for recipient in recipients:
            self._job_repository.enqueue_notification(
                notification_type=alert_type,
                recipient_user_id=recipient.id,
                business_id=notification.business_id,
                scheduled_for=utc_now(),
                dedupe_key=f"admin_telegram:{notification.id}:{recipient.id}:{alert_type}",
                metadata_json=mask_metadata(
                    {
                        "channel": "telegram",
                        "target_surface": ADMIN_TELEGRAM_TARGET_SURFACE,
                        "message_text": self._admin_telegram_message(notification),
                        "action_text": "Abrir Admin",
                        "action_url": self._admin_action_url(),
                        "admin_notification_id": notification.id,
                        "admin_notification_type": notification.notification_type,
                        "resource_type": notification.resource_type,
                        "resource_id": notification.resource_id,
                    }
                ),
            )

    def _admin_action_url(self) -> str:
        if not self._admin_app_url:
            return ""
        return f"{self._admin_app_url}/?surface=admin"

    def _admin_telegram_message(self, notification: AdminNotificationRecord) -> str:
        if notification.notification_type == "business_intake_submitted":
            return (
                f"NODO: llego una solicitud de negocio: {notification.summary} "
                "Revisa los datos antes de aprobarla."
            )
        return f"NODO: {notification.title}. {notification.summary}"
