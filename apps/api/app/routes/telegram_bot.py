from __future__ import annotations

import hashlib
import hmac
from typing import Any

import httpx
from fastapi import APIRouter, Request

from app.core.config import Settings
from app.core.errors import ApiError

router = APIRouter(tags=["telegram-bot"])


def telegram_webhook_secret(bot_token: str) -> str:
    return hashlib.sha256(bot_token.encode("utf-8")).hexdigest()[:40]


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or "telegram_webhook"


def _safe_text(value: Any) -> str:
    return value if isinstance(value, str) else ""


async def _telegram_post(settings: Settings, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.bot_token:
        raise ApiError("TELEGRAM_BOT_NOT_CONFIGURED", status_code=503)

    url = f"https://api.telegram.org/bot{settings.bot_token}/{method}"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ApiError("TELEGRAM_BOT_SEND_FAILED", status_code=502) from exc

    if data.get("ok") is not True:
        raise ApiError("TELEGRAM_BOT_SEND_FAILED", status_code=502)
    return data


async def _send_welcome(settings: Settings, chat_id: int | str) -> None:
    fallback_text = "Bienvenido a NODO. Usa el boton Abrir NODO del menu de Telegram para comenzar."
    try:
        await _telegram_post(
            settings,
            "sendPhoto",
            {
                "chat_id": chat_id,
                "photo": settings.telegram_welcome_image_url,
                "caption": "Usa el boton Abrir NODO para comenzar.",
            },
        )
    except ApiError:
        await _telegram_post(
            settings,
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": fallback_text,
            },
        )


async def _send_open_hint(settings: Settings, chat_id: int | str) -> None:
    await _telegram_post(
        settings,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": "Usa el boton Abrir NODO del menu de Telegram para continuar.",
        },
    )


async def _send_intake_start(settings: Settings, chat_id: int | str) -> None:
    await _telegram_post(
        settings,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": "Bienvenido a NODO Registro Negocios. Escribe tu codigo de referencia para comenzar.",
        },
    )


@router.post("/telegram/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    if not settings.bot_token:
        raise ApiError("TELEGRAM_BOT_NOT_CONFIGURED", status_code=503)

    expected_secret = telegram_webhook_secret(settings.bot_token)
    if not hmac.compare_digest(secret, expected_secret):
        raise ApiError("FORBIDDEN", status_code=403)

    update = await request.json()
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return {"data": {"ok": True, "handled": False}, "request_id": _request_id(request)}

    text = _safe_text(message.get("text")).strip()
    contact = message.get("contact") or {}
    if contact:
        await _send_open_hint(settings, chat_id)
        return {"data": {"ok": True, "handled": True, "action": "open_hint_sent"}, "request_id": _request_id(request)}

    if text.startswith("/start"):
        await _send_welcome(settings, chat_id)
        return {"data": {"ok": True, "handled": True, "action": "welcome_sent"}, "request_id": _request_id(request)}

    await _send_open_hint(settings, chat_id)
    return {"data": {"ok": True, "handled": True, "action": "open_hint_sent"}, "request_id": _request_id(request)}
