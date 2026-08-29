from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile

from app.auth.dependencies import require_current_user, require_current_user_with_terms
from app.modules.businesses.route_dependencies import (
    business_service as business_access_service,
)
from app.modules.credits.models import MAX_PROOF_SIZE_BYTES
from app.modules.credits.schemas import (
    AdminCreditAdjustmentRequest,
    AdminReviewCreditPurchaseRequest,
    BaseUsdcPaymentRequest,
    BaseUsdcTxHashRequest,
    ContractCreditPurchaseDismissRequest,
    CreditHandoffClaimRequest,
    CreditHandoffCreateRequest,
    CreditHandoffTokenRequest,
    ReferralApplyRequest,
    StripeCheckoutRequest,
)
from app.modules.credits.service import CreditService
from app.modules.legal.service import BusinessLegalService
from app.modules.operations import require_platform_operational
from app.modules.users.models import UserRecord
from app.shared.validation import read_limited_upload

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
        onchain_verifier=request.app.state.onchain_credit_verifier,
        admin_notifications=getattr(request.app.state, "admin_notification_service", None),
        user_repository=request.app.state.user_repository,
        handoff_store=request.app.state.credit_handoff_store,
        require_business_pin=lambda user: _require_business_pin(request, user),
    )


def _legal_service(request: Request) -> BusinessLegalService:
    return BusinessLegalService(
        business_repository=request.app.state.business_repository,
        legal_acceptance_repository=request.app.state.business_legal_acceptance_repository,
        audit_writer=request.app.state.audit_writer,
    )


def _require_business_pin(request: Request, user: UserRecord) -> None:
    business_access_service(request).require_unlocked_business_pin(user=user)


@router.get("/business/credits/wallet")
def business_credit_wallet(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).wallet(user=user), "request_id": _request_id(request)}


@router.get("/business/credits/ledger")
def business_credit_ledger(
    request: Request,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    type: str | None = Query(default=None),  # noqa: A002 - API contract uses "type".
    user: UserRecord = Depends(require_current_user_with_terms),
) -> dict:
    return {"data": _service(request).ledger(user=user, cursor=cursor, limit=limit, ledger_type=type), "request_id": _request_id(request)}


@router.post("/business/credits/stripe-checkout", status_code=201)
def create_stripe_checkout(
    payload: StripeCheckoutRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    require_platform_operational(request.app.state.emergency_mode_repository, operation="credit_stripe_checkout_create")
    _require_business_pin(request, user)
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
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    require_platform_operational(request.app.state.emergency_mode_repository, operation="credit_manual_payment_create")
    _require_business_pin(request, user)
    content = await read_limited_upload(
        file,
        max_bytes=MAX_PROOF_SIZE_BYTES,
        empty_or_too_large_error="MANUAL_PAYMENT_PROOF_REQUIRED",
    )
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


@router.post("/business/credits/base-payment", status_code=201)
def create_base_usdc_credit_payment(
    payload: BaseUsdcPaymentRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    require_platform_operational(request.app.state.emergency_mode_repository, operation="credit_base_payment_create")
    _legal_service(request).require_business_credit_terms(user=user)
    _require_business_pin(request, user)
    return {
        "data": _service(request).create_base_usdc_payment(user=user, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.get("/business/credits/purchases/pending-contract")
def business_pending_contract_credit_purchase(
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
) -> dict:
    return {
        "data": _service(request).pending_contract_purchase(user=user),
        "request_id": _request_id(request),
    }


@router.get("/business/credits/purchases/{purchase_id}")
def business_credit_purchase_detail(
    purchase_id: str,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
) -> dict:
    return {"data": _service(request).purchase_detail(user=user, purchase_id=purchase_id), "request_id": _request_id(request)}


@router.post("/business/credits/purchases/{purchase_id}/dismiss")
def dismiss_contract_credit_purchase(
    purchase_id: str,
    payload: ContractCreditPurchaseDismissRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
) -> dict:
    _require_business_pin(request, user)
    return {
        "data": _service(request).dismiss_contract_purchase(
            user=user,
            purchase_id=purchase_id,
            payload=payload,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.post("/business/credits/handoffs", status_code=201)
def create_credit_handoff(
    payload: CreditHandoffCreateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
) -> dict:
    require_platform_operational(request.app.state.emergency_mode_repository, operation="credit_wallet_handoff_create")
    _legal_service(request).require_business_credit_terms(user=user)
    _require_business_pin(request, user)
    return {
        "data": _service(request).create_credit_handoff(
            user=user,
            package_code=payload.package_code,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.post("/business/credits/handoffs/challenge")
def credit_handoff_challenge(
    payload: CreditHandoffTokenRequest,
    request: Request,
) -> dict:
    return {
        "data": _service(request).credit_handoff_challenge(token=payload.handoff_token),
        "request_id": _request_id(request),
    }


@router.post("/business/credits/handoffs/claim")
def claim_credit_handoff(
    payload: CreditHandoffClaimRequest,
    request: Request,
) -> dict:
    require_platform_operational(request.app.state.emergency_mode_repository, operation="credit_wallet_handoff_claim")
    return {
        "data": _service(request).claim_credit_handoff(
            token=payload.handoff_token,
            wallet_address=payload.wallet_address,
            chain_id=payload.chain_id,
            signature=payload.signature,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.get("/business/credits/handoffs/{handoff_id}")
def credit_handoff_status(
    handoff_id: str,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
) -> dict:
    return {
        "data": _service(request).credit_handoff_status(user=user, handoff_id=handoff_id),
        "request_id": _request_id(request),
    }


@router.post("/business/credits/purchases/{purchase_id}/tx-hash")
def submit_base_usdc_tx_hash(
    purchase_id: str,
    payload: BaseUsdcTxHashRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    _require_business_pin(request, user)
    return {
        "data": _service(request).submit_base_usdc_tx_hash(
            user=user,
            purchase_id=purchase_id,
            payload=payload,
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
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    _require_business_pin(request, user)
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


@router.get("/admin/credit-purchases/{purchase_id}")
def admin_credit_purchase_detail(
    purchase_id: str,
    request: Request,
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {"data": _service(request).admin_purchase_detail(user=user, purchase_id=purchase_id), "request_id": _request_id(request)}


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
