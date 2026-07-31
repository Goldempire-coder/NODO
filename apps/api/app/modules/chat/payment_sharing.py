from __future__ import annotations

import re


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


def redact_configured_payment_account(body: str, account_value: str) -> str:
    pattern = configured_payment_account_pattern(account_value)
    if pattern is None:
        return body
    return pattern.sub("[cuenta de pago configurada]", body)
