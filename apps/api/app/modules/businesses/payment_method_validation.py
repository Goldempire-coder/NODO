from __future__ import annotations

import re

from app.core.errors import ApiError

USDT_WALLET_PATTERN = re.compile(r"^[A-Za-z0-9]{20,120}$")
USDT_NETWORK_PATTERN = re.compile(r"^[A-Z0-9 _-]{2,32}$")


def normalize_payment_account(*, method_type: str, account_value: str | None) -> str:
    raw_value = account_value or ""
    if method_type == "usdt_trc20":
        normalized = "".join(raw_value.strip().split())
        if not USDT_WALLET_PATTERN.fullmatch(normalized):
            raise ApiError("PAYMENT_METHOD_INVALID", status_code=400)
        return normalized
    normalized = " ".join(raw_value.strip().split())
    if len(normalized) < 3:
        raise ApiError("PAYMENT_METHOD_INVALID", status_code=400)
    return normalized


def normalize_payment_network(*, method_type: str, network: str | None) -> str | None:
    if method_type != "usdt_trc20":
        return None
    normalized = " ".join((network or "").strip().upper().split())
    if not normalized:
        return None
    if not USDT_NETWORK_PATTERN.fullmatch(normalized):
        raise ApiError("PAYMENT_METHOD_INVALID", status_code=400)
    return normalized


def normalize_payment_holder(holder_name: str) -> str:
    holder = " ".join(holder_name.strip().split())
    if len(holder) < 2:
        raise ApiError("PAYMENT_METHOD_INVALID", status_code=400)
    return holder
