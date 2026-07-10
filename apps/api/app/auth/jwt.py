from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from typing import Any

from app.core.errors import ApiError


def _base64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _base64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("ascii"))


def _json_dumps(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def create_access_token(*, user_id: str, role: str, status: str, secret: str, ttl_seconds: int) -> tuple[str, str, int]:
    now = int(time.time())
    expires_at = now + ttl_seconds
    jti = str(uuid.uuid4())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "role": role,
        "status": status,
        "iat": now,
        "exp": expires_at,
        "jti": jti,
    }
    signing_input = f"{_base64url_encode(_json_dumps(header))}.{_base64url_encode(_json_dumps(payload))}"
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_base64url_encode(signature)}", jti, expires_at


def decode_access_token(token: str, secret: str) -> dict[str, Any]:
    try:
        header_raw, payload_raw, signature_raw = token.split(".")
    except ValueError as exc:
        raise ApiError("UNAUTHENTICATED", status_code=401) from exc

    signing_input = f"{header_raw}.{payload_raw}"
    expected_signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    if not hmac.compare_digest(_base64url_decode(signature_raw), expected_signature):
        raise ApiError("UNAUTHENTICATED", status_code=401)

    try:
        payload = json.loads(_base64url_decode(payload_raw))
    except (json.JSONDecodeError, ValueError) as exc:
        raise ApiError("UNAUTHENTICATED", status_code=401) from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise ApiError("SESSION_EXPIRED", status_code=401)
    return payload


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(refresh_token: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), refresh_token.encode("utf-8"), hashlib.sha256).hexdigest()
