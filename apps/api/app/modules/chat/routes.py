from __future__ import annotations

from fastapi import APIRouter, Depends, File, Header, Query, Request, Response, UploadFile

from app.auth.dependencies import require_current_user, require_current_user_with_terms
from app.modules.chat.models import MAX_ATTACHMENT_SIZE_BYTES
from app.modules.chat.schemas import MessageCreateRequest
from app.modules.chat.service import ChatService
from app.modules.notifications.chat_notifications import ChatNotificationService
from app.modules.users.models import UserRecord
from app.shared.observability import get_correlation_id, get_operation_id
from app.shared.validation import read_limited_upload

def _private_no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"


router = APIRouter(tags=["chat"], dependencies=[Depends(_private_no_store)])


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def _service(request: Request) -> ChatService:
    notifications = ChatNotificationService(
        settings=request.app.state.settings,
        job_repository=request.app.state.job_repository,
        business_repository=request.app.state.business_repository,
        correlation_id=get_correlation_id(request),
        operation_id=get_operation_id(request),
    )
    return ChatService(
        settings=request.app.state.settings,
        repository=request.app.state.chat_repository,
        order_repository=request.app.state.order_repository,
        business_repository=request.app.state.business_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
        idempotency_store=request.app.state.idempotency_store,
        storage=request.app.state.private_storage,
        admin_notifications=getattr(request.app.state, "admin_notification_service", None),
        notification_service=notifications,
    )


@router.get("/orders/{order_id}/messages")
def list_messages(
    order_id: str,
    request: Request,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {"data": _service(request).list_messages(user=user, order_id=order_id, cursor=cursor, limit=limit, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.post("/orders/{order_id}/messages", status_code=201)
def create_message(
    order_id: str,
    payload: MessageCreateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {"data": _service(request).create_message(user=user, order_id=order_id, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key), "request_id": _request_id(request)}


@router.post("/orders/{order_id}/share-zelle", status_code=201)
def share_configured_zelle(
    order_id: str,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).share_configured_zelle(
            user=user,
            order_id=order_id,
            request_id=_request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": _request_id(request),
    }


@router.post("/orders/{order_id}/share-payment-details", status_code=201)
def share_configured_payment_details(
    order_id: str,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).share_configured_payment_details(
            user=user,
            order_id=order_id,
            request_id=_request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": _request_id(request),
    }


@router.post("/orders/{order_id}/message-attachments", status_code=201)
async def upload_message_attachment(
    order_id: str,
    request: Request,
    file: UploadFile = File(...),
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    content = await read_limited_upload(
        file,
        max_bytes=MAX_ATTACHMENT_SIZE_BYTES,
        empty_or_too_large_error="MESSAGE_ATTACHMENT_TOO_LARGE",
    )
    return {
        "data": _service(request).upload_attachment(
            user=user,
            order_id=order_id,
            file_name=file.filename or "message-attachment",
            mime_type=file.content_type or "",
            content=content,
            request_id=_request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": _request_id(request),
    }


@router.post("/orders/{order_id}/message-attachments/{attachment_id}/view-url")
def message_attachment_view_url(
    order_id: str,
    attachment_id: str,
    request: Request,
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).attachment_view_url(
            user=user,
            order_id=order_id,
            attachment_id=attachment_id,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }
