from __future__ import annotations

from typing import Any

from app.modules.orders.models import OrderRecord


def dispute_payload(dispute) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    return {
        "id": dispute.id,
        "order_id": dispute.order_id,
        "status": dispute.status,
        "reason": dispute.reason,
        "description": dispute.description,
        "previous_order_status": dispute.previous_order_status,
        "resolution_type": dispute.resolution_type,
        "resolution_reason": dispute.resolution_reason,
        "resolved_at": dispute.resolved_at.isoformat() if dispute.resolved_at else None,
        "created_at": dispute.created_at.isoformat(),
    }


def safe_order_summary(order: OrderRecord) -> dict[str, Any]:
    return {
        "id": order.id,
        "public_order_code": order.public_order_code,
        "status": order.status,
        "amount_usd": str(order.amount_usd),
        "business_id": order.business_id,
        "created_at": order.created_at.isoformat(),
    }
