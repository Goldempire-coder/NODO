from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request

from app.auth.dependencies import require_current_user
from app.modules.staff.schemas import StaffInviteCreateRequest, StaffPermissionsUpdateRequest, StaffReasonRequest
from app.modules.staff.service import StaffService
from app.modules.users.models import UserRecord

router = APIRouter(prefix="/admin/staff", tags=["admin-staff"])


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def _service(request: Request) -> StaffService:
    return StaffService(
        settings=request.app.state.settings,
        repository=request.app.state.staff_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
        idempotency_store=request.app.state.idempotency_store,
    )


@router.get("")
def list_staff(
    request: Request,
    status: str | None = Query(default=None),
    staff_role: str | None = Query(default=None),
    q: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).list_staff(user=user, status=status, staff_role=staff_role, q=q, cursor=cursor, limit=limit, request_id=_request_id(request)),
        "request_id": _request_id(request),
    }


@router.get("/{staff_id}")
def staff_detail(staff_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).detail(user=user, profile_id=staff_id, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.post("/invites", status_code=201)
def create_staff_invite(
    payload: StaffInviteCreateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {"data": _service(request).create_invite(user=user, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key), "request_id": _request_id(request)}


@router.post("/{staff_id}/activate")
def activate_staff(
    staff_id: str,
    payload: StaffReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {"data": _service(request).activate(user=user, profile_id=staff_id, reason=payload.reason, request_id=_request_id(request), idempotency_key=idempotency_key), "request_id": _request_id(request)}


@router.post("/{staff_id}/suspend")
def suspend_staff(
    staff_id: str,
    payload: StaffReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {"data": _service(request).suspend(user=user, profile_id=staff_id, reason=payload.reason, request_id=_request_id(request), idempotency_key=idempotency_key), "request_id": _request_id(request)}


@router.post("/{staff_id}/revoke")
def revoke_staff(
    staff_id: str,
    payload: StaffReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {"data": _service(request).revoke(user=user, profile_id=staff_id, reason=payload.reason, request_id=_request_id(request), idempotency_key=idempotency_key), "request_id": _request_id(request)}


@router.post("/{staff_id}/permissions")
def update_staff_permissions(
    staff_id: str,
    payload: StaffPermissionsUpdateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {"data": _service(request).update_permissions(user=user, profile_id=staff_id, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key), "request_id": _request_id(request)}


@router.get("/{staff_id}/activity")
def staff_activity(
    staff_id: str,
    request: Request,
    event_type: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).activity(user=user, profile_id=staff_id, event_type=event_type, cursor=cursor, limit=limit, request_id=_request_id(request)),
        "request_id": _request_id(request),
    }
