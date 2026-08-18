from __future__ import annotations

import hashlib
import hmac
from typing import Any

import httpx
from fastapi import APIRouter, Header, Request

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
    fallback_text = "Bienvenido a NODO. Abre NODO desde el menu de Telegram para comenzar."
    try:
        await _telegram_post(
            settings,
            "sendPhoto",
            {
                "chat_id": chat_id,
                "photo": settings.telegram_welcome_image_url,
                "caption": "Abre NODO desde el menu de Telegram para comenzar.",
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
            "text": "Abre NODO desde el menu de Telegram para continuar.",
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


async def _handle_telegram_webhook(*, provided_secret: str | None, request: Request) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    if not settings.bot_token:
        raise ApiError("TELEGRAM_BOT_NOT_CONFIGURED", status_code=503)

    expected_secret = telegram_webhook_secret(settings.bot_token)
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


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    telegram_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
    nodo_secret: str | None = Header(default=None, alias="X-NODO-Bot-Webhook-Secret"),
) -> dict[str, Any]:
    return await _handle_telegram_webhook(provided_secret=telegram_secret or nodo_secret, request=request)


@router.post("/telegram/webhook/{legacy_secret}", deprecated=True)
async def legacy_telegram_webhook(legacy_secret: str, request: Request) -> dict[str, Any]:
    return await _handle_telegram_webhook(provided_secret=legacy_secret, request=request)
