from __future__ import annotations

from typing import Any

from app.modules.orders.models import OrderRecord, PaymentReportRecord
from app.modules.orders.serializers import business_order_payload, business_payment_report_payload
from app.modules.users.models import UserRecord


def payment_rejected_state_metadata(*, report: PaymentReportRecord, idempotency_key: str) -> dict[str, Any]:
    return {"payment_report_id": report.id, "idempotency_key": idempotency_key}


def payment_rejected_audit_event(
    *,
    user: UserRecord,
    order: OrderRecord,
    report: PaymentReportRecord,
    reason: str,
    request_id: str,
) -> dict[str, Any]:
    return {
        "event_type": "payment_report_rejected",
        "actor_user_id": user.id,
        "actor_role": user.role,
        "resource_type": "order",
        "resource_id": order.id,
        "request_id": request_id,
        "metadata_json": {"payment_report_id": report.id, "reason": reason},
    }


def payment_rejected_response(
    *,
    order: OrderRecord,
    report: PaymentReportRecord,
    disclaimer: str,
) -> dict[str, Any]:
    return {
        "order": business_order_payload(order),
        "payment_report": business_payment_report_payload(report),
        "disclaimer": disclaimer,
    }


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
