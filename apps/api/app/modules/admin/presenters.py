from __future__ import annotations

from typing import Any

SENSITIVE_KEYS = {"storage_path", "account_value", "token", "secret", "payment_instructions_snapshot"}


def mask_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "[masked]" if key in SENSITIVE_KEYS else mask_sensitive(item) for key, item in value.items()}
    if isinstance(value, list):
        return [mask_sensitive(item) for item in value]
    return value


def iso(value: Any) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else value
