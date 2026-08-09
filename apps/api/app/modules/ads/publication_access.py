from __future__ import annotations

from datetime import datetime, timezone

from app.core.errors import ApiError
from app.modules.businesses.models import BusinessRecord, utc_now


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def business_publication_pause_is_active(
    business: BusinessRecord,
    *,
    current_time: datetime | None = None,
) -> bool:
    paused_until = business.ad_publication_paused_until
    if paused_until is None:
        return False
    return _as_utc(current_time or utc_now()) < _as_utc(paused_until)


def require_ad_publication_access(
    business: BusinessRecord,
    *,
    current_time: datetime | None = None,
    has_active_operational_hold: bool = False,
) -> None:
    if business.verification_status != "approved":
        raise ApiError("BUSINESS_NOT_APPROVED", status_code=409)
    if business.risk_level in {"restricted", "high_risk"}:
        raise ApiError("FORBIDDEN", status_code=403)
    if has_active_operational_hold:
        raise ApiError("BUSINESS_PUBLICATION_UNDER_REVIEW", status_code=409)
    if business_publication_pause_is_active(business, current_time=current_time):
        raise ApiError("BUSINESS_PUBLICATION_TEMPORARILY_UNAVAILABLE", status_code=409)


def business_can_receive_new_orders(
    business: BusinessRecord,
    *,
    current_time: datetime | None = None,
    has_active_operational_hold: bool = False,
) -> bool:
    return (
        business.verification_status == "approved"
        and business.risk_level not in {"restricted", "high_risk"}
        and business.is_accepting_orders
        and not has_active_operational_hold
        and not business_publication_pause_is_active(
            business,
            current_time=current_time,
        )
    )


def require_business_can_receive_new_orders(
    business: BusinessRecord,
    *,
    current_time: datetime | None = None,
    has_active_operational_hold: bool = False,
) -> None:
    if not business_can_receive_new_orders(
        business,
        current_time=current_time,
        has_active_operational_hold=has_active_operational_hold,
    ):
        raise ApiError("AD_NOT_AVAILABLE", status_code=409)
