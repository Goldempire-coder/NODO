from __future__ import annotations

import hashlib
import secrets


ADMIN_TELEGRAM_LINK_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ADMIN_TELEGRAM_LINK_CODE_LENGTH = 12


def generate_admin_telegram_link_code() -> str:
    return "".join(secrets.choice(ADMIN_TELEGRAM_LINK_CODE_ALPHABET) for _ in range(ADMIN_TELEGRAM_LINK_CODE_LENGTH))


def normalize_admin_telegram_link_code(value: str) -> str:
    return value.strip().upper().replace("-", "").replace(" ", "")


def hash_admin_telegram_link_code(value: str) -> str:
    return hashlib.sha256(normalize_admin_telegram_link_code(value).encode("utf-8")).hexdigest()


def hash_admin_alert_telegram_id(telegram_id: int) -> str:
    return hashlib.sha256(str(telegram_id).encode("utf-8")).hexdigest()[:16]
