from __future__ import annotations

from app.core.errors import ApiError
from app.modules.orders.models import OrderRecord
from app.modules.users.models import UserRecord


def require_remitter(user: UserRecord) -> None:
    if user.role != "remitter" or user.status != "active":
        raise ApiError("FORBIDDEN", status_code=403)


def require_order_owner(user: UserRecord, order: OrderRecord) -> None:
    if order.remitter_user_id != user.id:
        raise ApiError("ORDER_NOT_FOUND", status_code=404)


def require_business_owner(user: UserRecord) -> None:
    if user.role != "business_owner" or user.status != "active":
        raise ApiError("FORBIDDEN", status_code=403)
