from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.businesses.access_control import require_active_business_access
from app.modules.businesses.models import BusinessRecord
from app.modules.credits.admin_actions import CreditAdminActions
from app.modules.credits.business_purchases import CreditBusinessPurchases
from app.modules.credits.business_referrals import (
    CREDITS_DISCLAIMER,
    CreditBusinessReferrals,
)
from app.modules.credits.schemas import (
    AdminCreditAdjustmentRequest,
    AdminReviewCreditPurchaseRequest,
    BaseUsdcPaymentRequest,
    BaseUsdcTxHashRequest,
    ReferralApplyRequest,
    StripeCheckoutRequest,
)
from app.modules.credits.serializers import ledger_public, purchase_public
from app.modules.credits.stripe_webhook import parse_stripe_webhook_event
from app.modules.users.models import UserRecord
from app.shared.rate_limit.redis import RateLimitUnavailableError
from app.shared.rate_limit.request_identity import current_request_ip_hash


class CreditService:
    def __init__(
        self,
        *,
        settings,
        repository,
        business_repository,
        audit_writer,
        rate_limiter,
        idempotency_store,
        storage,
        onchain_verifier,
        admin_notifications=None,
    ) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._businesses = business_repository
        self._audit = audit_writer
        self._rate_limiter = rate_limiter
        self._idempotency = idempotency_store
        self._storage = storage
        self._onchain_verifier = onchain_verifier
        self._admin_notifications = admin_notifications
        self._business_purchases = CreditBusinessPurchases(
            settings=self._settings,
            repository=self._repository,
            audit_writer=self._audit,
            idempotency_store=self._idempotency,
            storage=self._storage,
            onchain_verifier=self._onchain_verifier,
            rate_limit=self._rate_limit,
            contract_rate_limit=self._contract_rate_limit,
            require_idempotency_key=self._require_idempotency_key,
            admin_notifications=self._admin_notifications,
        )
        self._business_referrals = CreditBusinessReferrals(
            repository=self._repository,
            audit_writer=self._audit,
            idempotency_store=self._idempotency,
            rate_limit=self._rate_limit,
            require_idempotency_key=self._require_idempotency_key,
        )
        self._admin_actions = CreditAdminActions(
            repository=self._repository,
            business_repository=self._businesses,
            audit_writer=self._audit,
            idempotency_store=self._idempotency,
            rate_limit=self._rate_limit,
            require_idempotency_key=self._require_idempotency_key,
        )

    def _rate_limit(self, action: str, key: str) -> None:
        if not self._rate_limiter.allow(
            f"credits:{action}:{key}",
            max_attempts=self._settings.business_rate_limit_max_attempts,
            window_seconds=self._settings.business_rate_limit_window_seconds,
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def _require_idempotency_key(self, idempotency_key: str | None) -> str:
        if not idempotency_key or not idempotency_key.strip():
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        return idempotency_key.strip()

    def _contract_rate_limit(self, user_id: str, business_id: str) -> None:
        keys_and_limits = (
            (
                f"credits:base_usdc_contract_payment:user:{user_id}",
                self._settings.credit_contract_rate_limit_user_max_attempts,
            ),
            (
                f"credits:base_usdc_contract_payment:business:{business_id}",
                self._settings.credit_contract_rate_limit_business_max_attempts,
            ),
            (
                f"credits:base_usdc_contract_payment:ip:{current_request_ip_hash()}",
                self._settings.credit_contract_rate_limit_ip_max_attempts,
            ),
        )
        require_shared = self._settings.app_env in {"staging", "production"}
        allow_shared = getattr(self._rate_limiter, "allow_shared", None)
        if require_shared and allow_shared is None:
            raise ApiError("CRYPTO_PAYMENT_RATE_LIMIT_UNAVAILABLE", status_code=503)
        for key, max_attempts in keys_and_limits:
            try:
                if require_shared:
                    allowed = allow_shared(
                        key,
                        max_attempts=max_attempts,
                        window_seconds=self._settings.credit_contract_rate_limit_window_seconds,
                    )
                else:
                    allowed = self._rate_limiter.allow(
                        key,
                        max_attempts=max_attempts,
                        window_seconds=self._settings.credit_contract_rate_limit_window_seconds,
                    )
            except RateLimitUnavailableError as exc:
                raise ApiError("CRYPTO_PAYMENT_RATE_LIMIT_UNAVAILABLE", status_code=503) from exc
            if not allowed:
                raise ApiError("RATE_LIMITED", status_code=429)

    def _owner_business(self, user: UserRecord) -> BusinessRecord:
        business, _ = require_active_business_access(user=user, business_repository=self._businesses)
        return business

    def wallet(self, *, user: UserRecord) -> dict[str, Any]:
        business = self._owner_business(user)
        self._rate_limit("wallet", business.id)
        wallet = self._repository.ensure_wallet(business.id)
        return {
            "wallet": {
                "business_id": business.id,
                "available_credits": wallet.available_credits,
                "blocked_credits": wallet.blocked_credits,
                "consumed_credits": wallet.consumed_credits,
                "lifetime_purchased_credits": wallet.lifetime_purchased_credits,
                "lifetime_bonus_credits": wallet.lifetime_bonus_credits,
                "lifetime_adjusted_credits": wallet.lifetime_adjusted_credits,
                "founder_status": business.founder_status,
                "founder_expires_at": business.founder_expires_at.isoformat() if business.founder_expires_at else None,
                "referral_credits_earned": business.referral_credits_earned,
            },
            "disclaimer": CREDITS_DISCLAIMER,
        }

    def ledger(self, *, user: UserRecord, cursor: str | None, limit: int, ledger_type: str | None) -> dict[str, Any]:
        business = self._owner_business(user)
        self._rate_limit("ledger", business.id)
        items, next_cursor = self._repository.list_ledger(business_id=business.id, ledger_type=ledger_type, cursor=cursor, limit=limit)
        return {
            "items": [ledger_public(item) for item in items],
            "next_cursor": next_cursor,
            "disclaimer": CREDITS_DISCLAIMER,
        }

    def create_stripe_checkout(self, *, user: UserRecord, payload: StripeCheckoutRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        if not self._settings.legacy_credit_payment_methods_enabled:
            raise ApiError("CREDIT_PAYMENT_METHOD_DISABLED", status_code=410)
        business = self._owner_business(user)
        return self._business_purchases.create_stripe_checkout(user=user, business=business, payload=payload, request_id=request_id, idempotency_key=idempotency_key)

    def create_base_usdc_payment(self, *, user: UserRecord, payload: BaseUsdcPaymentRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        business = self._owner_business(user)
        return self._business_purchases.create_base_usdc_payment(user=user, business=business, payload=payload, request_id=request_id, idempotency_key=idempotency_key)

    def purchase_detail(self, *, user: UserRecord, purchase_id: str) -> dict[str, Any]:
        business = self._owner_business(user)
        self._rate_limit("purchase_detail", business.id)
        purchase = self._repository.get_purchase(purchase_id)
        if purchase is None or purchase.business_id != business.id:
            raise ApiError("PURCHASE_NOT_FOUND", status_code=404)
        if purchase.payment_method == "base_usdc_contract":
            return self._business_purchases.contract_purchase_detail(purchase)
        return {"purchase": purchase_public(purchase), "disclaimer": CREDITS_DISCLAIMER}

    def submit_base_usdc_tx_hash(self, *, user: UserRecord, purchase_id: str, payload: BaseUsdcTxHashRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        business = self._owner_business(user)
        return self._business_purchases.submit_base_usdc_tx_hash(user=user, business=business, purchase_id=purchase_id, payload=payload, request_id=request_id, idempotency_key=idempotency_key)

    def create_manual_payment(
        self,
        *,
        user: UserRecord,
        package_code: str,
        payment_method: str,
        manual_payment_reference: str | None,
        manual_tx_hash: str | None,
        manual_network: str | None,
        file_name: str,
        mime_type: str,
        content: bytes,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        if not self._settings.legacy_credit_payment_methods_enabled:
            raise ApiError("CREDIT_PAYMENT_METHOD_DISABLED", status_code=410)
        business = self._owner_business(user)
        return self._business_purchases.create_manual_payment(
            user=user,
            business=business,
            package_code=package_code,
            payment_method=payment_method,
            manual_payment_reference=manual_payment_reference,
            manual_tx_hash=manual_tx_hash,
            manual_network=manual_network,
            file_name=file_name,
            mime_type=mime_type,
            content=content,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    def referrals(self, *, user: UserRecord) -> dict[str, Any]:
        business = self._owner_business(user)
        return self._business_referrals.referrals(user=user, business=business)

    def apply_referral(self, *, user: UserRecord, payload: ReferralApplyRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        business = self._owner_business(user)
        return self._business_referrals.apply_referral(user=user, business=business, payload=payload, request_id=request_id, idempotency_key=idempotency_key)

    def stripe_webhook(self, *, raw_body: bytes, signature_header: str | None, request_id: str) -> dict[str, Any]:
        self._rate_limit("stripe_webhook", "stripe")
        event = parse_stripe_webhook_event(raw_body=raw_body, signature_header=signature_header, webhook_secret=self._settings.stripe_webhook_secret)
        event_id = str(event.get("id") or "")
        event_type = str(event.get("type") or "")
        session = event.get("data", {}).get("object", {})
        session_id = str(session.get("id") or "")
        if not event_id or not session_id:
            raise ApiError("STRIPE_SESSION_INVALID", status_code=400)
        if self._repository.stripe_event_processed(event_id):
            return {"duplicate": True, "event_id": event_id, "credited": False}
        purchase = self._repository.find_purchase_by_checkout_session(session_id)
        if purchase is None:
            raise ApiError("STRIPE_SESSION_INVALID", status_code=404)
        if event_type not in {"checkout.session.completed", "payment_intent.succeeded"}:
            self._audit.write(event_type="stripe_payment_failed", actor_user_id=None, actor_role=None, resource_type="credit_purchase", resource_id=purchase.id, request_id=request_id, metadata_json={"stripe_event_id": event_id})
            return {"event_id": event_id, "credited": False}
        updated, ledger = self._repository.approve_purchase(
            purchase=purchase,
            actor_user_id=None,
            event_id=event_id,
            payment_intent_id=session.get("payment_intent"),
        )
        self._audit.write(event_type="stripe_payment_succeeded", actor_user_id=None, actor_role=None, resource_type="credit_purchase", resource_id=updated.id, request_id=request_id, metadata_json={"stripe_event_id": event_id})
        self._audit.write(event_type="credits_added", actor_user_id=None, actor_role=None, resource_type="credit_purchase", resource_id=updated.id, request_id=request_id, metadata_json={"ledger_id": ledger.id if ledger else None, "amount": updated.credits_amount})
        return {"purchase": purchase_public(updated), "credited": ledger is not None}

    def admin_list_purchases(self, *, user: UserRecord, status: str | None, business_id: str | None, cursor: str | None, limit: int) -> dict[str, Any]:
        return self._admin_actions.list_purchases(user=user, status=status, business_id=business_id, cursor=cursor, limit=limit)

    def admin_purchase_detail(self, *, user: UserRecord, purchase_id: str) -> dict[str, Any]:
        return self._admin_actions.purchase_detail(user=user, purchase_id=purchase_id)

    def admin_approve_purchase(self, *, user: UserRecord, purchase_id: str, payload: AdminReviewCreditPurchaseRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._admin_actions.approve_purchase(user=user, purchase_id=purchase_id, payload=payload, request_id=request_id, idempotency_key=idempotency_key)

    def admin_reject_purchase(self, *, user: UserRecord, purchase_id: str, payload: AdminReviewCreditPurchaseRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._admin_actions.reject_purchase(user=user, purchase_id=purchase_id, payload=payload, request_id=request_id, idempotency_key=idempotency_key)

    def admin_adjust(self, *, user: UserRecord, payload: AdminCreditAdjustmentRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._admin_actions.adjust(user=user, payload=payload, request_id=request_id, idempotency_key=idempotency_key)
