from __future__ import annotations

import re
from typing import Any

FORBIDDEN_METADATA_KEYS = {
    "authorization",
    "cookie",
    "access_token",
    "refresh_token",
    "telegram_init_data",
    "bot_token",
    "business_intake_bot_token",
    "jwt_secret",
    "private_key",
    "seed_phrase",
    "mnemonic",
    "account_value",
    "storage_path",
    "signed_url",
    "destination_wallet_address",
    "wallet",
    "pin",
    "tx_hash",
    "payload",
    "telegram_payload",
    "message_body",
    "body",
}


def safe_text(value: str, max_length: int) -> str:
    cleaned = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", value)).strip()
    return cleaned[:max_length]


def sanitize_admin_notification_metadata(metadata: dict | None) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in (metadata or {}).items():
        normalized_key = str(key).lower()
        if normalized_key in FORBIDDEN_METADATA_KEYS or "token" in normalized_key or "secret" in normalized_key:
            continue
        if isinstance(value, str):
            safe[key] = safe_text(value, 160)
        elif isinstance(value, int | float | bool) or value is None:
            safe[key] = value
        else:
            safe[key] = str(type(value).__name__)
    return safe
