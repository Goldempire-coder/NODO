from __future__ import annotations

from decimal import Decimal

from app.core.errors import ApiError


ACTIVE_AD_LIMIT = 2
METHOD_SLOT_STATUSES = frozenset({"active", "in_order"})


def require_active_ad_candidate(
    *,
    active_count: int,
    active_method_count: int,
    committed_max_total_usd: Decimal,
    candidate_max_usd: Decimal,
    declared_available_capacity_usd: Decimal,
) -> None:
    """Fail closed before an ad becomes active.

    An in-order ad keeps its method slot and advertised maximum because
    cancellation or expiry can reactivate it. This envelope does not create a
    daily reservation; order capacity remains authoritative for actual funds.
    """

    if active_method_count > 0 or active_count >= ACTIVE_AD_LIMIT:
        raise ApiError("AD_LIMIT_NOT_ALLOWED", status_code=409)
    if committed_max_total_usd + candidate_max_usd > declared_available_capacity_usd:
        raise ApiError("AD_LIMIT_NOT_ALLOWED", status_code=409)
