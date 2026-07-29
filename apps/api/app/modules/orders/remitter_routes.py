from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request

from app.auth.dependencies import require_current_user, require_current_user_with_terms
from app.modules.operations import require_platform_operational
from app.modules.orders.helpers import activate_response_profile, reset_response_profile
from app.modules.orders.routes_support import order_service, request_id
from app.modules.orders.schemas import (
    OrderActionRequest,
    OrderCancelRequest,
    OrderCreateRequest,
    OrderRatingRequest,
)
from app.modules.users.models import UserRecord
from app.shared.profiling import staging_response_profile_enabled

router = APIRouter(tags=["orders"])


def _attach_dependency_profile(request: Request, data: dict) -> dict:
    auth_profile = getattr(request.state, "nodo_auth_profile", None)
    if auth_profile is None:
        return data
    profiled = dict(data)
    profile = dict(profiled.get("_profile") or {})
    profile["dependency"] = {"auth": auth_profile}
    profiled["_profile"] = profile
    return profiled


@router.post("/orders", status_code=201)
def create_order(
    payload: OrderCreateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    require_platform_operational(request.app.state.emergency_mode_repository, operation="order_create")
    profile_token = activate_response_profile(staging_response_profile_enabled(request))
    try:
        data = order_service(request).create_order(user=user, payload=payload, request_id=request_id(request), idempotency_key=idempotency_key)
    finally:
        reset_response_profile(profile_token)
    return {
        "data": _attach_dependency_profile(request, data),
        "request_id": request_id(request),
    }


@router.get("/orders/mine")
def my_orders(
    request: Request,
    status: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {"data": order_service(request).mine(user=user, status=status, cursor=cursor, limit=limit, request_id=request_id(request)), "request_id": request_id(request)}


@router.get("/orders/{order_id}")
def order_detail(order_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": order_service(request).detail(user=user, order_id=order_id, request_id=request_id(request)), "request_id": request_id(request)}


@router.post("/orders/{order_id}/rating", status_code=201)
def create_order_rating(
    order_id: str,
    payload: OrderRatingRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": order_service(request).create_rating(
            user=user,
            order_id=order_id,
            payload=payload,
            request_id=request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": request_id(request),
    }


@router.post("/orders/{order_id}/extend-payment-deadline")
def extend_payment_deadline(
    order_id: str,
    request: Request,
    payload: OrderActionRequest | None = None,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": order_service(request).extend(user=user, order_id=order_id, payload=payload, request_id=request_id(request), idempotency_key=idempotency_key),
        "request_id": request_id(request),
    }


@router.post("/orders/{order_id}/cancel")
def cancel_order(
    order_id: str,
    request: Request,
    payload: OrderCancelRequest | None = None,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": order_service(request).cancel(user=user, order_id=order_id, payload=payload, request_id=request_id(request), idempotency_key=idempotency_key),
        "request_id": request_id(request),
    }
