from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

from app.core.errors import ApiError


def parse_stripe_webhook_event(*, raw_body: bytes, signature_header: str | None, webhook_secret: str | None) -> dict[str, Any]:
    if not _verify_stripe_signature(raw_body=raw_body, signature_header=signature_header, webhook_secret=webhook_secret):
        raise ApiError("STRIPE_SIGNATURE_INVALID", status_code=400)
    try:
        event = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ApiError("VALIDATION_ERROR", status_code=422) from exc
    if not isinstance(event, dict):
        raise ApiError("VALIDATION_ERROR", status_code=422)
    return event


def _verify_stripe_signature(*, raw_body: bytes, signature_header: str | None, webhook_secret: str | None) -> bool:
    if not webhook_secret or not signature_header:
        return False
    parts = dict(part.split("=", 1) for part in signature_header.split(",") if "=" in part)
    timestamp = parts.get("t")
    expected = parts.get("v1")
    if not timestamp or not expected:
        return False
    signed_payload = f"{timestamp}.".encode("utf-8") + raw_body
    computed = hmac.new(webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    try:
        if abs(int(time.time()) - int(timestamp)) > 300:
            return False
    except ValueError:
        return False
    return hmac.compare_digest(computed, expected)
