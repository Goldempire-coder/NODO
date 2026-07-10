from __future__ import annotations

import hashlib
import re
from typing import Any
from uuid import UUID

from app.core.config import Settings
from app.core.errors import ApiError
from app.modules.businesses.access_control import evaluate_business_access
from app.modules.chat.models import ALLOWED_ATTACHMENT_MIME_TYPES, MAX_ATTACHMENT_SIZE_BYTES, new_id
from app.modules.chat.policy import require_chat_read, require_chat_write, require_message_state
from app.modules.chat.schemas import MessageCreateRequest
from app.modules.orders.models import OrderRecord
from app.modules.users.models import UserRecord


CHAT_DISCLAIMER = "Usa este chat para coordinar la orden y dejar un respaldo claro entre las partes."


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


class ChatService:
    def __init__(self, *, settings: Settings, repository, order_repository, business_repository, audit_writer, rate_limiter, idempotency_store, storage) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._orders = order_repository
        self._businesses = business_repository
        self._audit = audit_writer
        self._rate_limiter = rate_limiter
        self._idempotency = idempotency_store
        self._storage = storage

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
            "next_cursor": next_cursor,
            "capabilities": {
                "can_send_message": user.role in {"remitter", "business_owner"} and user.status == "active",
                "can_open_dispute": user.role in {"remitter", "business_owner"} and order.status in {"payment_reported", "payment_rejected", "payment_confirmed", "delivered"},
            },
            "disclaimer": CHAT_DISCLAIMER,
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
            return {"message": self._message_public(message, attached), "disclaimer": CHAT_DISCLAIMER}

        return self._idempotency.replay_or_store(f"chat:message:{user.id}:{order.id}:{idempotency_key}", payload=request_payload, compute=compute)

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
