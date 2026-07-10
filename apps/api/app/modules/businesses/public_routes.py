from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import require_current_user
from app.modules.businesses.route_dependencies import business_service, request_id
from app.modules.users.models import UserRecord

router = APIRouter(tags=["businesses"])


@router.get("/businesses/me")
def my_business(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": business_service(request).my_business(user=user), "request_id": request_id(request)}


@router.get("/business/payment-methods")
def own_payment_methods(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": business_service(request).own_payment_methods(user=user), "request_id": request_id(request)}
