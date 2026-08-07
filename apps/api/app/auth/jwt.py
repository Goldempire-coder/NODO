from __future__ import annotations

import base64
import binascii
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
    if not isinstance(raw, str) or not raw:
        raise ValueError("invalid base64url segment")
    padding = "=" * (-len(raw) % 4)
    try:
        encoded = (raw + padding).encode("ascii")
        return base64.b64decode(encoded, altchars=b"-_", validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise ValueError("invalid base64url segment") from exc


def _json_dumps(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _decode_json_object(raw: str) -> dict[str, Any]:
    try:
        decoded = json.loads(_base64url_decode(raw).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ValueError("invalid jwt json") from exc
    if not isinstance(decoded, dict):
        raise ValueError("jwt json must be an object")
    return decoded


def _is_jwt_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


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
        if not isinstance(token, str):
            raise ValueError("token must be text")
        header_raw, payload_raw, signature_raw = token.split(".")
        if not header_raw or not payload_raw or not signature_raw:
            raise ValueError("jwt segments must not be empty")
        signing_input = f"{header_raw}.{payload_raw}"
        signing_bytes = signing_input.encode("ascii")
        provided_signature = _base64url_decode(signature_raw)
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise ApiError("UNAUTHENTICATED", status_code=401) from exc

    expected_signature = hmac.new(secret.encode("utf-8"), signing_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(provided_signature, expected_signature):
        raise ApiError("UNAUTHENTICATED", status_code=401)

    try:
        header = _decode_json_object(header_raw)
        payload = _decode_json_object(payload_raw)
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            raise ValueError("unsupported jwt header")
        if any(not isinstance(payload.get(claim), str) or not payload[claim] for claim in ("sub", "role", "status", "jti")):
            raise ValueError("invalid jwt string claim")
        if not _is_jwt_integer(payload.get("iat")) or not _is_jwt_integer(payload.get("exp")):
            raise ValueError("invalid jwt timestamp claim")
    except (KeyError, TypeError, ValueError) as exc:
        raise ApiError("UNAUTHENTICATED", status_code=401) from exc

    if payload["exp"] < int(time.time()):
        raise ApiError("SESSION_EXPIRED", status_code=401)
    return payload


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(refresh_token: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), refresh_token.encode("utf-8"), hashlib.sha256).hexdigest()
