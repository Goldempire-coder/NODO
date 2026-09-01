from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import ApiError
from app.modules.admin.policy import require_admin_operations_read
from app.modules.users.models import UserRecord


def _require_uuid(value: str, code: str) -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError) as exc:
        raise ApiError(code, status_code=404) from exc


def _sender_label(role: str) -> str:
    return {
        "remitter": "Cliente",
        "business_owner": "Negocio",
        "admin": "NODO Admin",
        "super_admin": "NODO Admin",
        "support": "Soporte NODO",
    }.get(role, "Participante")


def _attachment_payload(attachment) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    return {
        "attachment_id": attachment.id,
        "mime_type": attachment.mime_type,
        "size_bytes": attachment.size_bytes,
        "download_available": False,
    }


class AdminOrderChatEvidenceService:
    def __init__(self, *, settings, order_repository, chat_repository, audit_writer, rate_limiter) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._orders = order_repository
        self._chat = chat_repository
        self._audit = audit_writer
        self._rate = rate_limiter

    def _rate_limit(self, *, user: UserRecord, order_id: str) -> None:
        key = f"admin:order_chat_evidence:{user.id}:{order_id}"
        if not self._rate.allow(
            key,
            max_attempts=self._settings.business_rate_limit_max_attempts,
            window_seconds=self._settings.business_rate_limit_window_seconds,
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def list_evidence(
        self,
        *,
        user: UserRecord,
        order_id: str,
        cursor: str | None,
        direction: str | None,
        limit: int,
        highlight_message_id: str | None,
        request_id: str,
    ) -> dict[str, Any]:
        require_admin_operations_read(user)
        order_id = _require_uuid(order_id, "ORDER_NOT_FOUND")
        self._rate_limit(user=user, order_id=order_id)
        if self._orders.get_by_id(order_id) is None:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        highlighted_message = None
        if highlight_message_id:
            highlight_message_id = _require_uuid(highlight_message_id, "MESSAGE_NOT_FOUND")
            highlighted_message = self._chat.get_message(highlight_message_id)
            if highlighted_message is None or highlighted_message.order_id != order_id:
                raise ApiError("MESSAGE_NOT_FOUND", status_code=404)
        page_direction = direction if cursor and direction in {"older", "newer"} else "initial"
        anchor_created_at = highlighted_message.created_at if highlighted_message is not None and cursor is None else None
        items, older_cursor, newer_cursor = self._chat.list_messages_for_evidence(
            order_id=order_id,
            cursor=cursor,
            direction=page_direction,
            limit=limit,
            anchor_created_at=anchor_created_at,
            anchor_message_id=highlighted_message.id if highlighted_message is not None else None,
        )
        attachments = self._chat.list_attachments_for_messages([message.id for message in items])
        highlight_found = bool(highlight_message_id and any(message.id == highlight_message_id for message in items))
        response_items = [
            {
                "message_id": message.id,
                "sender_role": message.sender_role,
                "sender_label": _sender_label(message.sender_role),
                "body": message.body,
                "status": message.status,
                "created_at": message.created_at.isoformat(),
                "highlighted": message.id == highlight_message_id,
                "attachments": [_attachment_payload(attachment) for attachment in attachments.get(message.id, [])],
            }
            for message in items
        ]
        self._audit.write(
            event_type="admin_order_chat_viewed",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="order",
            resource_id=order_id,
            request_id=request_id,
            metadata_json={
                "message_count": len(response_items),
                "highlight_requested": highlight_message_id is not None,
                "highlight_found": highlight_found,
                "page_direction": page_direction,
            },
        )
        return {
            "order_id": order_id,
            "items": response_items,
            "older_cursor": older_cursor,
            "newer_cursor": newer_cursor,
            "highlight_message_id": highlight_message_id,
            "highlight_found": highlight_found,
        }
