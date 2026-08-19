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


def business_access_error_code(
    *,
    user: UserRecord,
    business: BusinessRecord | None,
    link: BusinessAccessLinkRecord | None,
) -> str | None:
    if user.status == "blocked":
        return "USER_BLOCKED"
    if user.status != "active":
        return "USER_NOT_ACTIVE"
    if user.role != "business_owner":
        return "SURFACE_ACCESS_DENIED"
    if business is None:
        return "BUSINESS_ACCESS_LINK_REQUIRED"
    if business.owner_user_id != user.id:
        return "SURFACE_ACCESS_DENIED"
    if business.verification_status == "blocked":
        return "BUSINESS_BLOCKED"
    if business.verification_status == "suspended":
        return "BUSINESS_SUSPENDED"
    if business.verification_status != "approved":
        return "BUSINESS_NOT_APPROVED"
    if link is None:
        return "BUSINESS_ACCESS_LINK_REQUIRED"
    if link.role_in_business != "owner":
        return "BUSINESS_ACCESS_LINK_REQUIRED"
    if link.status != "active":
        return business_access_error_for_link_status(link.status)
    if link.business_id != business.id or link.user_id != user.id:
        return "SURFACE_ACCESS_DENIED"
    if link.telegram_id_snapshot != user.telegram_id:
        return "SURFACE_ACCESS_DENIED"
    return None


def _recommended_admin_action(code: str | None, *, telegram_matches: bool | None) -> str:
    if code is None:
        return "none"
    if code == "BUSINESS_BLOCKED":
        return "unblock_business"
    if code == "BUSINESS_SUSPENDED":
        return "reactivate_business"
    if code == "BUSINESS_NOT_APPROVED":
        return "review_business_approval"
    if code == "USER_BLOCKED":
        return "unblock_owner_user"
    if code == "USER_NOT_ACTIVE":
        return "reactivate_owner_user"
    if code in {"BUSINESS_ACCESS_SUSPENDED", "BUSINESS_ACCESS_BLOCKED", "BUSINESS_ACCESS_REVOKED"}:
        return "reactivate_owner_link"
    if code == "BUSINESS_ACCESS_LINK_REQUIRED":
        return "create_owner_link"
    if telegram_matches is False:
        return "regenerate_owner_link"
    return "review_owner_binding"


def business_access_diagnostic(
    *,
    business: BusinessRecord,
    owner_user: UserRecord | None,
    links: list[BusinessAccessLinkRecord],
) -> dict[str, Any]:
    linked_user_links = [
        link
        for link in links
        if link.business_id == business.id and link.user_id == business.owner_user_id
    ]
    linked_user_links.sort(key=lambda link: (link.updated_at, link.id), reverse=True)
    owner_links = [link for link in linked_user_links if link.role_in_business == "owner"]
    active_owner_links = [link for link in owner_links if link.status == "active"]
    candidate = (active_owner_links or owner_links or linked_user_links or [None])[0]
    telegram_matches = (
        candidate.telegram_id_snapshot == owner_user.telegram_id
        if candidate is not None and owner_user is not None
        else None
    )
    if owner_user is None:
        error_code = "OWNER_USER_NOT_FOUND"
    else:
        error_code = business_access_error_code(user=owner_user, business=business, link=candidate)

    return {
        "business_status": business.verification_status,
        "business_risk_level": business.risk_level,
        "business_can_access_surface": error_code is None,
        "owner_user_id": business.owner_user_id,
        "owner_user_status": owner_user.status if owner_user is not None else "missing",
        "owner_role_valid": owner_user is not None and owner_user.role == "business_owner",
        "owner_link_id": candidate.id if candidate is not None else None,
        "owner_link_status": candidate.status if candidate is not None else "missing",
        "owner_link_role": candidate.role_in_business if candidate is not None else None,
        "owner_link_conflict": len(owner_links) > 1,
        "telegram_matches": telegram_matches,
        "blocking_reason": error_code,
        "recommended_admin_action": _recommended_admin_action(error_code, telegram_matches=telegram_matches),
    }


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
    preliminary_error = business_access_error_code(user=user, business=business, link=None)
    if preliminary_error != "BUSINESS_ACCESS_LINK_REQUIRED":
        raise ApiError(preliminary_error, status_code=409 if preliminary_error == "BUSINESS_NOT_APPROVED" else 403)
    if business is None:
        raise ApiError("BUSINESS_ACCESS_LINK_REQUIRED", status_code=403)
    assert business is not None
    link = business_repository.get_access_link_for_business_user(business_id=business.id, user_id=user.id)
    error_code = business_access_error_code(user=user, business=business, link=link)
    if error_code is not None:
        raise ApiError(error_code, status_code=409 if error_code == "BUSINESS_NOT_APPROVED" else 403)
    assert link is not None
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
    error_code = business_access_error_code(user=user, business=business, link=link)
    if error_code is not None:
        raise ApiError(error_code, status_code=409 if error_code == "BUSINESS_NOT_APPROVED" else 403)
    assert business is not None and link is not None
    return business, link
