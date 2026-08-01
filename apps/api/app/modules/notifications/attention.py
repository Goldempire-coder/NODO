from __future__ import annotations

import hashlib
from typing import Any

from app.core.errors import ApiError
from app.modules.businesses.access_control import require_active_business_access
from app.modules.notifications.schemas import AttentionAcknowledgeRequest
from app.modules.orders.policy import require_remitter
from app.modules.support.models import ACTIVE_SUPPORT_STATUSES
from app.modules.users.models import UserRecord


BUSINESS_ORDER_ATTENTION_STATUSES = {
    "waiting_payment",
    "payment_reported",
    "payment_confirmed",
    "disputed",
}
BUSINESS_ORDER_CANCEL_ATTENTION_REASONS = {
    "remitter_cancelled_before_payment",
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
        chat_repository,
        read_repository,
    ) -> None:  # type: ignore[no-untyped-def]
        self._businesses = business_repository
        self._orders = order_repository
        self._support = support_repository
        self._chat = chat_repository
        self._read = read_repository

    def summary(
        self,
        *,
        user: UserRecord,
        surface: str,
    ) -> dict[str, Any]:
        items, orders_truncated, support_truncated = self._visible_attention_items(user=user, surface=surface)
        return {
            "counts": {
                "orders": len([item for item in items if item["kind"] == "order"]),
                "support": len([item for item in items if item["kind"] == "support"]),
                "total": len(items),
            },
            "items": items,
            "truncated": {
                "orders": orders_truncated,
                "support": support_truncated,
            },
        }

    def acknowledge(
        self,
        *,
        user: UserRecord,
        surface: str,
        payload: AttentionAcknowledgeRequest,
    ) -> dict[str, bool]:
        items, _orders_truncated, _support_truncated = self._collect_attention_items(
            user=user,
            surface=surface,
            filter_acknowledged=False,
        )
        item = next(
            (
                candidate
                for candidate in items
                if candidate["kind"] == payload.kind and candidate["resource_id"] == str(payload.resource_id)
            ),
            None,
        )
        if item is None:
            raise ApiError("ATTENTION_ITEM_NOT_FOUND", status_code=404)
        if item["signature"] != payload.signature:
            raise ApiError("ATTENTION_SIGNATURE_STALE", status_code=409)
        self._read.mark_acknowledged(
            user_id=user.id,
            surface=surface,
            resource_kind=payload.kind,
            resource_id=str(payload.resource_id),
            signature=payload.signature,
        )
        return {"acknowledged": True}

    def _visible_attention_items(self, *, user: UserRecord, surface: str) -> tuple[list[dict[str, Any]], bool, bool]:
        return self._collect_attention_items(user=user, surface=surface, filter_acknowledged=True)

    def _collect_attention_items(
        self,
        *,
        user: UserRecord,
        surface: str,
        filter_acknowledged: bool,
    ) -> tuple[list[dict[str, Any]], bool, bool]:
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
                cancel_reasons=BUSINESS_ORDER_CANCEL_ATTENTION_REASONS,
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
        latest_order_messages = self._chat.latest_counterparty_messages_for_orders(
            order_ids=[order.id for order in orders],
            recipient_user_id=user.id,
            surface=surface,
        )
        latest_support_messages = self._support.latest_participant_messages_for_tickets(
            ticket_ids=[ticket.id for ticket in tickets],
            recipient_user_id=user.id,
        )
        order_items = [
            {
                "kind": "order",
                "resource_id": order.id,
                "signature": _signature(
                    "order",
                    order.id,
                    order.status,
                    latest_order_messages[order.id].id if order.id in latest_order_messages else "no-message",
                ),
                "message": _order_attention_message(order=order, surface=surface),
                "occurred_at": _max_iso(
                    order.updated_at,
                    latest_order_messages[order.id].created_at if order.id in latest_order_messages else None,
                ),
            }
            for order in orders
        ]
        support_items = [
            {
                "kind": "support",
                "resource_id": ticket.id,
                "signature": _signature(
                    "support",
                    ticket.id,
                    ticket.status,
                    latest_support_messages[ticket.id].id if ticket.id in latest_support_messages else ticket.updated_at.isoformat(),
                ),
                "message": "Soporte NODO actualizo tu ticket.",
                "occurred_at": _max_iso(
                    ticket.updated_at,
                    latest_support_messages[ticket.id].created_at if ticket.id in latest_support_messages else None,
                ),
            }
            for ticket in tickets
        ]
        items = [*order_items, *support_items]
        if filter_acknowledged:
            acknowledged = self._read.get_acknowledged_signatures(
                user_id=user.id,
                surface=surface,
                resources=[(item["kind"], item["resource_id"]) for item in items],
            )
            items = [
                item
                for item in items
                if acknowledged.get((item["kind"], item["resource_id"])) != item["signature"]
            ]
        items = sorted(
            items,
            key=lambda item: item["occurred_at"],
            reverse=True,
        )
        return items, orders_truncated, support_truncated


def _signature(*parts: str) -> str:
    payload = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:32]


def _order_attention_message(*, order, surface: str) -> str:  # type: ignore[no-untyped-def]
    if surface == "business_mini_app":
        if order.status == "cancelled" and order.cancel_reason == "remitter_cancelled_before_payment":
            return f"La orden {order.public_order_code} fue cancelada por el cliente."
        return f"La orden {order.public_order_code} requiere atencion."
    return f"Tu orden {order.public_order_code} tiene una actualizacion pendiente."


def _max_iso(first, second=None) -> str:  # type: ignore[no-untyped-def]
    if second is not None and second > first:
        return second.isoformat()
    return first.isoformat()
