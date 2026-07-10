from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

from app.core.errors import ApiError


@dataclass(frozen=True)
class TelegramUserData:
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    auth_date: int


def validate_telegram_init_data(init_data: str, bot_token: str, max_age_seconds: int, now: int | None = None) -> TelegramUserData:
    if not init_data:
        raise ApiError("TELEGRAM_INIT_DATA_INVALID", status_code=401)

    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise ApiError("TELEGRAM_INIT_DATA_INVALID", status_code=401)

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise ApiError("TELEGRAM_INIT_DATA_INVALID", status_code=401)

    try:
        auth_date = int(pairs["auth_date"])
    except (KeyError, ValueError) as exc:
        raise ApiError("TELEGRAM_INIT_DATA_INVALID", status_code=401) from exc

    current_time = int(time.time()) if now is None else now
    if current_time - auth_date > max_age_seconds:
        raise ApiError("TELEGRAM_INIT_DATA_EXPIRED", status_code=401)

    try:
        user_payload = json.loads(pairs["user"])
        telegram_id = int(user_payload["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ApiError("TELEGRAM_INIT_DATA_INVALID", status_code=401) from exc

    return TelegramUserData(
        telegram_id=telegram_id,
        username=user_payload.get("username"),
        first_name=user_payload.get("first_name"),
        last_name=user_payload.get("last_name"),
        auth_date=auth_date,
    )
