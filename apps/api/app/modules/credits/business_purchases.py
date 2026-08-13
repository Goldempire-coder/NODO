from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Any, Callable

from app.core.errors import ApiError
from app.modules.businesses.models import BusinessRecord
from app.modules.credits.models import ALLOWED_PROOF_MIME_TYPES, BASE_USDC_TOKEN_SYMBOL, CREDIT_PACKAGES, MAX_PROOF_SIZE_BYTES, CreditPurchaseRecord, utc_now
from app.modules.credits.onchain import price_to_usdc_units, validate_evm_address, validate_tx_hash
from app.modules.credits.schemas import BaseUsdcPaymentRequest, BaseUsdcTxHashRequest, StripeCheckoutRequest
from app.modules.credits.serializers import file_public, purchase_public
from app.modules.users.models import UserRecord
from app.shared.document_uploads import validate_document_upload


def _mask_tx_hash(value: str, keep: int = 8) -> str:
    return f"***{value[-keep:]}" if len(value) > keep else "*" * len(value)


class CreditBusinessPurchases:
    def __init__(
        self,
        *,
        settings,
        repository,
        audit_writer,
        idempotency_store,
        storage,
        onchain_verifier,
        rate_limit: Callable[[str, str], None],
        require_idempotency_key: Callable[[str | None], str],
        admin_notifications=None,
    ) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._audit = audit_writer
        self._idempotency = idempotency_store
        self._storage = storage
        self._onchain_verifier = onchain_verifier
        self._rate_limit = rate_limit
        self._require_idempotency_key = require_idempotency_key
        self._admin_notifications = admin_notifications

    def create_stripe_checkout(self, *, user: UserRecord, business: BusinessRecord, payload: StripeCheckoutRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        self._rate_limit("stripe_checkout", business.id)
        stable_key = self._require_idempotency_key(idempotency_key)

        def compute() -> dict[str, Any]:
            package = CREDIT_PACKAGES.get(payload.package_code)
            if package is None:
                raise ApiError("INVALID_PACKAGE", status_code=400)
            self._repository.ensure_wallet(business.id)
            purchase = self._repository.create_stripe_purchase(business_id=business.id, package_code=payload.package_code, idempotency_key=stable_key)
            self._audit.write(event_type="credit_purchase_created", actor_user_id=user.id, actor_role=user.role, resource_type="credit_purchase", resource_id=purchase.id, request_id=request_id)
            self._audit.write(event_type="stripe_checkout_started", actor_user_id=user.id, actor_role=user.role, resource_type="credit_purchase", resource_id=purchase.id, request_id=request_id)
            return {
                "purchase": purchase_public(purchase),
                "checkout_url": self._checkout_url(purchase),
                "disclaimer": "Stripe checkout inicia la compra; el redirect no acredita creditos.",
            }

        return self._idempotency.replay_or_store(
            f"credits:stripe_checkout:{business.id}:{stable_key}",
            payload=payload.model_dump(),
            compute=compute,
        )

    def create_base_usdc_payment(self, *, user: UserRecord, business: BusinessRecord, payload: BaseUsdcPaymentRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        self._rate_limit("base_usdc_payment", business.id)
        stable_key = self._require_idempotency_key(idempotency_key)

        def compute() -> dict[str, Any]:
            package = CREDIT_PACKAGES.get(payload.package_code)
            if package is None:
                raise ApiError("INVALID_PACKAGE", status_code=400)
            if payload.token_symbol != BASE_USDC_TOKEN_SYMBOL:
                raise ApiError("ONCHAIN_TOKEN_NOT_ALLOWED", status_code=400)
            try:
                destination_wallet = validate_evm_address(self._settings.nodo_credit_receiving_wallet_base or "")
            except ApiError as exc:
                raise ApiError("ONCHAIN_RECEIVING_WALLET_NOT_CONFIGURED", status_code=503) from exc
            expected_units = price_to_usdc_units(package["price_usd"])
            expires_at = utc_now() + timedelta(minutes=self._settings.onchain_credit_purchase_ttl_minutes)
            self._repository.ensure_wallet(business.id)
            purchase = self._repository.create_base_usdc_purchase(
                business_id=business.id,
                package_code=payload.package_code,
                idempotency_key=stable_key,
                expected_amount_units=expected_units,
                destination_wallet_address=destination_wallet,
                expires_at=expires_at,
            )
            self._audit.write(event_type="onchain_credit_purchase_created", actor_user_id=user.id, actor_role=user.role, resource_type="credit_purchase", resource_id=purchase.id, request_id=request_id)
            return {
                "purchase": purchase_public(purchase),
                "payment": {
                    "network": purchase.network,
                    "chain_id": purchase.chain_id,
                    "token_symbol": purchase.token_symbol,
                    "token_contract_address": purchase.token_contract_address,
                    "token_decimals": purchase.token_decimals,
                    "expected_amount_units": str(purchase.expected_amount_units),
                    "expected_amount_display": str(purchase.price_usd),
                    "destination_wallet_address": purchase.destination_wallet_address,
                    "min_confirmations": self._settings.onchain_credit_min_confirmations,
                    "expires_at": purchase.expires_at.isoformat() if purchase.expires_at else None,
                },
                "disclaimer": "Base USDC inicia la compra; solo la verificacion on-chain del backend acredita creditos.",
            }

        return self._idempotency.replay_or_store(
            f"credits:base_usdc_payment:{business.id}:{stable_key}",
            payload=payload.model_dump(),
            compute=compute,
        )

    def submit_base_usdc_tx_hash(
        self,
        *,
        user: UserRecord,
        business: BusinessRecord,
        purchase_id: str,
        payload: BaseUsdcTxHashRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        self._rate_limit("base_usdc_tx_hash", business.id)
        stable_key = self._require_idempotency_key(idempotency_key)
        tx_hash = validate_tx_hash(payload.tx_hash)

        def compute() -> dict[str, Any]:
            purchase = self._repository.get_purchase(purchase_id)
            if purchase is None or purchase.business_id != business.id:
                raise ApiError("PURCHASE_NOT_FOUND", status_code=404)
            if purchase.payment_method != "base_usdc_onchain":
                raise ApiError("PURCHASE_STATUS_INVALID", status_code=409)
            if purchase.status in {"expired", "rejected", "verification_failed"}:
                raise ApiError("PURCHASE_STATUS_INVALID", status_code=409)
            if purchase.expected_amount_units is None or not purchase.destination_wallet_address:
                raise ApiError("ONCHAIN_VERIFICATION_FAILED", status_code=409)
            verification = self._onchain_verifier.verify(
                tx_hash=tx_hash,
                expected_amount_units=purchase.expected_amount_units,
                destination_wallet_address=purchase.destination_wallet_address,
                min_confirmations=self._settings.onchain_credit_min_confirmations,
            )
            updated, ledger = self._repository.apply_onchain_verification(purchase=purchase, verification=verification, actor_user_id=user.id)
            event_type = "onchain_credit_purchase_credited" if ledger else f"onchain_credit_purchase_{updated.status}"
            self._audit.write(event_type=event_type, actor_user_id=user.id, actor_role=user.role, resource_type="credit_purchase", resource_id=purchase.id, request_id=request_id, metadata_json={"tx_hash_masked": _mask_tx_hash(tx_hash), "status": updated.status})
            if updated.status in {"under_review", "verification_failed", "failed", "expired"} and self._admin_notifications is not None:
                self._admin_notifications.credit_purchase_attention(purchase=updated, reason=updated.status, request_id=request_id)
            if ledger:
                self._audit.write(event_type="credits_added", actor_user_id=user.id, actor_role=user.role, resource_type="credit_purchase", resource_id=purchase.id, request_id=request_id, metadata_json={"ledger_id": ledger.id, "amount": updated.credits_amount})
            return {"purchase": purchase_public(updated), "credited": ledger is not None}

        return self._idempotency.replay_or_store(
            f"credits:base_usdc_tx:{business.id}:{purchase_id}:{stable_key}",
            payload={"purchase_id": purchase_id, "tx_hash": tx_hash},
            compute=compute,
        )

    def create_manual_payment(
        self,
        *,
        user: UserRecord,
        business: BusinessRecord,
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
        self._rate_limit("manual_payment", business.id)
        stable_key = self._require_idempotency_key(idempotency_key)
        if not content or len(content) > MAX_PROOF_SIZE_BYTES:
            raise ApiError("MANUAL_PAYMENT_PROOF_REQUIRED", status_code=400)
        validated_file = validate_document_upload(
            content=content,
            declared_mime_type=mime_type,
            invalid_error_code="MANUAL_PAYMENT_PROOF_REQUIRED",
        )
        content_hash = hashlib.sha256(content).hexdigest()

        def compute() -> dict[str, Any]:
            return self._compute_manual_payment(
                user=user,
                business=business,
                package_code=package_code,
                payment_method=payment_method,
                manual_payment_reference=manual_payment_reference,
                manual_tx_hash=manual_tx_hash,
                manual_network=manual_network,
                file_name=validated_file.storage_file_name,
                mime_type=validated_file.mime_type,
                content=content,
                content_hash=content_hash,
                stable_key=stable_key,
                request_id=request_id,
            )

        return self._idempotency.replay_or_store(
            f"credits:manual:{business.id}:{stable_key}",
            payload={
                "package_code": package_code,
                "payment_method": payment_method,
                "manual_payment_reference": manual_payment_reference,
                "manual_tx_hash": manual_tx_hash,
                "manual_network": manual_network,
                "mime_type": validated_file.mime_type,
                "content_hash": content_hash,
            },
            compute=compute,
        )

    def _compute_manual_payment(
        self,
        *,
        user: UserRecord,
        business: BusinessRecord,
        package_code: str,
        payment_method: str,
        manual_payment_reference: str | None,
        manual_tx_hash: str | None,
        manual_network: str | None,
        file_name: str,
        mime_type: str,
        content: bytes,
        content_hash: str,
        stable_key: str,
        request_id: str,
    ) -> dict[str, Any]:
        self._validate_manual_payment(
            package_code=package_code,
            payment_method=payment_method,
            manual_payment_reference=manual_payment_reference,
            manual_tx_hash=manual_tx_hash,
            manual_network=manual_network,
            mime_type=mime_type,
            content=content,
        )
        self._repository.ensure_wallet(business.id)
        stored = self._storage.store_credit_purchase_proof(
            business_id=business.id,
            purchase_id="pending",
            file_id=content_hash[:16],
            file_name=file_name,
            content=content,
        )
        purchase, file = self._repository.create_manual_purchase(
            business_id=business.id,
            owner_user_id=user.id,
            package_code=package_code,
            payment_method=payment_method,
            idempotency_key=stable_key,
            storage_path=stored.storage_path,
            mime_type=mime_type,
            size_bytes=stored.size_bytes,
            manual_payment_reference=manual_payment_reference,
            manual_tx_hash=manual_tx_hash,
            manual_network=manual_network,
        )
        self._audit_manual_payment_submitted(user=user, purchase=purchase, request_id=request_id)
        return {
            "purchase": purchase_public(purchase),
            "proof": file_public(file),
            "disclaimer": "Pago manual enviado a revision. Solo aprobacion admin acredita creditos.",
        }

    def _validate_manual_payment(
        self,
        *,
        package_code: str,
        payment_method: str,
        manual_payment_reference: str | None,
        manual_tx_hash: str | None,
        manual_network: str | None,
        mime_type: str,
        content: bytes,
    ) -> None:
        if package_code not in CREDIT_PACKAGES:
            raise ApiError("INVALID_PACKAGE", status_code=400)
        if payment_method not in {"zelle_manual_admin_approved", "usdt_manual_admin_approved"}:
            raise ApiError("INVALID_PAYMENT_METHOD", status_code=400)
        if mime_type not in ALLOWED_PROOF_MIME_TYPES:
            raise ApiError("MANUAL_PAYMENT_PROOF_REQUIRED", status_code=400)
        if payment_method == "zelle_manual_admin_approved" and not manual_payment_reference:
            raise ApiError("VALIDATION_ERROR", status_code=422)
        if payment_method == "usdt_manual_admin_approved" and (not manual_tx_hash or manual_network != "TRC20"):
            raise ApiError("VALIDATION_ERROR", status_code=422)

    def _audit_manual_payment_submitted(self, *, user: UserRecord, purchase, request_id: str) -> None:  # type: ignore[no-untyped-def]
        self._audit.write(event_type="credit_purchase_created", actor_user_id=user.id, actor_role=user.role, resource_type="credit_purchase", resource_id=purchase.id, request_id=request_id)
        self._audit.write(event_type="manual_credit_payment_submitted", actor_user_id=user.id, actor_role=user.role, resource_type="credit_purchase", resource_id=purchase.id, request_id=request_id)

    def _checkout_url(self, purchase: CreditPurchaseRecord) -> str:
        if self._settings.app_env != "test" and not self._settings.stripe_secret_key:
            raise ApiError("STRIPE_SESSION_INVALID", status_code=503)
        return f"https://checkout.stripe.test/pay/{purchase.stripe_checkout_session_id}"
