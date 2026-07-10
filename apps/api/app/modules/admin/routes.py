from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.auth.dependencies import require_current_user
from app.modules.admin.service import AdminService
from app.modules.users.models import UserRecord

router = APIRouter(prefix="/admin", tags=["admin-console"])


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def _service(request: Request) -> AdminService:
    return AdminService(
        settings=request.app.state.settings,
        repository=request.app.state.admin_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
        read_model_cache=request.app.state.admin_read_model_cache,
    )


@router.get("/dashboard")
def dashboard(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).dashboard(user=user, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.get("/metrics")
def metrics(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).metrics(user=user, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.get("/businesses")
def list_businesses(
    request: Request,
    verification_status: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).list_businesses(
            user=user,
            verification_status=verification_status,
            risk_level=risk_level,
            cursor=cursor,
            limit=limit,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.get("/businesses/{business_id}")
def business_detail(business_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).business_detail(user=user, business_id=business_id, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.get("/orders")
def list_orders(
    request: Request,
    status: str | None = Query(default=None),
    business_id: str | None = Query(default=None),
    remitter_user_id: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).list_orders(
            user=user,
            status=status,
            business_id=business_id,
            remitter_user_id=remitter_user_id,
            cursor=cursor,
            limit=limit,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.get("/orders/{order_id}")
def order_detail(order_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).order_detail(user=user, order_id=order_id, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.get("/audit-logs")
def audit_logs(
    request: Request,
    event_type: str | None = Query(default=None),
    actor_user_id: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).audit_logs(
            user=user,
            event_type=event_type,
            actor_user_id=actor_user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            cursor=cursor,
            limit=limit,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }
