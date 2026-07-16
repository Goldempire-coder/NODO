from __future__ import annotations

import hashlib
import hmac
import secrets

from app.core.errors import ApiError

PIN_HASH_ALGORITHM = "pbkdf2_sha256"
PIN_HASH_ITERATIONS = 120_000
PIN_LENGTH_MIN = 4
PIN_LENGTH_MAX = 6


def normalize_pin(pin: str) -> str:
    normalized = pin.strip()
    if not normalized.isdigit() or not PIN_LENGTH_MIN <= len(normalized) <= PIN_LENGTH_MAX:
        raise ApiError("BUSINESS_PIN_INVALID", status_code=400)
    return normalized


def hash_pin(pin: str) -> str:
    normalized = normalize_pin(pin)
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        normalized.encode("utf-8"),
        salt.encode("utf-8"),
        PIN_HASH_ITERATIONS,
    ).hex()
    return f"{PIN_HASH_ALGORITHM}${PIN_HASH_ITERATIONS}${salt}${digest}"


def verify_pin(pin: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    normalized = normalize_pin(pin)
    try:
        algorithm, iterations_raw, salt, expected = stored_hash.split("$", 3)
        iterations = int(iterations_raw)
    except ValueError:
        return False
    if algorithm != PIN_HASH_ALGORITHM or iterations <= 0:
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        normalized.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(actual, expected)
