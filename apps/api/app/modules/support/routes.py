from __future__ import annotations

from fastapi import APIRouter, Depends, File, Header, Query, Request, Response, UploadFile

from app.auth.dependencies import require_current_user
from app.modules.support.models import MAX_SUPPORT_ATTACHMENT_SIZE_BYTES
from app.modules.support.schemas import (
    AdminSupportMessageCreateRequest,
    OperationReportCreateRequest,
    SupportAssignRequest,
    SupportEscalateRequest,
    SupportMessageCreateRequest,
    SupportReasonRequest,
    SupportTicketCreateRequest,
)
from app.modules.support.service import SupportService
from app.modules.notifications.support_notifications import SupportNotificationService
from app.modules.users.models import UserRecord
from app.shared.observability import get_correlation_id, get_operation_id
from app.shared.validation import read_limited_upload

def _private_no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"


router = APIRouter(tags=["support"], dependencies=[Depends(_private_no_store)])


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def _service(request: Request) -> SupportService:
    notifications = SupportNotificationService(
        settings=request.app.state.settings,
        job_repository=request.app.state.job_repository,
        correlation_id=get_correlation_id(request),
        operation_id=get_operation_id(request),
    )
    return SupportService(
        settings=request.app.state.settings,
        repository=request.app.state.support_repository,
        order_repository=request.app.state.order_repository,
        business_repository=request.app.state.business_repository,
        ad_repository=request.app.state.ad_repository,
        credit_repository=request.app.state.credit_repository,
        dispute_repository=request.app.state.dispute_repository,
        user_repository=request.app.state.user_repository,
        staff_repository=getattr(request.app.state, "staff_repository", None),
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
        idempotency_store=request.app.state.idempotency_store,
        storage=request.app.state.private_storage,
        admin_notifications=getattr(request.app.state, "admin_notification_service", None),
        notification_service=notifications,
        marketplace_cache=request.app.state.marketplace_cache,
    )


@router.post("/support/tickets", status_code=201)
def create_ticket(
    payload: SupportTicketCreateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    surface: str | None = Header(default=None, alias="X-NODO-Surface"),
) -> dict:
    return {
        "data": _service(request).create_ticket(user=user, payload=payload, surface=surface, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.post("/orders/{order_id}/operation-report", status_code=201)
def create_operation_report(
    order_id: str,
    payload: OperationReportCreateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).create_operation_report(
            user=user,
            order_id=order_id,
            payload=payload,
            request_id=_request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": _request_id(request),
    }


@router.post("/admin/business-publication-holds/{hold_id}/release")
def release_publication_hold(
    hold_id: str,
    payload: SupportReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).release_publication_hold(
            user=user,
            hold_id=hold_id,
            payload=payload,
            request_id=_request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": _request_id(request),
    }


@router.get("/support/tickets")
def list_tickets(
    request: Request,
    status: str | None = Query(default=None),
    status_group: str | None = Query(default=None),
    scope: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).list_user_tickets(user=user, status=status, status_group=status_group, scope=scope, cursor=cursor, limit=limit, request_id=_request_id(request)),
        "request_id": _request_id(request),
    }


@router.get("/support/tickets/{ticket_id}")
def ticket_detail(
    ticket_id: str,
    request: Request,
    messages_cursor: str | None = Query(default=None),
    messages_limit: int = Query(default=25, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).user_ticket_detail(
            user=user,
            ticket_id=ticket_id,
            messages_cursor=messages_cursor,
            messages_limit=messages_limit,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.post("/support/tickets/{ticket_id}/messages", status_code=201)
def create_message(
    ticket_id: str,
    payload: SupportMessageCreateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).create_user_message(user=user, ticket_id=ticket_id, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.post("/support/tickets/{ticket_id}/attachments", status_code=201)
async def upload_attachment(
    ticket_id: str,
    request: Request,
    file: UploadFile = File(...),
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    content = await read_limited_upload(
        file,
        max_bytes=MAX_SUPPORT_ATTACHMENT_SIZE_BYTES,
        empty_or_too_large_error="SUPPORT_ATTACHMENT_TOO_LARGE",
    )
    return {
        "data": _service(request).upload_attachment(
            user=user,
            ticket_id=ticket_id,
            file_name=file.filename or "support-attachment",
            mime_type=file.content_type or "",
            content=content,
            request_id=_request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": _request_id(request),
    }


@router.post("/support/tickets/{ticket_id}/close")
def close_own_ticket(
    ticket_id: str,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).close_user_ticket(
            user=user,
            ticket_id=ticket_id,
            request_id=_request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": _request_id(request),
    }


@router.get("/admin/support/tickets")
def admin_list_tickets(
    request: Request,
    status: str | None = Query(default=None),
    status_group: str | None = Query(default=None),
    scope: str | None = Query(default=None),
    category: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    assigned_support_user_id: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).list_admin_tickets(
            user=user,
            status=status,
            status_group=status_group,
            scope=scope,
            category=category,
            priority=priority,
            assigned_support_user_id=assigned_support_user_id,
            cursor=cursor,
            limit=limit,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.get("/admin/support/tickets/{ticket_id}")
def admin_ticket_detail(
    ticket_id: str,
    request: Request,
    messages_cursor: str | None = Query(default=None),
    messages_limit: int = Query(default=25, ge=1, le=50),
    events_cursor: str | None = Query(default=None),
    events_limit: int = Query(default=25, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).admin_ticket_detail(
            user=user,
            ticket_id=ticket_id,
            messages_cursor=messages_cursor,
            messages_limit=messages_limit,
            events_cursor=events_cursor,
            events_limit=events_limit,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.post("/admin/support/tickets/{ticket_id}/messages", status_code=201)
def admin_create_message(
    ticket_id: str,
    payload: AdminSupportMessageCreateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).create_admin_message(user=user, ticket_id=ticket_id, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.post("/admin/support/tickets/{ticket_id}/assign")
def assign_ticket(
    ticket_id: str,
    payload: SupportAssignRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).assign_ticket(user=user, ticket_id=ticket_id, assigned_support_user_id=payload.assigned_support_user_id, reason=payload.reason, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.post("/admin/support/tickets/{ticket_id}/escalate")
def escalate_ticket(
    ticket_id: str,
    payload: SupportEscalateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).escalate_ticket(user=user, ticket_id=ticket_id, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.post("/admin/support/tickets/{ticket_id}/resolve")
def resolve_ticket(
    ticket_id: str,
    payload: SupportReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).resolve_ticket(user=user, ticket_id=ticket_id, reason=payload.reason, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.post("/admin/support/tickets/{ticket_id}/close")
def close_ticket(
    ticket_id: str,
    payload: SupportReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).close_ticket(user=user, ticket_id=ticket_id, reason=payload.reason, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.post("/admin/support/tickets/{ticket_id}/attachments/{file_id}/view-url")
def attachment_view_url(
    ticket_id: str,
    file_id: str,
    payload: SupportReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).attachment_view_url(user=user, ticket_id=ticket_id, file_id=file_id, reason=payload.reason, request_id=_request_id(request)),
        "request_id": _request_id(request),
    }
