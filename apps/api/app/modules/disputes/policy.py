from __future__ import annotations

from app.core.errors import ApiError
from app.modules.disputes.models import ALLOWED_DISPUTE_ORDER_STATES, DISPUTE_REASONS, DISPUTE_RESOLUTION_TYPES
from app.modules.orders.models import OrderRecord
from app.modules.users.models import UserRecord


def require_dispute_reason(reason: str) -> None:
    if reason not in DISPUTE_REASONS:
        raise ApiError("DISPUTE_REASON_REQUIRED", status_code=400)


def require_dispute_order_state(order: OrderRecord) -> None:
    if order.status not in ALLOWED_DISPUTE_ORDER_STATES:
        raise ApiError("ORDER_STATUS_INVALID", status_code=409)


def can_open_dispute(user: UserRecord, order: OrderRecord, business_owner_id: str | None) -> bool:
    if user.status != "active":
        return False
    if user.role == "remitter" and user.id == order.remitter_user_id:
        return True
    if user.role == "business_owner" and user.id == business_owner_id:
        return True
    return False


def require_dispute_open_permission(user: UserRecord, order: OrderRecord, business_owner_id: str | None) -> None:
    if not can_open_dispute(user, order, business_owner_id):
        raise ApiError("ORDER_NOT_FOUND", status_code=404)


def require_admin_dispute_read(user: UserRecord) -> None:
    if user.role not in {"admin", "super_admin", "support"} or user.status != "active":
        raise ApiError("FORBIDDEN", status_code=403)


def require_admin_dispute_resolve(user: UserRecord) -> None:
    if user.role not in {"admin", "super_admin"} or user.status != "active":
        raise ApiError("FORBIDDEN", status_code=403)


def require_dispute_resolution_type(resolution_type: str) -> None:
    if resolution_type not in DISPUTE_RESOLUTION_TYPES:
        raise ApiError("DISPUTE_RESOLUTION_NOT_ALLOWED", status_code=400)


def require_dispute_resolution_reason(reason: str) -> None:
    if not reason or not reason.strip():
        raise ApiError("DISPUTE_RESOLUTION_REASON_REQUIRED", status_code=400)
