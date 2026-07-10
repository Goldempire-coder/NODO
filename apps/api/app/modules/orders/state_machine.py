from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.errors import ApiError
from app.modules.orders.models import OrderRecord


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ensure_aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def is_waiting_payment_expired(order: OrderRecord, *, now: datetime | None = None) -> bool:
    current = now or now_utc()
    return order.status == "waiting_payment" and ensure_aware(order.payment_report_deadline_at) <= current


def require_extend_allowed(order: OrderRecord) -> None:
    if order.status != "waiting_payment":
        raise ApiError("ORDER_STATUS_INVALID", status_code=409)
    if order.paid_reported_at is not None:
        raise ApiError("ORDER_PAYMENT_ALREADY_REPORTED", status_code=409)
    if order.extension_used:
        raise ApiError("ORDER_EXTENSION_ALREADY_USED", status_code=409)
    if is_waiting_payment_expired(order):
        raise ApiError("ORDER_EXPIRED", status_code=409)


def require_cancel_allowed(order: OrderRecord) -> None:
    if order.status != "waiting_payment":
        raise ApiError("ORDER_STATUS_INVALID", status_code=409)
    if order.paid_reported_at is not None:
        raise ApiError("ORDER_PAYMENT_ALREADY_REPORTED", status_code=409)
    if is_waiting_payment_expired(order):
        raise ApiError("ORDER_EXPIRED", status_code=409)


def require_payment_reveal_allowed(order: OrderRecord) -> None:
    if order.status != "waiting_payment":
        raise ApiError("ORDER_STATUS_INVALID", status_code=409)
    if is_waiting_payment_expired(order):
        raise ApiError("ORDER_EXPIRED", status_code=409)


def require_payment_report_allowed(order: OrderRecord) -> None:
    if order.status == "payment_reported":
        raise ApiError("PAYMENT_REPORT_ALREADY_SUBMITTED", status_code=409)
    if order.status != "waiting_payment":
        raise ApiError("PAYMENT_REPORT_NOT_ALLOWED", status_code=409)
    if is_waiting_payment_expired(order):
        raise ApiError("ORDER_EXPIRED", status_code=409)


def require_business_payment_confirmation_allowed(order: OrderRecord) -> None:
    if order.status != "payment_reported":
        raise ApiError("PAYMENT_CONFIRMATION_NOT_ALLOWED", status_code=409)


def require_business_payment_rejection_allowed(order: OrderRecord) -> None:
    if order.status != "payment_reported":
        raise ApiError("PAYMENT_REJECTION_NOT_ALLOWED", status_code=409)


def require_business_delivery_allowed(order: OrderRecord) -> None:
    if order.status != "payment_confirmed":
        raise ApiError("DELIVERY_NOT_ALLOWED", status_code=409)


def extended_deadline(order: OrderRecord) -> datetime:
    return ensure_aware(order.payment_report_deadline_at) + timedelta(minutes=15)
