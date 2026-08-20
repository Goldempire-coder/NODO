from __future__ import annotations

import hmac
from typing import Any

from fastapi import APIRouter, Header, Request

from app.core.config import Settings
from app.core.errors import ApiError
from app.modules.notifications.telegram_sender import TelegramNotificationAdapter
from app.routes.telegram_bot import telegram_webhook_secret

router = APIRouter(tags=["admin-telegram-bot"])


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or "admin_telegram_webhook"


def _safe_text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _telegram_adapter(request: Request) -> TelegramNotificationAdapter:
    return getattr(request.app.state, "admin_telegram_adapter", TelegramNotificationAdapter())


def _send_admin_bot_message(request: Request, *, chat_id: int, text: str) -> None:
    settings: Settings = request.app.state.settings
    if not settings.nodo_admin_telegram_bot_token:
        raise ApiError("TELEGRAM_BOT_NOT_CONFIGURED", status_code=503)
    _telegram_adapter(request).send_message(
        bot_token=settings.nodo_admin_telegram_bot_token,
        chat_id=chat_id,
        text=text,
    )


async def _handle_admin_telegram_webhook(*, provided_secret: str | None, request: Request) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    if not settings.nodo_admin_telegram_bot_token:
        raise ApiError("TELEGRAM_BOT_NOT_CONFIGURED", status_code=503)

    expected_secret = telegram_webhook_secret(settings.nodo_admin_telegram_bot_token)
    if not provided_secret or not hmac.compare_digest(provided_secret, expected_secret):
        raise ApiError("FORBIDDEN", status_code=403)

    try:
        update = await request.json()
    except ValueError as exc:
        raise ApiError("VALIDATION_ERROR", status_code=422) from exc
    if not isinstance(update, dict):
        raise ApiError("VALIDATION_ERROR", status_code=422)

    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    chat_id = chat.get("id")
    telegram_id = sender.get("id")
    if chat_id is None or telegram_id is None:
        return {"data": {"ok": True, "handled": False}, "request_id": _request_id(request)}

    text = _safe_text(message.get("text")).strip()
    if not text.startswith("/start"):
        _send_admin_bot_message(
            request,
            chat_id=int(chat_id),
            text="NODO Admin: este bot envia alertas operativas importantes. Escribe /start para verificar el acceso.",
        )
        return {"data": {"ok": True, "handled": True, "action": "admin_alerts_hint"}, "request_id": _request_id(request)}

    user = request.app.state.user_repository.get_user_by_telegram_id(int(telegram_id))
    if user is not None and user.status == "active" and user.role in {"admin", "super_admin"}:
        _send_admin_bot_message(
            request,
            chat_id=int(chat_id),
            text="Listo. Este Telegram puede recibir alertas Admin importantes de NODO.",
        )
        return {"data": {"ok": True, "handled": True, "action": "admin_alerts_ready"}, "request_id": _request_id(request)}

    _send_admin_bot_message(
        request,
        chat_id=int(chat_id),
        text="No pude activar alertas Admin en este Telegram. Vincula primero este Telegram a un Admin o Super Admin activo.",
    )
    return {"data": {"ok": True, "handled": True, "action": "admin_alerts_not_linked"}, "request_id": _request_id(request)}


@router.post("/admin-telegram/webhook")
async def admin_telegram_webhook(
    request: Request,
    telegram_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
) -> dict[str, Any]:
    return await _handle_admin_telegram_webhook(provided_secret=telegram_secret, request=request)
