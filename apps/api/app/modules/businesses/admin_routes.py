from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from app.auth.dependencies import require_current_user
from app.modules.businesses.route_dependencies import business_service, request_id
from app.modules.businesses.schemas import AdminBusinessCapacityUpdateRequest, AdminOperationalCapacityUpdateRequest, AdminReasonRequest
from app.modules.users.models import UserRecord

router = APIRouter(tags=["admin-businesses"])


@router.get("/admin/businesses/pending")
def admin_pending_businesses(
    request: Request,
    user: UserRecord = Depends(require_current_user),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
) -> dict:
    return {
        "data": business_service(request).admin_pending(user=user, cursor=cursor, limit=limit),
        "request_id": request_id(request),
    }


@router.get("/admin/businesses/{business_id}")
def admin_business_detail(
    business_id: str,
    request: Request,
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": business_service(request).admin_detail(user=user, business_id=business_id),
        "request_id": request_id(request),
    }


@router.post("/admin/businesses/{business_id}/verification-documents/{file_id}/view-url")
def admin_document_view_url(
    business_id: str,
    file_id: str,
    payload: AdminReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": business_service(request).signed_document_url(
            user=user,
            business_id=business_id,
            file_id=file_id,
            reason=payload.reason,
            request_id=request_id(request),
        ),
        "request_id": request_id(request),
    }


@router.post("/admin/businesses/{business_id}/approve")
def admin_approve_business(
    business_id: str,
    payload: AdminReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": business_service(request).approve(
            user=user,
            business_id=business_id,
            reason=payload.reason,
            request_id=request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": request_id(request),
    }


@router.post("/admin/businesses/{business_id}/capacity")
def admin_update_business_capacity(
    business_id: str,
    payload: AdminBusinessCapacityUpdateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": business_service(request).update_business_capacity(
            user=user,
            business_id=business_id,
            payload=payload,
            request_id=request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": request_id(request),
    }


@router.get("/admin/businesses/{business_id}/capacity")
def admin_business_operational_capacity(
    business_id: str,
    request: Request,
    response: Response,
    user: UserRecord = Depends(require_current_user),
) -> dict:
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "data": business_service(request).admin_capacity(
            user=user,
            business_id=business_id,
        ),
        "request_id": request_id(request),
    }


@router.put("/admin/businesses/{business_id}/capacity")
def admin_update_business_operational_capacity(
    business_id: str,
    payload: AdminOperationalCapacityUpdateRequest,
    request: Request,
    response: Response,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "data": business_service(request).admin_update_operational_capacity(
            user=user,
            business_id=business_id,
            payload=payload,
            request_id=request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": request_id(request),
    }


@router.post("/admin/businesses/{business_id}/reject")
def admin_reject_business(
    business_id: str,
    payload: AdminReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": business_service(request).reject(
            user=user,
            business_id=business_id,
            reason=payload.reason,
            request_id=request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": request_id(request),
    }


@router.post("/admin/businesses/{business_id}/suspend")
def admin_suspend_business(
    business_id: str,
    payload: AdminReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": business_service(request).suspend_business(
            user=user,
            business_id=business_id,
            reason=payload.reason,
            request_id=request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": request_id(request),
    }


@router.post("/admin/businesses/{business_id}/reactivate")
def admin_reactivate_business(
    business_id: str,
    payload: AdminReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": business_service(request).reactivate_business(
            user=user,
            business_id=business_id,
            reason=payload.reason,
            request_id=request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": request_id(request),
    }


@router.post("/admin/businesses/{business_id}/block")
def admin_block_business(
    business_id: str,
    payload: AdminReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": business_service(request).block_business(
            user=user,
            business_id=business_id,
            reason=payload.reason,
            request_id=request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": request_id(request),
    }
