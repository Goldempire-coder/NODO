from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile

from app.auth.dependencies import require_current_user
from app.modules.credits.schemas import AdminCreditAdjustmentRequest, AdminReviewCreditPurchaseRequest, ReferralApplyRequest, StripeCheckoutRequest
from app.modules.credits.service import CreditService
from app.modules.users.models import UserRecord

router = APIRouter(tags=["credits"])


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def _service(request: Request) -> CreditService:
    return CreditService(
        settings=request.app.state.settings,
        repository=request.app.state.credit_repository,
        business_repository=request.app.state.business_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
        idempotency_store=request.app.state.idempotency_store,
        storage=request.app.state.private_storage,
    )


@router.get("/business/credits/wallet")
def business_credit_wallet(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).wallet(user=user), "request_id": _request_id(request)}


@router.get("/business/credits/ledger")
def business_credit_ledger(
    request: Request,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    type: str | None = Query(default=None),  # noqa: A002 - API contract uses "type".
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {"data": _service(request).ledger(user=user, cursor=cursor, limit=limit, ledger_type=type), "request_id": _request_id(request)}


@router.post("/business/credits/stripe-checkout", status_code=201)
def create_stripe_checkout(
    payload: StripeCheckoutRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).create_stripe_checkout(user=user, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.post("/business/credits/manual-payment", status_code=201)
async def create_manual_credit_payment(
    request: Request,
    package_code: str = Form(...),
    payment_method: str = Form(...),
    manual_payment_reference: str | None = Form(default=None),
    manual_tx_hash: str | None = Form(default=None),
    manual_network: str | None = Form(default=None),
    file: UploadFile = File(...),
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    content = await file.read()
    return {
        "data": _service(request).create_manual_payment(
            user=user,
            package_code=package_code,
            payment_method=payment_method,
            manual_payment_reference=manual_payment_reference,
            manual_tx_hash=manual_tx_hash,
            manual_network=manual_network,
            file_name=file.filename or "credit-proof",
            mime_type=file.content_type or "",
            content=content,
            request_id=_request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": _request_id(request),
    }


@router.get("/business/referrals")
def business_referrals(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).referrals(user=user), "request_id": _request_id(request)}


@router.post("/business/referrals/apply")
def apply_referral(
    payload: ReferralApplyRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).apply_referral(user=user, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None, alias="Stripe-Signature")) -> dict:
    data = _service(request).stripe_webhook(raw_body=await request.body(), signature_header=stripe_signature, request_id=_request_id(request))
    return {"data": data, "request_id": _request_id(request)}


@router.get("/admin/credit-purchases")
def admin_credit_purchases(
    request: Request,
    status: str | None = Query(default=None),
    business_id: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).admin_list_purchases(user=user, status=status, business_id=business_id, cursor=cursor, limit=limit),
        "request_id": _request_id(request),
    }


@router.post("/admin/credit-purchases/{purchase_id}/approve")
def admin_approve_credit_purchase(
    purchase_id: str,
    payload: AdminReviewCreditPurchaseRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).admin_approve_purchase(
            user=user,
            purchase_id=purchase_id,
            payload=payload,
            request_id=_request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": _request_id(request),
    }


@router.post("/admin/credit-purchases/{purchase_id}/reject")
def admin_reject_credit_purchase(
    purchase_id: str,
    payload: AdminReviewCreditPurchaseRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).admin_reject_purchase(
            user=user,
            purchase_id=purchase_id,
            payload=payload,
            request_id=_request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": _request_id(request),
    }


@router.post("/admin/credits/adjust")
def admin_adjust_credits(
    payload: AdminCreditAdjustmentRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).admin_adjust(user=user, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }
