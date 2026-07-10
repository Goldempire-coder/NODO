from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.business_intake.models import INTAKE_ALLOWED_MIME_TYPES

MAX_BOT_TEXT_LENGTH = 500


def clean_bot_text(value: Any, *, min_length: int = 1, max_length: int = MAX_BOT_TEXT_LENGTH) -> str:
    if not isinstance(value, str):
        raise ApiError("BOT_INPUT_INVALID", status_code=400)
    cleaned = " ".join(value.strip().split())
    if len(cleaned) < min_length or len(cleaned) > max_length:
        raise ApiError("BOT_INPUT_INVALID", status_code=400)
    return cleaned


def message_has_forbidden_media(message: dict[str, Any]) -> bool:
    return any(key in message for key in ("video", "audio", "voice", "animation", "video_note"))


def message_has_allowed_file(message: dict[str, Any]) -> bool:
    return "photo" in message or "document" in message


def extract_telegram_file_info(message: dict[str, Any]) -> dict[str, Any]:
    if "photo" in message:
        photos = message.get("photo")
        if not isinstance(photos, list) or not photos:
            raise ApiError("BOT_UPLOAD_INVALID", status_code=400)
        photo = max(photos, key=lambda item: int(item.get("file_size") or 0))
        return {
            "file_id": clean_bot_text(photo.get("file_id"), max_length=256),
            "file_unique_id": photo.get("file_unique_id"),
            "file_name": "telegram-photo.jpg",
            "mime_type": "image/jpeg",
            "size_bytes": int(photo["file_size"]) if photo.get("file_size") is not None else None,
            "document_kind": "local_image",
        }

    document = message.get("document")
    if not isinstance(document, dict):
        raise ApiError("BOT_UPLOAD_INVALID", status_code=400)
    mime_type = clean_bot_text(document.get("mime_type"), max_length=120)
    if mime_type not in INTAKE_ALLOWED_MIME_TYPES:
        raise ApiError("BOT_UPLOAD_INVALID", status_code=400)
    return {
        "file_id": clean_bot_text(document.get("file_id"), max_length=256),
        "file_unique_id": document.get("file_unique_id"),
        "file_name": clean_bot_text(document.get("file_name") or "telegram-document", max_length=160),
        "mime_type": mime_type,
        "size_bytes": int(document["file_size"]) if document.get("file_size") is not None else None,
        "document_kind": "other_reference",
    }
