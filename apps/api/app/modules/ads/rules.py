from __future__ import annotations

from decimal import Decimal

from app.core.errors import ApiError


def calculate_required_credits(amount_max_usd: Decimal) -> int:
    if amount_max_usd <= Decimal("100"):
        return 1
    if amount_max_usd <= Decimal("500"):
        return 2
    if amount_max_usd <= Decimal("2000"):
        return 3
    raise ApiError("AD_AMOUNT_TOO_HIGH", status_code=400)
