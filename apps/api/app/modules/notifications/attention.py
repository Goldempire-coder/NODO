from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.businesses.access_control import require_active_business_access
from app.modules.orders.policy import require_remitter
from app.modules.support.models import ACTIVE_SUPPORT_STATUSES
from app.modules.users.models import UserRecord


BUSINESS_ORDER_ATTENTION_STATUSES = {
    "waiting_payment",
    "payment_reported",
    "payment_confirmed",
    "disputed",
}
CLIENT_ORDER_ATTENTION_STATUSES = {
    "waiting_payment",
    "payment_reported",
    "payment_rejected",
    "payment_confirmed",
    "delivered",
    "disputed",
}
ATTENTION_PAGE_LIMIT = 50


class SurfaceAttentionService:
    def __init__(
        self,
        *,
        business_repository,
        order_repository,
        support_repository,
    ) -> None:  # type: ignore[no-untyped-def]
        self._businesses = business_repository
        self._orders = order_repository
        self._support = support_repository

    def summary(
        self,
        *,
        user: UserRecord,
        surface: str,
    ) -> dict[str, Any]:
        support_requester_user_id: str | None
        support_business_id: str | None
        if surface == "business_mini_app":
            business, _ = require_active_business_access(
                user=user,
                business_repository=self._businesses,
            )
            orders, orders_truncated = self._orders.list_attention_for_business(
                business_id=business.id,
                statuses=BUSINESS_ORDER_ATTENTION_STATUSES,
                limit=ATTENTION_PAGE_LIMIT,
            )
            support_requester_user_id = None
            support_business_id = business.id
        elif surface == "client_mini_app":
            require_remitter(user)
            orders, orders_truncated = self._orders.list_attention_for_remitter(
                remitter_user_id=user.id,
                statuses=CLIENT_ORDER_ATTENTION_STATUSES,
                limit=ATTENTION_PAGE_LIMIT,
            )
            support_requester_user_id = user.id
            support_business_id = None
        else:
            raise ApiError("SURFACE_ACCESS_DENIED", status_code=403)

        tickets, _support_cursor = self._support.list_tickets(
            requester_user_id=support_requester_user_id,
            business_id=support_business_id,
            statuses={"waiting_user"} & ACTIVE_SUPPORT_STATUSES,
            scope=None,
            category=None,
            priority=None,
            assigned_support_user_id=None,
            cursor=None,
            limit=ATTENTION_PAGE_LIMIT + 1,
            requester_surface=surface,
        )
        support_truncated = len(tickets) > ATTENTION_PAGE_LIMIT
        tickets = tickets[:ATTENTION_PAGE_LIMIT]
        order_items = [
            {
                "kind": "order",
                "resource_id": order.id,
                "signature": f"order:{order.id}:{order.status}",
                "message": (
                    f"La orden {order.public_order_code} requiere atencion."
                    if surface == "business_mini_app"
                    else f"Tu orden {order.public_order_code} tiene una actualizacion pendiente."
                ),
                "occurred_at": order.updated_at.isoformat(),
            }
            for order in orders
        ]
        support_items = [
            {
                "kind": "support",
                "resource_id": ticket.id,
                "signature": f"support:{ticket.id}:{ticket.status}:{ticket.updated_at.isoformat()}",
                "message": "Soporte NODO actualizo tu ticket.",
                "occurred_at": ticket.updated_at.isoformat(),
            }
            for ticket in tickets
        ]
        items = sorted(
            [*order_items, *support_items],
            key=lambda item: item["occurred_at"],
            reverse=True,
        )
        return {
            "counts": {
                "orders": len(order_items),
                "support": len(support_items),
                "total": len(items),
            },
            "items": items,
            "truncated": {
                "orders": orders_truncated,
                "support": support_truncated,
            },
        }
