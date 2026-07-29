from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.modules.jobs.models import mask_metadata
from app.modules.notifications.notification_types import ORDER_NOTIFICATION_TYPES
from app.modules.orders.models import OrderRecord

logger = get_logger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _decimal_text(value: Decimal) -> str:
    return f"{value:.2f}"


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
        correlation_id: str | None = None,
        operation_id: str | None = None,
    ) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._jobs = job_repository
        self._businesses = business_repository
        self._correlation_id = correlation_id
        self._operation_id = operation_id

    def order_created_business(self, *, order: OrderRecord, request_id: str, correlation_id: str | None = None, operation_id: str | None = None) -> None:
        business = self._businesses.get_business(order.business_id)
        if business is None:
            self._log_enqueue_skipped("order_created_business", order, "BUSINESS_NOT_FOUND", request_id)
            return
        self._enqueue(
            notification_type="order_created_business",
            order=order,
            recipient_user_id=business.owner_user_id,
            target_surface="business_mini_app",
            text=self._business_order_created_text(order),
            action_url=self._business_order_url(order.id),
            request_id=request_id,
            correlation_id=correlation_id,
            operation_id=operation_id,
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

    def payment_confirmed_client(self, *, order: OrderRecord, request_id: str, correlation_id: str | None = None, operation_id: str | None = None) -> None:
        self._enqueue(
            notification_type="payment_confirmed_client",
            order=order,
            recipient_user_id=order.remitter_user_id,
            target_surface="client_mini_app",
            text=f"Pago confirmado en la orden {order.public_order_code}. El negocio debe marcar el envio cuando complete la entrega.",
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
                f"El negocio marco el pago movil como enviado en la orden {order.public_order_code}. "
                "Si tu receptor no recibio, abre disputa antes de que la orden cierre automaticamente."
            ),
            action_url=self._client_order_url(order.id),
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
    ) -> None:
        if notification_type not in ORDER_NOTIFICATION_TYPES:
            raise ValueError(f"unsupported order notification type: {notification_type}")
        logical_recipient = recipient_user_id or recipient_role
        if not logical_recipient:
            self._log_enqueue_skipped(notification_type, order, "RECIPIENT_REQUIRED", request_id)
            return
        dedupe_key = f"order:{order.id}:event:{notification_type}:recipient:{logical_recipient}"
        metadata = mask_metadata(
            {
                "channel": "telegram",
                "delivery_state": "pending",
                "event": notification_type,
                "target_surface": target_surface,
                "public_order_code": order.public_order_code,
                "order_status": order.status,
                "amount_usd": _decimal_text(order.amount_usd),
                "payment_method": order.payment_method_snapshot,
                "delivery_method": order.delivery_method_snapshot,
                "message_text": text,
                "action_text": "Abrir orden",
                "action_url": action_url,
                **_safe_operation_context(
                    request_id=request_id,
                    correlation_id=correlation_id or self._correlation_id,
                    operation_id=operation_id or self._operation_id,
                ),
            }
        )
        try:
            notification, created = self._jobs.enqueue_notification(
                notification_type=notification_type,
                recipient_user_id=recipient_user_id,
                recipient_role=recipient_role,
                order_id=order.id,
                business_id=order.business_id,
                dispute_id=dispute_id,
                scheduled_for=_now(),
                dedupe_key=dedupe_key,
                metadata_json=metadata,
            )
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

    def _business_order_created_text(self, order: OrderRecord) -> str:
        return (
            f"Nueva orden {order.public_order_code} por {_decimal_text(order.amount_usd)} USD. "
            f"Metodo: {order.payment_method_snapshot}. Abre la orden para revisar los datos seguros."
        )

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
    def order_created_business(self, **_: Any) -> None:
        return

    def payment_reported_business(self, **_: Any) -> None:
        return

    def order_cancelled_before_payment_business(self, **_: Any) -> None:
        return

    def payment_confirmed_client(self, **_: Any) -> None:
        return

    def payment_rejected_client(self, **_: Any) -> None:
        return

    def order_delivered_client(self, **_: Any) -> None:
        return

    def order_disputed_parties_admin(self, **_: Any) -> None:
        return
