from __future__ import annotations


def normalize_referral_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None
