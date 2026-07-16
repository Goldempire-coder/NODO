from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request

from app.auth.dependencies import require_current_user
from app.modules.businesses.route_dependencies import business_service as business_access_service
from app.modules.orders.routes_support import order_service, request_id
from app.modules.orders.schemas import OrderActionRequest
from app.modules.users.models import UserRecord

router = APIRouter(tags=["orders"])


def _require_business_pin(request: Request, user: UserRecord) -> None:
    business_access_service(request).require_unlocked_business_pin(user=user)


@router.get("/business/orders")
def business_orders(
    request: Request,
    status: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {"data": order_service(request).business_orders(user=user, status=status, cursor=cursor, limit=limit, request_id=request_id(request)), "request_id": request_id(request)}


@router.get("/business/orders/{order_id}")
def business_order_detail(order_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": order_service(request).business_order_detail(user=user, order_id=order_id, request_id=request_id(request)), "request_id": request_id(request)}


@router.post("/business/orders/{order_id}/confirm-payment")
def confirm_business_payment(
    order_id: str,
    request: Request,
    payload: OrderActionRequest | None = None,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    _require_business_pin(request, user)
    return {
        "data": order_service(request).confirm_business_payment(user=user, order_id=order_id, payload=payload, request_id=request_id(request), idempotency_key=idempotency_key),
        "request_id": request_id(request),
    }


@router.post("/business/orders/{order_id}/reject-payment-report")
def reject_business_payment_report(
    order_id: str,
    request: Request,
    payload: OrderActionRequest | None = None,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    _require_business_pin(request, user)
    return {
        "data": order_service(request).reject_business_payment_report(user=user, order_id=order_id, payload=payload, request_id=request_id(request), idempotency_key=idempotency_key),
        "request_id": request_id(request),
    }


@router.post("/business/orders/{order_id}/mark-delivered")
def mark_business_delivered(
    order_id: str,
    request: Request,
    payload: OrderActionRequest | None = None,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    _require_business_pin(request, user)
    return {
        "data": order_service(request).mark_business_delivered(user=user, order_id=order_id, payload=payload, request_id=request_id(request), idempotency_key=idempotency_key),
        "request_id": request_id(request),
    }
