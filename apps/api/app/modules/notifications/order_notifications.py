from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.modules.jobs.models import mask_metadata
from app.modules.notifications.notification_types import ORDER_NOTIFICATION_TYPES
from app.modules.notifications.order_notification_jobs import (
    OrderCreatedBusinessNotificationPlan,
    build_order_created_business_job,
)
from app.modules.orders.models import OrderRecord

logger = get_logger(__name__)
ADMIN_ALERT_TARGET_SURFACE = "admin_alerts"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_operation_context(
    *,
    request_id: str,
    correlation_id: str | None = None,
    operation_id: str | None = None,
) -> dict[str, str]:
    context = {"request_id": request_id}
    if correlation_id:
        context["correlation_id"] = correlation_id
    if operation_id:
        context["operation_id"] = operation_id
    return context


class OrderNotificationService:
    def __init__(
        self,
        *,
        settings: Settings,
        job_repository,
        business_repository,
        user_repository=None,
        admin_telegram_alerts_enabled: bool = False,
        correlation_id: str | None = None,
        operation_id: str | None = None,
    ) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._jobs = job_repository
        self._businesses = business_repository
        self._users = user_repository
        self._admin_telegram_alerts_enabled = admin_telegram_alerts_enabled
        self._correlation_id = correlation_id
        self._operation_id = operation_id

    def order_created_business(self, *, order: OrderRecord, request_id: str, correlation_id: str | None = None, operation_id: str | None = None) -> None:
        business = self._businesses.get_business(order.business_id)
        if business is None:
            self._log_enqueue_skipped("order_created_business", order, "BUSINESS_NOT_FOUND", request_id)
            return
        fields = build_order_created_business_job(
            order=order,
            plan=self.order_created_business_plan(
                business=business,
                request_id=request_id,
                correlation_id=correlation_id,
                operation_id=operation_id,
            ),
        )
        self._enqueue_fields(fields=fields, order=order, request_id=request_id)

    def order_created_business_plan(
        self,
        *,
        business,
        request_id: str,
        correlation_id: str | None = None,
        operation_id: str | None = None,
    ) -> OrderCreatedBusinessNotificationPlan:  # type: ignore[no-untyped-def]
        return OrderCreatedBusinessNotificationPlan(
            recipient_user_id=business.owner_user_id,
            web_app_base_url=self._settings.telegram_web_app_url,
            request_id=request_id,
            correlation_id=correlation_id or self._correlation_id,
            operation_id=operation_id or self._operation_id,
        )

    def payment_reported_business(self, *, order: OrderRecord, request_id: str, correlation_id: str | None = None, operation_id: str | None = None) -> None:
        business = self._businesses.get_business(order.business_id)
        if business is None:
            self._log_enqueue_skipped("payment_reported_business", order, "BUSINESS_NOT_FOUND", request_id)
            return
        self._enqueue(
            notification_type="payment_reported_business",
            order=order,
            recipient_user_id=business.owner_user_id,
            target_surface="business_mini_app",
            text=f"Pago reportado en la orden {order.public_order_code}. Revisa la orden y confirma si recibiste el pago.",
            action_url=self._business_order_url(order.id),
            request_id=request_id,
            correlation_id=correlation_id,
            operation_id=operation_id,
        )

    def order_cancelled_before_payment_business(
        self,
        *,
        order: OrderRecord,
        request_id: str,
        correlation_id: str | None = None,
        operation_id: str | None = None,
    ) -> None:
        business = self._businesses.get_business(order.business_id)
        if business is None:
            self._log_enqueue_skipped(
                "order_cancelled_payment_not_reported",
                order,
                "BUSINESS_NOT_FOUND",
                request_id,
            )
            return
        self._enqueue(
            notification_type="order_cancelled_payment_not_reported",
            order=order,
            recipient_user_id=business.owner_user_id,
            target_surface="business_mini_app",
            text=(
                f"La orden {order.public_order_code} fue cancelada por el cliente "
                "antes de reportar pago."
            ),
            action_url=self._business_order_url(order.id),
            request_id=request_id,
            correlation_id=correlation_id,
            operation_id=operation_id,
        )

    def order_cancelled_business_unavailable_client(
        self,
        *,
        order: OrderRecord,
        request_id: str,
        correlation_id: str | None = None,
        operation_id: str | None = None,
    ) -> None:
        self._enqueue(
            notification_type="order_cancelled_business_unavailable",
            order=order,
            recipient_user_id=order.remitter_user_id,
            target_surface="client_mini_app",
            text=(
                f"El negocio no puede atender la orden {order.public_order_code}. "
                "La orden fue cancelada antes de reportar pago."
            ),
            action_url=self._client_order_url(order.id),
            request_id=request_id,
            correlation_id=correlation_id,
            operation_id=operation_id,
        )

    def payment_confirmed_client(self, *, order: OrderRecord, request_id: str, correlation_id: str | None = None, operation_id: str | None = None) -> None:
        self._enqueue(
            notification_type="payment_confirmed_client",
            order=order,
            recipient_user_id=order.remitter_user_id,
            target_surface="client_mini_app",
            text=f"La orden {order.public_order_code} fue actualizada. Abre NODO para continuar.",
            action_url=self._client_order_url(order.id),
            request_id=request_id,
            correlation_id=correlation_id,
            operation_id=operation_id,
        )

    def payment_rejected_client(self, *, order: OrderRecord, request_id: str, correlation_id: str | None = None, operation_id: str | None = None) -> None:
        self._enqueue(
            notification_type="payment_rejected_client",
            order=order,
            recipient_user_id=order.remitter_user_id,
            target_surface="client_mini_app",
            text=f"El negocio no reconocio el pago reportado para la orden {order.public_order_code}. Revisa la orden y conserva la trazabilidad.",
            action_url=self._client_order_url(order.id),
            request_id=request_id,
            correlation_id=correlation_id,
            operation_id=operation_id,
        )

    def order_delivered_client(self, *, order: OrderRecord, request_id: str, correlation_id: str | None = None, operation_id: str | None = None) -> None:
        self._enqueue(
            notification_type="order_delivered_client",
            order=order,
            recipient_user_id=order.remitter_user_id,
            target_surface="client_mini_app",
            text=(
                f"La orden {order.public_order_code} fue actualizada. "
                "Confirma la recepcion desde NODO o abre una disputa si corresponde."
            ),
            action_url=self._client_order_url(order.id),
            request_id=request_id,
            correlation_id=correlation_id,
            operation_id=operation_id,
        )

    def order_receiver_details_shared_business(
        self,
        *,
        order: OrderRecord,
        request_id: str,
        correlation_id: str | None = None,
        operation_id: str | None = None,
    ) -> None:
        business = self._businesses.get_business(order.business_id)
        if business is None:
            self._log_enqueue_skipped(
                "order_receiver_details_shared_business",
                order,
                "BUSINESS_NOT_FOUND",
                request_id,
            )
            return
        self._enqueue(
            notification_type="order_receiver_details_shared_business",
            order=order,
            recipient_user_id=business.owner_user_id,
            target_surface="business_mini_app",
            text=f"La orden {order.public_order_code} fue actualizada. Abre NODO para continuar.",
            action_url=self._business_order_url(order.id),
            request_id=request_id,
            correlation_id=correlation_id,
            operation_id=operation_id,
        )

    def order_completed_business(
        self,
        *,
        order: OrderRecord,
        request_id: str,
        correlation_id: str | None = None,
        operation_id: str | None = None,
    ) -> None:
        business = self._businesses.get_business(order.business_id)
        if business is None:
            self._log_enqueue_skipped(
                "order_completed_business",
                order,
                "BUSINESS_NOT_FOUND",
                request_id,
            )
            return
        self._enqueue(
            notification_type="order_completed_business",
            order=order,
            recipient_user_id=business.owner_user_id,
            target_surface="business_mini_app",
            text=f"El cliente confirmo la recepcion en la orden {order.public_order_code}. La orden esta completada.",
            action_url=self._business_order_url(order.id),
            request_id=request_id,
            correlation_id=correlation_id,
            operation_id=operation_id,
        )

    def order_disputed_parties_admin(
        self,
        *,
        order: OrderRecord,
        dispute_id: str,
        request_id: str,
        correlation_id: str | None = None,
        operation_id: str | None = None,
    ) -> None:
        business = self._businesses.get_business(order.business_id)
        recipients: list[tuple[str | None, str | None, str, str]] = [
            (order.remitter_user_id, None, "client_mini_app", self._client_order_url(order.id)),
        ]
        if business is not None:
            recipients.append((business.owner_user_id, None, "business_mini_app", self._business_order_url(order.id)))
        recipients.extend([(None, "admin", "admin_web", ""), (None, "support", "admin_web", "")])
        for recipient_user_id, recipient_role, target_surface, action_url in recipients:
            self._enqueue(
                notification_type="order_disputed_parties_admin",
                order=order,
                recipient_user_id=recipient_user_id,
                recipient_role=recipient_role,
                target_surface=target_surface,
                text=f"La orden {order.public_order_code} paso a disputa. Revisa el estado actual en NODO.",
                action_url=action_url,
                request_id=request_id,
                correlation_id=correlation_id,
                operation_id=operation_id,
                dispute_id=dispute_id,
            )
        self._enqueue_admin_dispute_alerts(order=order, dispute_id=dispute_id, request_id=request_id)

    def order_dispute_resolution_parties(
        self,
        *,
        order: OrderRecord,
        dispute_id: str,
        resolution_type: str,
        request_id: str,
    ) -> None:
        business = self._businesses.get_business(order.business_id)
        recipients: list[tuple[str, str, str]] = [
            (order.remitter_user_id, "client_mini_app", self._client_order_url(order.id)),
        ]
        if business is not None:
            recipients.append((business.owner_user_id, "business_mini_app", self._business_order_url(order.id)))
        for recipient_user_id, target_surface, action_url in recipients:
            self._enqueue(
                # Reuse the existing DB-constrained dispute notification family;
                # metadata distinguishes the final administrative update.
                notification_type="order_disputed_parties_admin",
                order=order,
                recipient_user_id=recipient_user_id,
                target_surface=target_surface,
                text=f"La orden {order.public_order_code} fue actualizada por una decision administrativa. Revisa el estado actual en NODO.",
                action_url=action_url,
                request_id=request_id,
                correlation_id=None,
                operation_id=None,
                dispute_id=dispute_id,
                dedupe_suffix=f"resolution:{resolution_type}",
                metadata_extra={"dispute_update": "resolution"},
            )

    def _enqueue(
        self,
        *,
        notification_type: str,
        order: OrderRecord,
        recipient_user_id: str | None,
        target_surface: str,
        text: str,
        action_url: str,
        request_id: str,
        correlation_id: str | None,
        operation_id: str | None,
        recipient_role: str | None = None,
        dispute_id: str | None = None,
        dedupe_suffix: str | None = None,
        metadata_extra: dict[str, Any] | None = None,
    ) -> None:
        if notification_type not in ORDER_NOTIFICATION_TYPES:
            raise ValueError(f"unsupported order notification type: {notification_type}")
        logical_recipient = recipient_user_id or recipient_role
        if not logical_recipient:
            self._log_enqueue_skipped(notification_type, order, "RECIPIENT_REQUIRED", request_id)
            return
        dedupe_key = f"order:{order.id}:event:{notification_type}:recipient:{logical_recipient}"
        if dedupe_suffix:
            dedupe_key = f"{dedupe_key}:{dedupe_suffix}"
        metadata = mask_metadata(
            {
                "channel": "telegram",
                "delivery_state": "pending",
                "event": notification_type,
                "target_surface": target_surface,
                "public_order_code": order.public_order_code,
                "order_status": order.status,
                "message_text": text,
                "action_text": "Abrir orden",
                "action_url": action_url,
                **(metadata_extra or {}),
                **_safe_operation_context(
                    request_id=request_id,
                    correlation_id=correlation_id or self._correlation_id,
                    operation_id=operation_id or self._operation_id,
                ),
            }
        )
        self._enqueue_fields(
            fields={
                "notification_type": notification_type,
                "recipient_user_id": recipient_user_id,
                "recipient_role": recipient_role,
                "order_id": order.id,
                "business_id": order.business_id,
                "dispute_id": dispute_id,
                "scheduled_for": _now(),
                "dedupe_key": dedupe_key,
                "metadata_json": metadata,
            },
            order=order,
            request_id=request_id,
        )

    def _enqueue_fields(
        self,
        *,
        fields: dict[str, Any],
        order: OrderRecord,
        request_id: str,
    ) -> None:
        notification_type = str(fields["notification_type"])
        logical_recipient = fields.get("recipient_user_id") or fields.get("recipient_role")
        try:
            notification, created = self._jobs.enqueue_notification(**fields)
        except Exception as exc:
            logger.warning(
                "notification_job_enqueue_failed",
                extra={
                    "event": "notification_job_enqueue_failed",
                    "notification_type": notification_type,
                    "order_id": order.id,
                    "recipient": logical_recipient,
                    "request_id": request_id,
                    "error_code": getattr(exc, "code", "NOTIFICATION_ENQUEUE_FAILED"),
                },
            )
            return
        logger.info(
            "notification_job_enqueued",
            extra={
                "event": "notification_job_enqueued",
                "notification_job_id": notification.id,
                "notification_type": notification_type,
                "order_id": order.id,
                "recipient": logical_recipient,
                "notification_created": created,
                "request_id": request_id,
            },
        )

    def _enqueue_admin_dispute_alerts(self, *, order: OrderRecord, dispute_id: str, request_id: str) -> None:
        if not self._admin_telegram_alerts_enabled or self._users is None:
            return
        recipients = self._users.list_active_admin_telegram_recipients()
        if not recipients:
            self._log_enqueue_skipped("admin_alert_dispute_opened", order, "NO_ADMIN_TELEGRAM_RECIPIENTS", request_id)
            return
        for recipient in recipients:
            self._enqueue_fields(
                fields={
                    "notification_type": "admin_alert_dispute_opened",
                    "recipient_user_id": recipient.id,
                    "order_id": order.id,
                    "business_id": order.business_id,
                    "dispute_id": dispute_id,
                    "scheduled_for": _now(),
                    "dedupe_key": f"admin_telegram:dispute:{dispute_id}:{recipient.id}:opened",
                    "metadata_json": mask_metadata(
                        {
                            "channel": "telegram",
                            "delivery_state": "pending",
                            "event": "admin_alert_dispute_opened",
                            "target_surface": ADMIN_ALERT_TARGET_SURFACE,
                            "public_order_code": order.public_order_code,
                            "message_text": (
                                "NODO alerta\n\n"
                                f"Se abrio una disputa en la orden {order.public_order_code}.\n\n"
                                "Accion sugerida: abre Admin > Disputas para revisar el caso "
                                "antes de resolverlo."
                            ),
                            "action_text": "Abrir panel Admin",
                            "action_url": f"{self._settings.telegram_web_app_url}/?surface=admin",
                            "order_id": order.id,
                            "dispute_id": dispute_id,
                        }
                    ),
                },
                order=order,
                request_id=request_id,
            )

    def _business_order_created_text(self, order: OrderRecord) -> str:
        return f"Nueva negociacion {order.public_order_code}. Abre NODO para revisarla."

    def _business_order_chat_url(self, order_id: str) -> str:
        base_url = self._settings.telegram_web_app_url.rstrip("/")
        return f"{base_url}/business/?view=business-chat&order_id={order_id}"

    def _business_order_url(self, order_id: str) -> str:
        base_url = self._settings.telegram_web_app_url.rstrip("/")
        return f"{base_url}/business/?view=business-order-detail&order_id={order_id}"

    def _client_order_url(self, order_id: str) -> str:
        base_url = self._settings.telegram_web_app_url.rstrip("/")
        return f"{base_url}/?view=order-summary&order_id={order_id}"

    def _log_enqueue_skipped(self, notification_type: str, order: OrderRecord, error_code: str, request_id: str) -> None:
        logger.warning(
            "notification_job_enqueue_skipped",
            extra={
                "event": "notification_job_enqueue_skipped",
                "notification_type": notification_type,
                "order_id": order.id,
                "error_code": error_code,
                "request_id": request_id,
            },
        )


class NoopOrderNotificationService:
    def order_created_business_plan(self, **_: Any) -> None:
        return None

    def order_created_business(self, **_: Any) -> None:
        return

    def payment_reported_business(self, **_: Any) -> None:
        return

    def order_cancelled_before_payment_business(self, **_: Any) -> None:
        return

    def order_cancelled_business_unavailable_client(self, **_: Any) -> None:
        return

    def payment_confirmed_client(self, **_: Any) -> None:
        return

    def payment_rejected_client(self, **_: Any) -> None:
        return

    def order_delivered_client(self, **_: Any) -> None:
        return

    def order_receiver_details_shared_business(self, **_: Any) -> None:
        return

    def order_completed_business(self, **_: Any) -> None:
        return

    def order_disputed_parties_admin(self, **_: Any) -> None:
        return

    def order_dispute_resolution_parties(self, **_: Any) -> None:
        return
