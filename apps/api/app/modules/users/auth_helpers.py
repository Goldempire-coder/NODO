from __future__ import annotations

import hashlib
import json


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
    return json.dumps({key: "[REDACTED]" if "token" in key else value for key, value in payload.items()}, sort_keys=True)
