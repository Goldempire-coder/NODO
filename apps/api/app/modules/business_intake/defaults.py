from __future__ import annotations

DEFAULT_MIN_AMOUNT_USD = "20.00"
DEFAULT_MAX_AMOUNT_USD = "100.00"
DEFAULT_DAILY_LIMIT_USD = "1000.00"
DEFAULT_SCHEDULE_TEXT = "El negocio opera con el boton online/offline de NODO."


def default_intake_limits() -> dict[str, str]:
    return {
        "min_amount_usd": DEFAULT_MIN_AMOUNT_USD,
        "max_amount_usd": DEFAULT_MAX_AMOUNT_USD,
        "daily_limit_usd": DEFAULT_DAILY_LIMIT_USD,
    }
