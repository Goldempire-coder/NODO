from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from app.auth.dependencies import require_current_user
from app.modules.disputes.schemas import AdminOrderDisputeOpenRequest, DisputeCreateRequest, DisputeResolveRequest
from app.modules.disputes.service import DisputeService
from app.modules.notifications.order_notifications import OrderNotificationService
from app.modules.users.models import UserRecord
from app.shared.observability import get_correlation_id, get_operation_id, get_request_id

router = APIRouter(tags=["disputes"])


def _request_id(request: Request) -> str:
    return get_request_id(request)


def _mark_admin_response_private(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"


def _service(request: Request) -> DisputeService:
    notifications = OrderNotificationService(
        settings=request.app.state.settings,
        job_repository=request.app.state.job_repository,
        business_repository=request.app.state.business_repository,
        correlation_id=get_correlation_id(request),
        operation_id=get_operation_id(request),
    )
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
        notification_service=notifications,
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
    response: Response,
    status: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    _mark_admin_response_private(response)
    return {"data": _service(request).list_admin_disputes(user=user, status=status, cursor=cursor, limit=limit, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.get("/admin/disputes/{dispute_id}")
def admin_dispute_detail(dispute_id: str, request: Request, response: Response, user: UserRecord = Depends(require_current_user)) -> dict:
    _mark_admin_response_private(response)
    return {"data": _service(request).admin_dispute_detail(user=user, dispute_id=dispute_id, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.post("/admin/orders/{order_id}/open-dispute", status_code=201)
def open_admin_order_dispute(
    order_id: str,
    payload: AdminOrderDisputeOpenRequest,
    request: Request,
    response: Response,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    _mark_admin_response_private(response)
    return {
        "data": _service(request).open_admin_order_dispute(
            user=user,
            order_id=order_id,
            payload=payload,
            request_id=_request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": _request_id(request),
    }


@router.post("/admin/disputes/{dispute_id}/resolve")
def resolve_admin_dispute(
    dispute_id: str,
    payload: DisputeResolveRequest,
    request: Request,
    response: Response,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    _mark_admin_response_private(response)
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
