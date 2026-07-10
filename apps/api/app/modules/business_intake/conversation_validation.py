from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.errors import ApiError

MAX_BOT_TEXT_LENGTH = 500


def validated_amount_range(min_amount_usd: str, max_amount_usd: str) -> tuple[str, str]:
    try:
        min_amount = Decimal(min_amount_usd)
        max_amount = Decimal(max_amount_usd)
    except (InvalidOperation, ValueError) as exc:
        raise ApiError("VALIDATION_ERROR", status_code=422) from exc
    if min_amount <= 0 or max_amount < min_amount:
        raise ApiError("VALIDATION_ERROR", status_code=422)
    return str(min_amount), str(max_amount)


def clean_text(value: Any, *, min_length: int = 1, max_length: int = MAX_BOT_TEXT_LENGTH) -> str:
    if not isinstance(value, str):
        raise ApiError("BOT_INPUT_INVALID", status_code=400)
    cleaned = " ".join(value.strip().split())
    if len(cleaned) < min_length or len(cleaned) > max_length:
        raise ApiError("BOT_INPUT_INVALID", status_code=400)
    return cleaned


def split_clean_list(value: str) -> list[str]:
    items = [" ".join(item.strip().split()) for item in value.replace("\n", ",").split(",")]
    cleaned = [item for item in items if item]
    if not cleaned or any(len(item) > 80 for item in cleaned):
        raise ApiError("BOT_INPUT_INVALID", status_code=400)
    return cleaned[:20]


def normalize_operation(value: str) -> str:
    normalized = value.strip().lower().replace("ÃƒÂ¡", "a")
    if normalized in {"buy_usd", "compra", "comprar", "compra usd", "compro usd"}:
        return "buy_usd"
    if normalized in {"sell_usd", "vende", "vender", "vende usd", "vendo usd"}:
        return "sell_usd"
    if normalized in {"both", "ambas", "ambos", "compra y vende", "comprar y vender"}:
        return "both"
    raise ApiError("BOT_INPUT_INVALID", status_code=400)


def normalize_methods(value: str) -> list[str]:
    normalized = value.lower().replace("-", " ").replace("_", " ")
    methods: list[str] = []
    if "zelle" in normalized:
        methods.append("zelle")
    if "usdt" in normalized or "trc20" in normalized:
        methods.append("usdt_trc20")
    if not methods:
        raise ApiError("BOT_INPUT_INVALID", status_code=400)
    return methods
