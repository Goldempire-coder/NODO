from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Header, Request, UploadFile

from app.auth.dependencies import require_current_user, require_current_user_with_terms
from app.core.errors import ApiError
from app.modules.orders.payment_constants import MAX_PAYMENT_EVIDENCE_SIZE_BYTES
from app.modules.orders.routes_support import order_service, request_id
from app.modules.orders.schemas import PaymentReportRequest
from app.modules.users.models import UserRecord
from app.shared.validation import read_limited_upload

router = APIRouter(tags=["orders"])


@router.get("/orders/{order_id}/payment-instructions")
def payment_instructions(order_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": order_service(request).payment_instructions(user=user, order_id=order_id, request_id=request_id(request)), "request_id": request_id(request)}


@router.post("/orders/{order_id}/payment-evidence", status_code=201)
async def upload_payment_evidence(
    order_id: str,
    request: Request,
    file: UploadFile = File(...),
    file_type: str = Form(...),
    pending_payment_report_id: str | None = Form(default=None),
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    if file_type != "payment_evidence":
        raise ApiError("INVALID_PAYMENT_EVIDENCE", status_code=400)
    content = await read_limited_upload(
        file,
        max_bytes=MAX_PAYMENT_EVIDENCE_SIZE_BYTES,
        empty_or_too_large_error="INVALID_PAYMENT_EVIDENCE",
    )
    return {
        "data": order_service(request).upload_payment_evidence(
            user=user,
            order_id=order_id,
            file_name=file.filename or "payment-evidence",
            mime_type=file.content_type or "",
            content=content,
            pending_payment_report_id=pending_payment_report_id,
            request_id=request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": request_id(request),
    }


@router.post("/orders/{order_id}/payment-report", status_code=201)
def report_payment(
    order_id: str,
    payload: PaymentReportRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": order_service(request).report_payment(user=user, order_id=order_id, payload=payload, request_id=request_id(request), idempotency_key=idempotency_key),
        "request_id": request_id(request),
    }
