from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.modules.ads.models import AdRecord
from app.modules.businesses.models import BusinessPaymentMethodRecord, BusinessRecord
from app.modules.orders.schemas import OrderCreateRequest
from app.modules.users.models import UserRecord


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def payment_snapshot(payment: BusinessPaymentMethodRecord) -> dict[str, Any]:
    return {
        "method_type": payment.method_type,
        "network": payment.network,
        "account_value": payment.account_value,
        "account_masked": payment.account_masked,
        "holder_name": payment.holder_name,
    }


@dataclass(frozen=True)
class CreateOrderPlan:
    amount_bs: Decimal
    deadline: datetime
    initial_state_event: dict[str, Any]
    create_order_fields: dict[str, Any]
    audit_events: list[dict[str, Any]]


def build_create_order_plan(
    *,
    user: UserRecord,
    payload: OrderCreateRequest,
    ad: AdRecord,
    business: BusinessRecord,
    payment: BusinessPaymentMethodRecord,
    deadline: datetime,
    request_id: str,
    idempotency_key: str,
) -> CreateOrderPlan:
    amount_bs = money(payload.amount_usd * ad.rate_bs_per_usd)
    return CreateOrderPlan(
        amount_bs=amount_bs,
        deadline=deadline,
        initial_state_event=build_initial_order_state_event(user=user, ad=ad, request_id=request_id, idempotency_key=idempotency_key),
        create_order_fields=build_create_order_fields(
            user=user,
            payload=payload,
            ad=ad,
            business=business,
            payment=payment,
            deadline=deadline,
            idempotency_key=idempotency_key,
            amount_bs=amount_bs,
        ),
        audit_events=build_create_order_audit_events(user=user, ad=ad, request_id=request_id),
    )


def build_initial_order_state_event(*, user: UserRecord, ad: AdRecord, request_id: str, idempotency_key: str) -> dict[str, Any]:
    return {
        "from_status": None,
        "to_status": "waiting_payment",
        "event_type": "order_created",
        "actor_user_id": user.id,
        "actor_role": user.role,
        "reason": None,
        "request_id": request_id,
        "metadata_json": {"ad_id": ad.id, "idempotency_key": idempotency_key},
    }


def build_create_order_fields(
    *,
    user: UserRecord,
    payload: OrderCreateRequest,
    ad: AdRecord,
    business: BusinessRecord,
    payment: BusinessPaymentMethodRecord,
    deadline: datetime,
    idempotency_key: str,
    amount_bs: Decimal,
) -> dict[str, Any]:
    return {
        "ad_id": ad.id,
        "business_id": business.id,
        "remitter_user_id": user.id,
        "status": "waiting_payment",
        "idempotency_key": idempotency_key,
        "amount_usd": payload.amount_usd,
        "rate_snapshot": ad.rate_bs_per_usd,
        "amount_bs_calculated": amount_bs,
        "business_name_snapshot": business.business_name,
        "payment_method_snapshot": ad.payment_method,
        "delivery_method_snapshot": ad.delivery_method,
        "min_amount_snapshot": ad.amount_min_usd,
        "max_amount_snapshot": ad.amount_max_usd,
        "payment_instructions_snapshot": payment_snapshot(payment),
        "receiver_data_json": payload.receiver_data.model_dump() if payload.receiver_data else {},
        "payment_report_deadline_at": deadline,
        "expires_at": deadline,
    }


def build_create_order_audit_events(*, user: UserRecord, ad: AdRecord, request_id: str) -> list[dict[str, Any]]:
    return [
        {
            "event_type": "order_created",
            "actor_user_id": user.id,
            "actor_role": user.role,
            "resource_type": "order",
            "resource_id": None,
            "request_id": request_id,
            "metadata_json": {"ad_id": ad.id},
        },
        {
            "event_type": "ad_moved_in_order",
            "actor_user_id": user.id,
            "actor_role": user.role,
            "resource_type": "ad",
            "resource_id": ad.id,
            "request_id": request_id,
            "metadata_json": {"order_id": None},
        },
        {
            "event_type": "business_capacity_reserved",
            "actor_user_id": user.id,
            "actor_role": user.role,
            "resource_type": "order",
            "resource_id": None,
            "request_id": request_id,
            "metadata_json": {
                "business_id": ad.business_id,
            },
        },
    ]


def bind_created_order_to_audit_events(audit_events: list[dict[str, Any]], *, order_id: str) -> list[dict[str, Any]]:
    bound: list[dict[str, Any]] = []
    for event in audit_events:
        item = {**event}
        if item["event_type"] == "order_created":
            item["resource_id"] = order_id
        if item["event_type"] == "business_capacity_reserved":
            item["resource_id"] = order_id
        if item["event_type"] == "ad_moved_in_order":
            item["metadata_json"] = {**item["metadata_json"], "order_id": order_id}
        bound.append(item)
    return bound
