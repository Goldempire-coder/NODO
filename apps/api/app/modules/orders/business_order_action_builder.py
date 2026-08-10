from __future__ import annotations

from typing import Any

from app.modules.orders.models import OrderRecord
from app.modules.orders.serializers import business_order_payload
from app.modules.users.models import UserRecord


def delivered_state_metadata(*, idempotency_key: str) -> dict[str, Any]:
    return {"idempotency_key": idempotency_key}


def delivered_audit_event(
    *,
    user: UserRecord,
    order: OrderRecord,
    reason: str | None,
    request_id: str,
) -> dict[str, Any]:
    return {
        "event_type": "order_delivered",
        "actor_user_id": user.id,
        "actor_role": user.role,
        "resource_type": "order",
        "resource_id": order.id,
        "request_id": request_id,
        "metadata_json": {"reason": reason},
    }


def delivered_response(*, order: OrderRecord, disclaimer: str) -> dict[str, Any]:
    return {"order": business_order_payload(order), "disclaimer": disclaimer}
