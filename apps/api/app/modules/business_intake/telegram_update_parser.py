from __future__ import annotations

from typing import Any

from app.core.errors import ApiError


def empty_telegram_response() -> dict[str, Any]:
    return {
        "ok": True,
        "intake_id": None,
        "status": None,
        "last_step": None,
        "duplicate_update": False,
        "handled": False,
    }


def telegram_message_context(update: dict[str, Any]) -> dict[str, Any] | None:
    message = update.get("message") or update.get("edited_message") or {}
    if not isinstance(message, dict) or not message:
        return None

    update_id = update.get("update_id")
    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    chat_id = chat.get("id")
    telegram_user_id = sender.get("id")
    if update_id is None or chat_id is None or telegram_user_id is None:
        raise ApiError("BOT_INPUT_INVALID", status_code=400)

    text = message.get("text")
    return {
        "message": message,
        "update_id": int(update_id),
        "chat_id": int(chat_id),
        "telegram_user_id": int(telegram_user_id),
        "text": text,
        "normalized_text": text.strip().lower() if isinstance(text, str) else "",
    }
