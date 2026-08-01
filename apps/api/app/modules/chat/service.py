from __future__ import annotations

import hashlib
import re
from typing import Any
from uuid import UUID

from app.core.config import Settings
from app.core.errors import ApiError
from app.core.logging import get_logger
from app.modules.chat.moderation import detect_off_platform_solicitation
from app.modules.businesses.access_control import evaluate_business_access
from app.modules.chat.models import ALLOWED_ATTACHMENT_MIME_TYPES, MAX_ATTACHMENT_SIZE_BYTES, new_id
from app.modules.chat.policy import require_chat_read, require_chat_write, require_message_state
from app.modules.chat.schemas import MessageCreateRequest
from app.modules.notifications.chat_notifications import NoopChatNotificationService
from app.modules.orders.models import OrderRecord
from app.modules.users.models import UserRecord


CHAT_DISCLAIMER = "Usa este chat para coordinar la orden y dejar un respaldo claro entre las partes."
NEGOTIATION_CREATED_MESSAGE = (
    "Negociación creada. Coordinen por aquí. "
    "No envíes Zelle hasta que el negocio comparta sus datos."
)
logger = get_logger(__name__)


def _require_uuid(value: str, code: str = "ORDER_NOT_FOUND") -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError) as exc:
        raise ApiError(code, status_code=404 if code.endswith("NOT_FOUND") else 400) from exc


def _sanitize_body(value: str | None) -> str | None:
    if value is None:
        return None
    clean = re.sub(r"<[^>]*>", "", value).strip()
    return clean[:2000]


def _attachment_payload(attachment) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    return {
        "id": attachment.id,
        "file_asset_id": attachment.file_asset_id,
        "file_type": attachment.file_type,
        "mime_type": attachment.mime_type,
        "size_bytes": attachment.size_bytes,
        "created_at": attachment.created_at.isoformat(),
    }


def _message_attachment_filename(*, attachment) -> str:  # type: ignore[no-untyped-def]
    extension_by_mime = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
    }
    extension = extension_by_mime.get(attachment.mime_type, "")
    return f"nodo-message-attachment-{attachment.id[:8]}{extension}"


def _payment_evidence_attachment_payload(file) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    return {
        "id": file.id,
        "file_asset_id": file.id,
        "file_type": file.file_type,
        "mime_type": file.mime_type,
        "size_bytes": file.size_bytes,
        "created_at": file.created_at.isoformat(),
    }


def _payment_evidence_filename(*, file) -> str:  # type: ignore[no-untyped-def]
    extension_by_mime = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
    }
    extension = extension_by_mime.get(file.mime_type, "")
    return f"nodo-payment-evidence-{file.id[:8]}{extension}"


class ChatService:
    def __init__(self, *, settings: Settings, repository, order_repository, business_repository, audit_writer, rate_limiter, idempotency_store, storage, admin_notifications=None, notification_service=None) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._orders = order_repository
        self._businesses = business_repository
        self._audit = audit_writer
        self._rate_limiter = rate_limiter
        self._idempotency = idempotency_store
        self._storage = storage
        self._admin_notifications = admin_notifications
        self._notifications = notification_service or NoopChatNotificationService()

    def _rate_limit(self, action: str, user: UserRecord, order_id: str | None = None) -> None:
        key = f"chat:{action}:{user.id}:{order_id or 'global'}"
        if not self._rate_limiter.allow(
            key,
            max_attempts=self._settings.business_rate_limit_max_attempts,
            window_seconds=self._settings.business_rate_limit_window_seconds,
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def _order(self, order_id: str) -> OrderRecord:
        order_id = _require_uuid(order_id)
        order = self._orders.get_by_id(order_id)
        if order is None:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        return order

    def _business_owner_id(self, order: OrderRecord) -> str | None:
        business = self._businesses.get_business(order.business_id)
        return business.owner_user_id if business else None

    def _require_business_actor_access(self, user: UserRecord, order: OrderRecord) -> None:
        if user.role != "business_owner":
            return
        business = self._businesses.get_business(order.business_id)
        evaluate_business_access(user=user, business=business, business_repository=self._businesses)

    def _require_direct_participant(self, user: UserRecord, order: OrderRecord) -> None:
        business_owner_id = self._business_owner_id(order)
        if user.id not in {order.remitter_user_id, business_owner_id}:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)

    def _message_public(self, message, attachments: list | None = None) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        return {
            "id": message.id,
            "order_id": message.order_id,
            "sender_role": message.sender_role,
            "body": message.body,
            "visibility": message.visibility,
            "status": message.status,
            "attachments": [_attachment_payload(attachment) for attachment in (attachments or [])],
            "created_at": message.created_at.isoformat(),
        }

    @staticmethod
    def _configured_zelle_account(order: OrderRecord) -> str | None:
        if order.payment_method_snapshot != "zelle":
            return None
        account_value = str((order.payment_instructions_snapshot or {}).get("account_value") or "").strip()
        return account_value or None

    def _payment_details_shared(self, order: OrderRecord) -> bool:
        account_value = self._configured_zelle_account(order)
        if account_value is None:
            return order.payment_method_snapshot != "zelle"
        return self._repository.has_business_message_containing(
            order_id=order.id,
            text=account_value,
        )

    def _system_messages(self, order: OrderRecord, cursor: str | None) -> list[dict[str, Any]]:
        if cursor is not None:
            return []
        messages = [
            {
                "id": f"system:negotiation-created:{order.id}",
                "order_id": order.id,
                "sender_role": "system",
                "body": NEGOTIATION_CREATED_MESSAGE,
                "visibility": "parties",
                "status": "visible",
                "attachments": [],
                "created_at": order.created_at.isoformat(),
            }
        ]
        report = self._orders.get_latest_payment_report_for_order(order.id)
        if report is not None:
            evidence = self._orders.list_payment_evidence_for_report(report.id)
            messages.append(
                {
                    "id": f"system:payment-reported:{report.id}",
                    "order_id": order.id,
                    "sender_role": "system",
                    "body": "Cliente marco Pago enviado. Revisa el comprobante adjunto.",
                    "visibility": "parties",
                    "status": "visible",
                    "attachments": [_payment_evidence_attachment_payload(file) for file in evidence],
                    "created_at": report.created_at.isoformat(),
                }
            )
        if order.payment_confirmed_at is not None:
            messages.append(
                {
                    "id": f"system:payment-confirmed:{order.id}",
                    "order_id": order.id,
                    "sender_role": "system",
                    "body": "Negocio confirmo Zelle recibido. Escribe tu Pago Movil en el chat.",
                    "visibility": "parties",
                    "status": "visible",
                    "attachments": [],
                    "created_at": order.payment_confirmed_at.isoformat(),
                }
            )
        receiver_details = self._orders.get_receiver_details(order.id)
        if receiver_details is not None:
            messages.append(
                {
                    "id": f"system:receiver-details-shared:{receiver_details.id}",
                    "order_id": order.id,
                    "sender_role": "system",
                    "body": "Cliente compartio Pago Movil seguro.",
                    "visibility": "parties",
                    "status": "visible",
                    "attachments": [],
                    "created_at": receiver_details.shared_at.isoformat(),
                }
            )
        if order.delivered_at is not None:
            messages.append(
                {
                    "id": f"system:order-delivered:{order.id}",
                    "order_id": order.id,
                    "sender_role": "system",
                    "body": "Negocio marco Pago Movil enviado. Cliente debe confirmar recepcion o abrir caso.",
                    "visibility": "parties",
                    "status": "visible",
                    "attachments": [],
                    "created_at": order.delivered_at.isoformat(),
                }
            )
        if order.completed_at is not None:
            messages.append(
                {
                    "id": f"system:order-completed:{order.id}",
                    "order_id": order.id,
                    "sender_role": "system",
                    "body": "Negociacion completada.",
                    "visibility": "parties",
                    "status": "visible",
                    "attachments": [],
                    "created_at": order.completed_at.isoformat(),
                }
            )
        return messages

    def _capabilities(self, *, user: UserRecord, order: OrderRecord) -> dict[str, bool]:
        payment_details_shared = self._payment_details_shared(order)
        receiver_details_shared = self._orders.has_receiver_details(order.id)
        waiting_payment = order.status == "waiting_payment"
        return {
            "can_send_message": user.role in {"remitter", "business_owner"} and user.status == "active",
            "can_open_dispute": user.role in {"remitter", "business_owner"}
            and order.status
            in {
                "payment_reported",
                "payment_rejected",
                "payment_confirmed",
                "delivered",
            },
            "can_share_zelle": user.role == "business_owner"
            and user.status == "active"
            and waiting_payment
            and self._configured_zelle_account(order) is not None
            and not payment_details_shared,
            "payment_details_shared": payment_details_shared,
            "can_report_payment": user.role == "remitter"
            and waiting_payment
            and payment_details_shared,
            "receiver_details_shared": receiver_details_shared,
            "can_share_receiver_details": False,
            "can_reveal_receiver_details": user.role == "business_owner"
            and user.status == "active"
            and order.status in {"payment_confirmed", "delivered", "disputed"}
            and receiver_details_shared,
            "receiver_details_required": False,
            "can_confirm_received": user.role == "remitter"
            and user.status == "active"
            and order.status == "delivered",
            "can_confirm_payment": user.role == "business_owner"
            and user.status == "active"
            and order.status == "payment_reported",
            "can_mark_delivered": user.role == "business_owner"
            and user.status == "active"
            and order.status == "payment_confirmed",
        }

    def list_messages(self, *, user: UserRecord, order_id: str, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        order = self._order(order_id)
        self._rate_limit("list", user, order.id)
        require_message_state(order)
        require_chat_read(user, order, self._business_owner_id(order))
        self._require_business_actor_access(user, order)
        items, next_cursor = self._repository.list_messages(order_id=order.id, cursor=cursor, limit=limit)
        attachments = self._repository.list_attachments_for_messages([message.id for message in items])
        return {
            "order_id": order.id,
            "items": [self._message_public(message, attachments.get(message.id, [])) for message in items],
            "system_messages": self._system_messages(order, cursor),
            "next_cursor": next_cursor,
            "capabilities": self._capabilities(user=user, order=order),
            "disclaimer": CHAT_DISCLAIMER,
        }

    def attachment_view_url(self, *, user: UserRecord, order_id: str, attachment_id: str, request_id: str) -> dict[str, Any]:
        if self._storage is None:
            raise ApiError("STORAGE_UNAVAILABLE", status_code=503)
        order = self._order(order_id)
        self._rate_limit("attachment_view", user, order.id)
        require_message_state(order)
        self._require_direct_participant(user, order)
        require_chat_read(user, order, self._business_owner_id(order))
        self._require_business_actor_access(user, order)
        normalized_attachment_id = _require_uuid(attachment_id, "MESSAGE_ATTACHMENT_NOT_FOUND")
        attachment = self._repository.get_attachment(normalized_attachment_id)
        if (
            attachment is None
            or attachment.order_id != order.id
            or attachment.message_id is None
            or attachment.status != "active"
        ):
            return self._payment_evidence_view_url(
                user=user,
                order=order,
                file_id=normalized_attachment_id,
                request_id=request_id,
            )
        file = self._repository.get_file_asset(attachment.file_asset_id)
        if (
            file is None
            or file.file_type != "message_attachment"
            or file.resource_type != "message"
            or file.resource_id != attachment.message_id
        ):
            raise ApiError("MESSAGE_ATTACHMENT_NOT_FOUND", status_code=404)
        expires_in = min(self._settings.storage_signed_url_ttl_seconds, 300)
        url = self._storage.signed_view_url(storage_path=file.storage_path, expires_in=expires_in)
        self._audit.write(
            event_type="message_attachment_viewed",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="message_attachment",
            resource_id=attachment.id,
            request_id=request_id,
            metadata_json={
                "order_id": order.id,
                "message_id": attachment.message_id,
                "mime_type": attachment.mime_type,
                "size_bytes": attachment.size_bytes,
            },
        )
        return {
            "url": url,
            "expires_in_seconds": expires_in,
            "download_filename": _message_attachment_filename(attachment=attachment),
        }

    def _payment_evidence_view_url(self, *, user: UserRecord, order: OrderRecord, file_id: str, request_id: str) -> dict[str, Any]:
        self._require_direct_participant(user, order)
        file = self._orders.get_payment_evidence_file(file_id)
        report = self._orders.get_latest_payment_report_for_order(order.id)
        if (
            file is None
            or report is None
            or file.resource_id != report.id
            or (file.metadata_json or {}).get("order_id") != order.id
        ):
            raise ApiError("MESSAGE_ATTACHMENT_NOT_FOUND", status_code=404)
        expires_in = min(self._settings.storage_signed_url_ttl_seconds, 300)
        url = self._storage.signed_view_url(storage_path=file.storage_path, expires_in=expires_in)
        self._audit.write(
            event_type="payment_evidence_viewed_from_chat",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="payment_evidence",
            resource_id=file.id,
            request_id=request_id,
            metadata_json={
                "order_id": order.id,
                "payment_report_id": report.id,
                "mime_type": file.mime_type,
                "size_bytes": file.size_bytes,
            },
        )
        return {
            "url": url,
            "expires_in_seconds": expires_in,
            "download_filename": _payment_evidence_filename(file=file),
        }

    def create_message(self, *, user: UserRecord, order_id: str, payload: MessageCreateRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        order = self._order(order_id)
        self._rate_limit("create", user, order.id)
        require_message_state(order)
        require_chat_write(user, order, self._business_owner_id(order))
        self._require_business_actor_access(user, order)
        body = _sanitize_body(payload.body)
        if not body and not payload.attachment_ids:
            raise ApiError("MESSAGE_BODY_REQUIRED", status_code=400)
        if len(payload.attachment_ids) > 5:
            raise ApiError("MESSAGE_ATTACHMENT_INVALID", status_code=400)
        normalized_attachments = [_require_uuid(attachment_id, "MESSAGE_ATTACHMENT_INVALID") for attachment_id in payload.attachment_ids]
        request_payload = {"order_id": order.id, "body": body, "attachment_ids": normalized_attachments}

        def compute() -> dict[str, Any]:
            for attachment_id in normalized_attachments:
                attachment = self._repository.get_attachment(attachment_id)
                if attachment is None or attachment.order_id != order.id or attachment.uploaded_by_user_id != user.id or attachment.message_id is not None:
                    raise ApiError("MESSAGE_ATTACHMENT_INVALID", status_code=400)
            message = self._repository.create_message(order_id=order.id, sender_user_id=user.id, sender_role=user.role, body=body, idempotency_key=idempotency_key)
            attached = self._repository.attach_to_message(attachment_ids=normalized_attachments, message_id=message.id)
            event_type = "dispute_message_created" if order.status == "disputed" else "message_created"
            self._audit.write(
                event_type=event_type,
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="message",
                resource_id=message.id,
                request_id=request_id,
                metadata_json={"order_id": order.id, "attachment_count": len(attached)},
            )
            self._inspect_business_message_for_off_platform_solicitation(user=user, order=order, message=message, request_id=request_id)
            self._notifications.message_created(
                order=order,
                message=message,
                sender_role=user.role,
                request_id=request_id,
            )
            return {
                "message": self._message_public(message, attached),
                "capabilities": self._capabilities(user=user, order=order),
                "disclaimer": CHAT_DISCLAIMER,
            }

        return self._idempotency.replay_or_store(f"chat:message:{user.id}:{order.id}:{idempotency_key}", payload=request_payload, compute=compute)

    def share_configured_zelle(
        self,
        *,
        user: UserRecord,
        order_id: str,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        order = self._order(order_id)
        self._rate_limit("share_zelle", user, order.id)
        require_message_state(order)
        if user.role != "business_owner":
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        require_chat_write(user, order, self._business_owner_id(order))
        self._require_business_actor_access(user, order)
        if order.status != "waiting_payment":
            raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
        account_value = self._configured_zelle_account(order)
        if account_value is None:
            raise ApiError("ORDER_PAYMENT_METHOD_UNAVAILABLE", status_code=409)
        holder_name = str(
            (order.payment_instructions_snapshot or {}).get("holder_name") or ""
        ).strip()
        body = f"Zelle del negocio: {account_value}"
        if holder_name:
            body = f"{body}\nTitular: {holder_name}"

        def compute() -> dict[str, Any]:
            message, created = self._repository.create_configured_payment_message_once(
                order_id=order.id,
                sender_user_id=user.id,
                body=body,
                account_value=account_value,
                idempotency_key=idempotency_key,
            )
            if created:
                self._audit.write(
                    event_type="business_zelle_shared",
                    actor_user_id=user.id,
                    actor_role=user.role,
                    resource_type="message",
                    resource_id=message.id,
                    request_id=request_id,
                    metadata_json={
                        "order_id": order.id,
                        "business_id": order.business_id,
                    },
                )
                self._inspect_business_message_for_off_platform_solicitation(
                    user=user,
                    order=order,
                    message=message,
                    request_id=request_id,
                )
                self._notifications.message_created(
                    order=order,
                    message=message,
                    sender_role=user.role,
                    request_id=request_id,
                )
            return {
                "message": self._message_public(message),
                "capabilities": self._capabilities(user=user, order=order),
                "disclaimer": CHAT_DISCLAIMER,
            }

        return self._idempotency.replay_or_store(
            f"chat:share_zelle:{user.id}:{order.id}:{idempotency_key}",
            payload={"order_id": order.id, "action": "share_configured_zelle"},
            compute=compute,
        )

    def _inspect_business_message_for_off_platform_solicitation(self, *, user: UserRecord, order: OrderRecord, message, request_id: str) -> None:  # type: ignore[no-untyped-def]
        if user.role != "business_owner":
            return
        account_value = self._configured_zelle_account(order)
        match = detect_off_platform_solicitation(
            message.body,
            allowed_contact_values=(account_value,) if account_value else (),
        )
        if match is None:
            return
        self._audit.write(
            event_type="order_chat_off_platform_solicitation_detected",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="message",
            resource_id=message.id,
            request_id=request_id,
            metadata_json={
                "order_id": order.id,
                "business_id": order.business_id,
                "rule_id": match.rule_id,
                "severity": match.severity,
            },
        )
        if self._admin_notifications is not None:
            try:
                self._admin_notifications.order_chat_off_platform_solicitation(order=order, message=message, match=match, request_id=request_id)
            except Exception as exc:
                logger.warning(
                    "order_chat_off_platform_alert_failed",
                    extra={
                        "event": "order_chat_off_platform_alert_failed",
                        "order_id": order.id,
                        "message_id": message.id,
                        "business_id": order.business_id,
                        "rule_id": match.rule_id,
                        "error_code": type(exc).__name__,
                        "request_id": request_id,
                    },
                )

    def upload_attachment(
        self,
        *,
        user: UserRecord,
        order_id: str,
        file_name: str,
        mime_type: str,
        content: bytes,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        if self._storage is None:
            raise ApiError("STORAGE_UNAVAILABLE", status_code=503)
        order = self._order(order_id)
        self._validate_attachment_upload(user=user, order=order, mime_type=mime_type, content=content)
        payload = self._attachment_idempotency_payload(order=order, file_name=file_name, mime_type=mime_type, content=content)

        def compute() -> dict[str, Any]:
            return self._compute_attachment_upload(user=user, order=order, file_name=file_name, mime_type=mime_type, content=content, request_id=request_id)

        return self._idempotency.replay_or_store(f"chat:attachment:{user.id}:{order.id}:{idempotency_key}", payload=payload, compute=compute)

    def _validate_attachment_upload(self, *, user: UserRecord, order: OrderRecord, mime_type: str, content: bytes) -> None:
        self._rate_limit("attachment", user, order.id)
        require_message_state(order)
        require_chat_write(user, order, self._business_owner_id(order))
        self._require_business_actor_access(user, order)
        if mime_type not in ALLOWED_ATTACHMENT_MIME_TYPES:
            raise ApiError("MESSAGE_ATTACHMENT_TYPE_NOT_ALLOWED", status_code=400)
        if not content:
            raise ApiError("MESSAGE_ATTACHMENT_INVALID", status_code=400)
        if len(content) > MAX_ATTACHMENT_SIZE_BYTES:
            raise ApiError("MESSAGE_ATTACHMENT_TOO_LARGE", status_code=400)

    def _attachment_idempotency_payload(self, *, order: OrderRecord, file_name: str, mime_type: str, content: bytes) -> dict[str, Any]:
        return {
            "order_id": order.id,
            "file_name": file_name,
            "mime_type": mime_type,
            "size_bytes": len(content),
            "content_sha256": hashlib.sha256(content).hexdigest(),
        }

    def _compute_attachment_upload(self, *, user: UserRecord, order: OrderRecord, file_name: str, mime_type: str, content: bytes, request_id: str) -> dict[str, Any]:
        file_id = new_id()
        attachment_id = new_id()
        stored = self._storage.store_message_attachment(order_id=order.id, attachment_id=attachment_id, file_id=file_id, file_name=file_name, content=content)
        _, attachment = self._repository.create_attachment_file(
            file_id=file_id,
            attachment_id=attachment_id,
            owner_user_id=user.id,
            order_id=order.id,
            storage_path=stored.storage_path,
            mime_type=mime_type,
            size_bytes=stored.size_bytes,
        )
        self._audit_attachment_upload(user=user, order=order, attachment=attachment, file_id=file_id, mime_type=mime_type, size_bytes=stored.size_bytes, request_id=request_id)
        return {"attachment": _attachment_payload(attachment), "disclaimer": CHAT_DISCLAIMER}

    def _audit_attachment_upload(self, *, user: UserRecord, order: OrderRecord, attachment, file_id: str, mime_type: str, size_bytes: int, request_id: str) -> None:  # type: ignore[no-untyped-def]
        self._audit.write(
            event_type="message_attachment_uploaded",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="message_attachment",
            resource_id=attachment.id,
            request_id=request_id,
            metadata_json={"order_id": order.id, "file_asset_id": file_id, "mime_type": mime_type, "size_bytes": size_bytes},
        )
