from __future__ import annotations

from app.core.errors import ApiError
from app.modules.businesses.models import BusinessRecord


ACCESS_LINK_STATUS_EVENTS = {
    "active": "business_access_reactivated",
    "suspended": "business_access_suspended",
    "revoked": "business_access_unlinked",
    "blocked": "business_access_blocked",
}


def required_admin_reason(reason: str) -> str:
    reason = reason.strip()
    if not reason:
        raise ApiError("ADMIN_REASON_REQUIRED", status_code=400)
    return reason


def require_idempotency_key(idempotency_key: str | None) -> None:
    if not idempotency_key:
        raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)


def require_business_can_receive_access_link(business: BusinessRecord) -> None:
    if business.verification_status == "blocked":
        raise ApiError("BUSINESS_BLOCKED", status_code=403)
    if business.verification_status == "suspended":
        raise ApiError("BUSINESS_SUSPENDED", status_code=403)
    if business.verification_status != "approved":
        raise ApiError("BUSINESS_NOT_APPROVED", status_code=409)


def event_type_for_access_link_status(status: str) -> str:
    return ACCESS_LINK_STATUS_EVENTS[status]
