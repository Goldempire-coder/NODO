from __future__ import annotations

from typing import Any

from app.modules.ads.models import CreditLedgerRecord
from app.modules.orders.models import OrderRecord, PaymentReportRecord
from app.modules.orders.serializers import business_order_payload, business_payment_report_payload
from app.modules.users.models import UserRecord


def payment_confirmed_state_metadata(
    *,
    report: PaymentReportRecord,
    ledger: CreditLedgerRecord,
    order: OrderRecord,
    idempotency_key: str,
) -> dict[str, Any]:
    return {
        "payment_report_id": report.id,
        "ledger_id": ledger.id,
        "ad_id": order.ad_id,
        "idempotency_key": idempotency_key,
    }


def payment_confirmation_audit_events(
    *,
    user: UserRecord,
    order: OrderRecord,
    report: PaymentReportRecord,
    ledger: CreditLedgerRecord,
    reason: str | None,
    request_id: str,
) -> list[dict[str, Any]]:
    return [
        {
            "event_type": "payment_confirmed",
            "actor_user_id": user.id,
            "actor_role": user.role,
            "resource_type": "order",
            "resource_id": order.id,
            "request_id": request_id,
            "metadata_json": {"payment_report_id": report.id, "reason": reason},
        },
        {
            "event_type": "credits_consumed",
            "actor_user_id": user.id,
            "actor_role": user.role,
            "resource_type": "order",
            "resource_id": order.id,
            "request_id": request_id,
            "metadata_json": {"ledger_id": ledger.id, "amount": ledger.amount, "ad_id": order.ad_id},
        },
        {
            "event_type": "ad_archived",
            "actor_user_id": user.id,
            "actor_role": user.role,
            "resource_type": "ad",
            "resource_id": order.ad_id,
            "request_id": request_id,
            "metadata_json": {"order_id": order.id},
        },
    ]


def business_payment_confirmation_response(
    *,
    order: OrderRecord,
    report: PaymentReportRecord,
    ledger: CreditLedgerRecord,
    disclaimer: str,
) -> dict[str, Any]:
    return {
        "order": business_order_payload(order),
        "payment_report": business_payment_report_payload(report),
        "credits": {"ledger_id": ledger.id, "consumed": ledger.amount},
        "disclaimer": disclaimer,
    }
