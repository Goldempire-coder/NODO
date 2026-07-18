from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from functools import lru_cache

ADMIN_PASSWORD_MIN_LENGTH = 10
ADMIN_PASSWORD_MAX_LENGTH = 128
ADMIN_PASSWORD_ITERATIONS = 310_000
_USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._@+-]{2,126}[a-z0-9]$")


def normalize_admin_username(username: str) -> str:
    normalized = " ".join(username.strip().lower().split())
    if not _USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("invalid admin username")
    return normalized


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode((value + "=" * (-len(value) % 4)).encode("ascii"))


def hash_admin_password(password: str) -> str:
    if not isinstance(password, str) or not (ADMIN_PASSWORD_MIN_LENGTH <= len(password) <= ADMIN_PASSWORD_MAX_LENGTH):
        raise ValueError("invalid admin password")
    salt = secrets.token_bytes(24)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ADMIN_PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${ADMIN_PASSWORD_ITERATIONS}${_b64(salt)}${_b64(digest)}"


@lru_cache(maxsize=1)
def dummy_admin_password_hash() -> str:
    salt = b"nodo-admin-login-dummy"
    digest = hashlib.pbkdf2_hmac("sha256", b"nodo-admin-password-timing", salt, ADMIN_PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${ADMIN_PASSWORD_ITERATIONS}${_b64(salt)}${_b64(digest)}"


def verify_admin_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt_raw, digest_raw = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = _unb64(salt_raw)
        expected = _unb64(digest_raw)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)
