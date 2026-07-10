from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request

from app.auth.dependencies import require_current_user
from app.modules.disputes.schemas import DisputeCreateRequest, DisputeResolveRequest
from app.modules.disputes.service import DisputeService
from app.modules.users.models import UserRecord

router = APIRouter(tags=["disputes"])


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def _service(request: Request) -> DisputeService:
    return DisputeService(
        settings=request.app.state.settings,
        repository=request.app.state.dispute_repository,
        order_repository=request.app.state.order_repository,
        chat_repository=request.app.state.chat_repository,
        business_repository=request.app.state.business_repository,
        ad_repository=request.app.state.ad_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
        idempotency_store=request.app.state.idempotency_store,
    )


@router.post("/orders/{order_id}/disputes", status_code=201)
def open_dispute(
    order_id: str,
    payload: DisputeCreateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {"data": _service(request).open_dispute(user=user, order_id=order_id, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key), "request_id": _request_id(request)}


@router.get("/admin/disputes")
def list_admin_disputes(
    request: Request,
    status: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {"data": _service(request).list_admin_disputes(user=user, status=status, cursor=cursor, limit=limit, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.get("/admin/disputes/{dispute_id}")
def admin_dispute_detail(dispute_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).admin_dispute_detail(user=user, dispute_id=dispute_id, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.post("/admin/disputes/{dispute_id}/resolve")
def resolve_admin_dispute(
    dispute_id: str,
    payload: DisputeResolveRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).resolve_admin_dispute(
            user=user,
            dispute_id=dispute_id,
            payload=payload,
            request_id=_request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": _request_id(request),
    }
