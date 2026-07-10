from __future__ import annotations

from fastapi import APIRouter, Depends, File, Header, Query, Request, UploadFile

from app.auth.dependencies import require_current_user
from app.modules.chat.schemas import MessageCreateRequest
from app.modules.chat.service import ChatService
from app.modules.users.models import UserRecord

router = APIRouter(tags=["chat"])


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def _service(request: Request) -> ChatService:
    return ChatService(
        settings=request.app.state.settings,
        repository=request.app.state.chat_repository,
        order_repository=request.app.state.order_repository,
        business_repository=request.app.state.business_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
        idempotency_store=request.app.state.idempotency_store,
        storage=request.app.state.private_storage,
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
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {"data": _service(request).create_message(user=user, order_id=order_id, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key), "request_id": _request_id(request)}


@router.post("/orders/{order_id}/message-attachments", status_code=201)
async def upload_message_attachment(
    order_id: str,
    request: Request,
    file: UploadFile = File(...),
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    content = await file.read()
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

