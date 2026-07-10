from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request

from app.auth.dependencies import require_current_user
from app.modules.businesses.route_dependencies import business_service, request_id
from app.modules.businesses.schemas import AdminBusinessAccessLinkCreateRequest, AdminReasonRequest
from app.modules.users.models import UserRecord

router = APIRouter(tags=["admin-business-access"])


@router.post("/admin/businesses/{business_id}/access-links", status_code=201)
def admin_create_business_access_link(
    business_id: str,
    payload: AdminBusinessAccessLinkCreateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": business_service(request).create_access_link(
            user=user,
            business_id=business_id,
            payload=payload,
            request_id=request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": request_id(request),
    }


def _change_access_link_status(
    *,
    business_id: str,
    link_id: str,
    status: str,
    payload: AdminReasonRequest,
    request: Request,
    user: UserRecord,
    idempotency_key: str | None,
) -> dict:
    return {
        "data": business_service(request).change_access_link_status(
            user=user,
            business_id=business_id,
            link_id=link_id,
            status=status,
            reason=payload.reason,
            request_id=request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": request_id(request),
    }


@router.post("/admin/businesses/{business_id}/access-links/{link_id}/suspend")
def admin_suspend_business_access_link(
    business_id: str,
    link_id: str,
    payload: AdminReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return _change_access_link_status(business_id=business_id, link_id=link_id, status="suspended", payload=payload, request=request, user=user, idempotency_key=idempotency_key)


@router.post("/admin/businesses/{business_id}/access-links/{link_id}/reactivate")
def admin_reactivate_business_access_link(
    business_id: str,
    link_id: str,
    payload: AdminReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return _change_access_link_status(business_id=business_id, link_id=link_id, status="active", payload=payload, request=request, user=user, idempotency_key=idempotency_key)


@router.post("/admin/businesses/{business_id}/access-links/{link_id}/revoke")
def admin_revoke_business_access_link(
    business_id: str,
    link_id: str,
    payload: AdminReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return _change_access_link_status(business_id=business_id, link_id=link_id, status="revoked", payload=payload, request=request, user=user, idempotency_key=idempotency_key)


@router.post("/admin/businesses/{business_id}/access-links/{link_id}/block")
def admin_block_business_access_link(
    business_id: str,
    link_id: str,
    payload: AdminReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return _change_access_link_status(business_id=business_id, link_id=link_id, status="blocked", payload=payload, request=request, user=user, idempotency_key=idempotency_key)
