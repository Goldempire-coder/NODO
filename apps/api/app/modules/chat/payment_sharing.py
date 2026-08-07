from __future__ import annotations

import re


OFFICIAL_PAYMENT_DETAILS_IDEMPOTENCY_PREFIX = "official_payment_details:"
_CONTACT_TOKEN_CHARS = r"A-Za-z0-9._%+@-"
_CONTACT_SUFFIX = r"(?![A-Za-z0-9_%+@-]|\.(?=[A-Za-z0-9]))"


def configured_payment_account_pattern(account_value: str) -> re.Pattern[str] | None:
    clean = account_value.strip()
    if not clean:
        return None
    return re.compile(
        rf"(?<![{_CONTACT_TOKEN_CHARS}]){re.escape(clean)}{_CONTACT_SUFFIX}",
        re.IGNORECASE,
    )


def contains_configured_payment_account(body: str | None, account_value: str) -> bool:
    pattern = configured_payment_account_pattern(account_value)
    return bool(pattern and pattern.search(body or ""))


def official_payment_details_idempotency_key(idempotency_key: str) -> str:
    return f"{OFFICIAL_PAYMENT_DETAILS_IDEMPOTENCY_PREFIX}{idempotency_key}"


def is_official_payment_details_idempotency_key(idempotency_key: str | None) -> bool:
    return bool(
        idempotency_key
        and idempotency_key.startswith(OFFICIAL_PAYMENT_DETAILS_IDEMPOTENCY_PREFIX)
    )
