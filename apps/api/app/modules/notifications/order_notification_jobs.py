from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.modules.jobs.models import mask_metadata
from app.modules.orders.models import OrderRecord


@dataclass(frozen=True)
class OrderCreatedBusinessNotificationPlan:
    recipient_user_id: str
    web_app_base_url: str
    request_id: str
    correlation_id: str | None = None
    operation_id: str | None = None


def build_order_created_business_job(
    *,
    order: OrderRecord,
    plan: OrderCreatedBusinessNotificationPlan,
    enqueued_at: datetime | None = None,
) -> dict[str, Any]:
    now = enqueued_at or datetime.now(timezone.utc)
    action_url = (
        f"{plan.web_app_base_url.rstrip('/')}/business/"
        f"?view=business-chat&order_id={order.id}"
    )
    metadata = {
        "channel": "telegram",
        "delivery_state": "pending",
        "event": "order_created_business",
        "target_surface": "business_mini_app",
        "public_order_code": order.public_order_code,
        "order_status": order.status,
        "message_text": (
            f"Nueva negociacion {order.public_order_code}. Abre NODO para revisarla."
        ),
        "action_text": "Abrir orden",
        "action_url": action_url,
        "request_id": plan.request_id,
        "order_created_at": order.created_at.isoformat(),
        "job_enqueued_at": now.isoformat(),
    }
    if plan.correlation_id:
        metadata["correlation_id"] = plan.correlation_id
    if plan.operation_id:
        metadata["operation_id"] = plan.operation_id
    return {
        "notification_type": "order_created_business",
        "recipient_user_id": plan.recipient_user_id,
        "recipient_role": None,
        "order_id": order.id,
        "business_id": order.business_id,
        "dispute_id": None,
        "scheduled_for": now,
        "dedupe_key": (
            f"order:{order.id}:event:order_created_business:"
            f"recipient:{plan.recipient_user_id}"
        ),
        "metadata_json": mask_metadata(metadata),
    }
