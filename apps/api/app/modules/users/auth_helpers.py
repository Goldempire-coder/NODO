from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from app.shared.logging_redaction import redact_mapping

REFRESH_ALLOWED_STATUSES_BY_ROLE = {
    "remitter": {"active", "restricted"},
    "business_owner": {"active", "restricted"},
    "admin": {"active"},
    "super_admin": {"active"},
    "support": {"active"},
}


def hash_ip(ip_address: str | None) -> str | None:
    if not ip_address:
        return None
    return hashlib.sha256(ip_address.encode("utf-8")).hexdigest()


def safe_debug_payload(payload: dict) -> str:
    def redact_auth_fields(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                key: "[REDACTED]"
                if "token" in str(key).lower() or str(key).lower() == "code"
                else redact_auth_fields(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [redact_auth_fields(item) for item in value]
        return value

    return json.dumps(redact_mapping(redact_auth_fields(payload)), sort_keys=True)
