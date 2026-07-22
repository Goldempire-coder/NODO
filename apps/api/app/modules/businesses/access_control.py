from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.businesses.models import BusinessAccessLinkRecord, BusinessRecord, utc_now
from app.modules.users.models import UserRecord


BUSINESS_CAPABILITIES = [
    "business.dashboard.view",
    "business.payment_methods.view",
    "business.ads.create",
    "business.ads.manage",
    "business.orders.view",
    "business.orders.confirm_payment",
    "business.orders.reject_payment_report",
    "business.orders.mark_delivered",
    "business.chat.use",
    "business.credits.view",
    "business.referrals.view",
]


def business_access_error_for_link_status(status: str) -> str:
    return {
        "suspended": "BUSINESS_ACCESS_SUSPENDED",
        "blocked": "BUSINESS_ACCESS_BLOCKED",
        "revoked": "BUSINESS_ACCESS_REVOKED",
    }.get(status, "BUSINESS_ACCESS_LINK_REQUIRED")


def business_access_state_for_error(code: str) -> str:
    return {
        "BUSINESS_ACCESS_LINK_REQUIRED": "no_business_link",
        "BUSINESS_ACCESS_SUSPENDED": "link_suspended",
        "BUSINESS_ACCESS_BLOCKED": "link_blocked",
        "BUSINESS_ACCESS_REVOKED": "link_revoked",
        "BUSINESS_NOT_APPROVED": "business_not_approved",
        "BUSINESS_SUSPENDED": "business_suspended",
        "BUSINESS_BLOCKED": "business_blocked",
        "USER_BLOCKED": "user_blocked",
        "USER_NOT_ACTIVE": "user_not_active",
    }.get(code, "surface_access_denied")


def public_user_for_surface(user: UserRecord) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "role": user.role,
        "status": user.status,
    }


def public_business_for_surface(business: BusinessRecord, link: BusinessAccessLinkRecord | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": business.id,
        "owner_user_id": business.owner_user_id,
        "business_name": business.business_name,
        "country": business.country,
        "verification_status": business.verification_status,
        "min_order_amount_usd": f"{business.min_order_amount_usd:.2f}",
        "max_order_amount_usd": f"{business.max_order_amount_usd:.2f}",
        "daily_limit_usd": f"{business.daily_limit_usd:.2f}",
        "active_order_limit": business.active_order_limit,
        "approved_at": business.approved_at.isoformat() if business.approved_at else None,
    }
    if link is not None:
        pin_locked = link.business_pin_locked_until is not None and link.business_pin_locked_until > utc_now()
        pin_unlocked = link.business_pin_unlocked_until is not None and link.business_pin_unlocked_until > utc_now()
        payload["access_link"] = {
            "id": link.id,
            "status": link.status,
            "role_in_business": link.role_in_business,
            "linked_at": link.linked_at.isoformat(),
            "pin_required": True,
            "pin_configured": link.business_pin_hash is not None,
            "pin_unlocked": pin_unlocked,
            "pin_locked_until": link.business_pin_locked_until.isoformat() if pin_locked else None,
            "pin_unlocked_until": link.business_pin_unlocked_until.isoformat() if pin_unlocked else None,
        }
    return payload


def evaluate_business_access(
    *,
    user: UserRecord,
    business: BusinessRecord | None,
    business_repository,
) -> tuple[BusinessRecord, BusinessAccessLinkRecord]:
    if user.status == "blocked":
        raise ApiError("USER_BLOCKED", status_code=403)
    if user.status != "active":
        raise ApiError("USER_NOT_ACTIVE", status_code=403)
    if user.role != "business_owner":
        raise ApiError("SURFACE_ACCESS_DENIED", status_code=403)
    if business is None:
        raise ApiError("BUSINESS_ACCESS_LINK_REQUIRED", status_code=403)
    if business.owner_user_id != user.id:
        raise ApiError("SURFACE_ACCESS_DENIED", status_code=403)
    if business.verification_status == "blocked":
        raise ApiError("BUSINESS_BLOCKED", status_code=403)
    if business.verification_status == "suspended":
        raise ApiError("BUSINESS_SUSPENDED", status_code=403)
    if business.verification_status != "approved":
        raise ApiError("BUSINESS_NOT_APPROVED", status_code=409)
    link = business_repository.get_access_link_for_business_user(business_id=business.id, user_id=user.id)
    if link is None:
        raise ApiError("BUSINESS_ACCESS_LINK_REQUIRED", status_code=403)
    if link.status != "active":
        raise ApiError(business_access_error_for_link_status(link.status), status_code=403)
    if link.telegram_id_snapshot != user.telegram_id:
        raise ApiError("SURFACE_ACCESS_DENIED", status_code=403)
    return business, link


def require_active_business_access(*, user: UserRecord, business_repository) -> tuple[BusinessRecord, BusinessAccessLinkRecord]:
    if hasattr(business_repository, "get_business_with_latest_access_link_for_owner"):
        business, link = business_repository.get_business_with_latest_access_link_for_owner(user.id)
        return evaluate_business_access_link(user=user, business=business, link=link)
    business = business_repository.get_active_business_for_owner(user.id)
    return evaluate_business_access(user=user, business=business, business_repository=business_repository)


def evaluate_business_access_link(
    *,
    user: UserRecord,
    business: BusinessRecord | None,
    link: BusinessAccessLinkRecord | None,
) -> tuple[BusinessRecord, BusinessAccessLinkRecord]:
    if user.status == "blocked":
        raise ApiError("USER_BLOCKED", status_code=403)
    if user.status != "active":
        raise ApiError("USER_NOT_ACTIVE", status_code=403)
    if user.role != "business_owner":
        raise ApiError("SURFACE_ACCESS_DENIED", status_code=403)
    if business is None:
        raise ApiError("BUSINESS_ACCESS_LINK_REQUIRED", status_code=403)
    if business.owner_user_id != user.id:
        raise ApiError("SURFACE_ACCESS_DENIED", status_code=403)
    if business.verification_status == "blocked":
        raise ApiError("BUSINESS_BLOCKED", status_code=403)
    if business.verification_status == "suspended":
        raise ApiError("BUSINESS_SUSPENDED", status_code=403)
    if business.verification_status != "approved":
        raise ApiError("BUSINESS_NOT_APPROVED", status_code=409)
    if link is None:
        raise ApiError("BUSINESS_ACCESS_LINK_REQUIRED", status_code=403)
    if link.status != "active":
        raise ApiError(business_access_error_for_link_status(link.status), status_code=403)
    if link.business_id != business.id or link.user_id != user.id:
        raise ApiError("SURFACE_ACCESS_DENIED", status_code=403)
    if link.telegram_id_snapshot != user.telegram_id:
        raise ApiError("SURFACE_ACCESS_DENIED", status_code=403)
    return business, link
