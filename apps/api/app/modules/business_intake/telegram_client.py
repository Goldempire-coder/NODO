from __future__ import annotations

from typing import Any

import httpx

from app.core.errors import ApiError


async def telegram_api_post(bot_token: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
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


def telegram_api_post_sync(bot_token: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ApiError("TELEGRAM_BOT_SEND_FAILED", status_code=502) from exc
    if data.get("ok") is not True:
        raise ApiError("TELEGRAM_BOT_SEND_FAILED", status_code=502)
    return data


async def telegram_download_file(bot_token: str, file_id: str) -> bytes:
    file_data = await telegram_api_post(bot_token, "getFile", {"file_id": file_id})
    file_path = ((file_data.get("result") or {}).get("file_path") or "").strip()
    if not file_path or ".." in file_path.split("/"):
        raise ApiError("BOT_UPLOAD_INVALID", status_code=400)
    url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ApiError("TELEGRAM_BOT_SEND_FAILED", status_code=502) from exc
    return bytes(response.content)


async def telegram_send_message(bot_token: str, chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    await telegram_api_post(bot_token, "sendMessage", payload)


def telegram_send_message_sync(bot_token: str, chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    telegram_api_post_sync(bot_token, "sendMessage", payload)


async def telegram_set_chat_menu_button(bot_token: str, chat_id: int, text: str, web_app_url: str) -> None:
    await telegram_api_post(
        bot_token,
        "setChatMenuButton",
        {
            "chat_id": chat_id,
            "menu_button": {
                "type": "web_app",
                "text": text,
                "web_app": {"url": web_app_url},
            },
        },
    )


def telegram_set_chat_menu_button_sync(bot_token: str, chat_id: int, text: str, web_app_url: str) -> None:
    telegram_api_post_sync(
        bot_token,
        "setChatMenuButton",
        {
            "chat_id": chat_id,
            "menu_button": {
                "type": "web_app",
                "text": text,
                "web_app": {"url": web_app_url},
            },
        },
    )
