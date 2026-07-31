from __future__ import annotations

from app.core.errors import ApiError
from app.modules.orders.models import OrderRecord
from app.modules.users.models import UserRecord


def require_message_state(order: OrderRecord) -> None:
    if order.status not in {
        "waiting_payment",
        "payment_reported",
        "payment_rejected",
        "payment_confirmed",
        "delivered",
        "disputed",
    }:
        raise ApiError("ORDER_STATUS_INVALID", status_code=409)


def can_read_chat(user: UserRecord, order: OrderRecord, business_owner_id: str | None) -> bool:
    if user.role == "remitter" and user.id == order.remitter_user_id:
        return True
    if user.role == "business_owner" and business_owner_id == user.id:
        return True
    if order.status == "waiting_payment":
        return False
    if user.role in {"admin", "super_admin", "support"} and user.status == "active":
        return True
    return False


def can_write_chat(user: UserRecord, order: OrderRecord, business_owner_id: str | None) -> bool:
    if user.status != "active":
        return False
    if user.role == "remitter" and user.id == order.remitter_user_id:
        return True
    if user.role == "business_owner" and business_owner_id == user.id:
        return True
    return False


def require_chat_read(user: UserRecord, order: OrderRecord, business_owner_id: str | None) -> None:
    if not can_read_chat(user, order, business_owner_id):
        raise ApiError("ORDER_NOT_FOUND", status_code=404)


def require_chat_write(user: UserRecord, order: OrderRecord, business_owner_id: str | None) -> None:
    if not can_write_chat(user, order, business_owner_id):
        raise ApiError("ORDER_NOT_FOUND", status_code=404)
