from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response

from app.auth.dependencies import require_current_user, require_current_user_with_terms
from app.modules.businesses.route_dependencies import business_service, request_id
from app.modules.businesses.schemas import BusinessAvailabilityUpdateRequest, BusinessCapacityUpdateRequest, BusinessOwnPaymentMethodCreateRequest, BusinessOwnPaymentMethodUpdateRequest, BusinessPinSetupRequest, BusinessPinVerifyRequest
from app.modules.users.models import UserRecord

router = APIRouter(tags=["businesses"])


@router.get("/businesses/me")
def my_business(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": business_service(request).my_business(user=user), "request_id": request_id(request)}


@router.get("/business/payment-methods")
def own_payment_methods(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": business_service(request).own_payment_methods(user=user), "request_id": request_id(request)}


@router.get("/business/capacity")
def own_business_capacity(
    request: Request,
    response: Response,
    user: UserRecord = Depends(require_current_user_with_terms),
) -> dict:
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "data": business_service(request).own_capacity(user=user),
        "request_id": request_id(request),
    }


@router.put("/business/capacity")
def update_own_business_capacity(
    payload: BusinessCapacityUpdateRequest,
    request: Request,
    response: Response,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "data": business_service(request).update_own_capacity(
            user=user,
            payload=payload,
            request_id=request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": request_id(request),
    }


@router.get("/business/security/pin")
def business_pin_status(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": business_service(request).business_pin_status(user=user), "request_id": request_id(request)}


@router.patch("/business/availability")
def update_own_availability(
    payload: BusinessAvailabilityUpdateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": business_service(request).update_own_availability(
            user=user,
            payload=payload,
            request_id=request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": request_id(request),
    }


@router.post("/business/security/pin/setup")
def setup_business_pin(
    payload: BusinessPinSetupRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": business_service(request).setup_business_pin(
            user=user,
            payload=payload,
            request_id=request_id(request),
        ),
        "request_id": request_id(request),
    }


@router.post("/business/security/pin/verify")
def verify_business_pin(
    payload: BusinessPinVerifyRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": business_service(request).verify_business_pin(
            user=user,
            payload=payload,
            request_id=request_id(request),
        ),
        "request_id": request_id(request),
    }


@router.post("/business/security/pin/lock")
def lock_business_pin(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": business_service(request).lock_business_pin(user=user, request_id=request_id(request)), "request_id": request_id(request)}


@router.post("/business/payment-methods", status_code=201)
def create_own_payment_method(
    payload: BusinessOwnPaymentMethodCreateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": business_service(request).create_own_payment_method(
            user=user,
            payload=payload,
            request_id=request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": request_id(request),
    }


@router.patch("/business/payment-methods/{payment_method_id}")
def update_own_payment_method(
    payment_method_id: str,
    payload: BusinessOwnPaymentMethodUpdateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": business_service(request).update_own_payment_method(
            user=user,
            payment_method_id=payment_method_id,
            payload=payload,
            request_id=request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": request_id(request),
    }


@router.delete("/business/payment-methods/{payment_method_id}")
def delete_own_payment_method(
    payment_method_id: str,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": business_service(request).delete_own_payment_method(
            user=user,
            payment_method_id=payment_method_id,
            request_id=request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": request_id(request),
    }
