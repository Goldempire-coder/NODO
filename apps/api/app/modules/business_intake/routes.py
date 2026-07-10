from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile

from app.auth.dependencies import require_current_user
from app.modules.business_intake.route_helpers import request_id, require_business_intake_bot, service
from app.modules.business_intake.schemas import (
    AdminBusinessIntakeDeleteRequest,
    AdminBusinessIntakeReviewRequest,
    BusinessIntakeContactRequest,
    BusinessIntakeStartRequest,
    BusinessIntakeSubmitRequest,
)
from app.modules.business_intake.service import telegram_send_message as _service_telegram_send_message
from app.modules.business_intake.telegram_routes import telegram_router
from app.modules.users.models import UserRecord

router = APIRouter(tags=["business-intake"])
router.include_router(telegram_router)


async def telegram_send_message(bot_token: str, chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    await _service_telegram_send_message(bot_token, chat_id, text, reply_markup)


def _request_id(request: Request) -> str:
    return request_id(request)


def _service(request: Request):  # type: ignore[no-untyped-def]
    return service(request)


def _require_bot(request: Request, secret: str | None) -> None:
    require_business_intake_bot(request, secret)


@router.post("/business-intake/start", status_code=201)
def start_intake(
    payload: BusinessIntakeStartRequest,
    request: Request,
    bot_secret: str | None = Header(default=None, alias="X-NODO-Bot-Webhook-Secret"),
) -> dict:
    _require_bot(request, bot_secret)
    return {"data": _service(request).start(payload=payload, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.post("/business-intake/{intake_id}/contact")
def contact_intake(
    intake_id: str,
    payload: BusinessIntakeContactRequest,
    request: Request,
    bot_secret: str | None = Header(default=None, alias="X-NODO-Bot-Webhook-Secret"),
) -> dict:
    _require_bot(request, bot_secret)
    return {"data": _service(request).contact(intake_id=intake_id, payload=payload, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.post("/business-intake/{intake_id}/submit")
def submit_intake(
    intake_id: str,
    payload: BusinessIntakeSubmitRequest,
    request: Request,
    bot_secret: str | None = Header(default=None, alias="X-NODO-Bot-Webhook-Secret"),
) -> dict:
    _require_bot(request, bot_secret)
    return {"data": _service(request).submit(intake_id=intake_id, payload=payload, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.post("/business-intake/{intake_id}/documents", status_code=201)
async def upload_intake_document(
    intake_id: str,
    request: Request,
    document_kind: str = Form(...),
    telegram_update_id: int = Form(...),
    file: UploadFile = File(...),
    bot_secret: str | None = Header(default=None, alias="X-NODO-Bot-Webhook-Secret"),
) -> dict:
    _require_bot(request, bot_secret)
    content = await file.read()
    return {
        "data": _service(request).upload_document(
            intake_id=intake_id,
            telegram_update_id=telegram_update_id,
            document_kind=document_kind,
            file_name=file.filename or "intake-document",
            mime_type=file.content_type or "",
            content=content,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.get("/admin/business-intake")
def admin_list_intake(
    request: Request,
    status: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).admin_list(user=user, status=status, cursor=cursor, limit=limit, request_id=_request_id(request)),
        "request_id": _request_id(request),
    }


@router.get("/admin/business-intake/{intake_id}")
def admin_intake_detail(intake_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).admin_detail(user=user, intake_id=intake_id, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.post("/admin/business-intake/{intake_id}/accept")
def admin_accept_intake(
    intake_id: str,
    payload: AdminBusinessIntakeReviewRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).admin_accept(user=user, intake_id=intake_id, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.post("/admin/business-intake/{intake_id}/reject")
def admin_reject_intake(
    intake_id: str,
    payload: AdminBusinessIntakeReviewRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).admin_reject(user=user, intake_id=intake_id, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.post("/admin/business-intake/{intake_id}/delete")
def admin_delete_intake(
    intake_id: str,
    payload: AdminBusinessIntakeDeleteRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).admin_delete(user=user, intake_id=intake_id, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }
