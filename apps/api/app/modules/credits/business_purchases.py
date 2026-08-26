from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.errors import ApiError
from app.modules.businesses.models import BusinessRecord
from app.modules.credits.models import (
    ALLOWED_PROOF_MIME_TYPES,
    BASE_USDC_TOKEN_SYMBOL,
    CREDIT_PACKAGES,
    MAX_PROOF_SIZE_BYTES,
    CreditPurchaseRecord,
    CreditPaymentNetworkProfile,
    credit_payment_network_profile,
    utc_now,
)
from app.modules.credits.onchain import (
    normalize_credit_verification,
    price_to_usdc_units,
    validate_evm_address,
    validate_tx_hash,
)
from app.modules.credits.payment_authorizations import (
    PaymentAuthorizationSnapshot,
    authorization_is_expired,
    build_payment_authorization_typed_data,
    new_purchase_ref,
    normalize_payment_address,
    sign_payment_authorization,
)
from app.modules.credits.schemas import (
    BaseUsdcPaymentRequest,
    BaseUsdcTxHashRequest,
    ContractBaseUsdcPaymentRequest,
    LegacyBaseUsdcPaymentRequest,
    StripeCheckoutRequest,
)
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
        contract_rate_limit: Callable[[str, str], None] | None = None,
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
        self._contract_rate_limit = contract_rate_limit or (
            lambda _user_id, business_id: rate_limit("base_usdc_contract_payment", business_id)
        )
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
        if isinstance(payload, ContractBaseUsdcPaymentRequest):
            return self._create_contract_payment(
                user=user,
                business=business,
                payload=payload,
                request_id=request_id,
                idempotency_key=idempotency_key,
            )
        if self._contract_payment_mode_configured():
            raise ApiError("VALIDATION_ERROR", status_code=422)
        if not self._settings.legacy_credit_payment_methods_enabled:
            raise ApiError("CREDIT_PAYMENT_METHOD_DISABLED", status_code=410)
        return self._create_legacy_base_usdc_payment(
            user=user,
            business=business,
            payload=payload,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    def _contract_payment_mode_configured(self) -> bool:
        return any(
            (
                self._settings.nodo_credit_payment_contract_address,
                self._settings.nodo_credit_payment_network,
                self._settings.nodo_credit_payment_contract_version,
                self._settings.nodo_credit_auth_signer_key,
                self._settings.nodo_credit_auth_signer_address,
                self._settings.nodo_credit_auth_signer_version,
                self._settings.nodo_credit_payment_contract_paused,
            )
        )

    def _create_legacy_base_usdc_payment(
        self,
        *,
        user: UserRecord,
        business: BusinessRecord,
        payload: LegacyBaseUsdcPaymentRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
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
                self._audit.write(
                    event_type="onchain_receiving_wallet_configuration_invalid",
                    actor_user_id=user.id,
                    actor_role=user.role,
                    resource_type="business",
                    resource_id=business.id,
                    request_id=request_id,
                    metadata_json={"code": "ONCHAIN_RECEIVING_WALLET_NOT_CONFIGURED"},
                )
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

    def _create_contract_payment(
        self,
        *,
        user: UserRecord,
        business: BusinessRecord,
        payload: ContractBaseUsdcPaymentRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        self._contract_rate_limit(user.id, business.id)
        stable_key = self._require_idempotency_key(idempotency_key)
        payer_address = normalize_payment_address(payload.payer_wallet_address)

        def compute() -> dict[str, Any]:
            package = CREDIT_PACKAGES.get(payload.package_code)
            if package is None:
                raise ApiError("INVALID_PACKAGE", status_code=400)
            existing = self._repository.get_contract_purchase_by_idempotency(
                business_id=business.id,
                idempotency_key=stable_key,
            )
            if existing is not None:
                if (
                    existing.payment_method != "base_usdc_contract"
                    or existing.package_code != payload.package_code
                    or existing.onchain_payer_address != payer_address
                ):
                    raise ApiError("IDEMPOTENCY_PAYLOAD_MISMATCH", status_code=409)
                return self._contract_payment_response(existing)
            if (
                self._repository.count_pending_contract_purchases(business.id)
                >= self._settings.credit_contract_pending_purchase_limit
            ):
                raise ApiError("CRYPTO_PAYMENT_PENDING_LIMIT_REACHED", status_code=409)
            contract_address, treasury_address, network_profile = self._contract_configuration()
            signed_at = utc_now()
            valid_until = int(signed_at.timestamp()) + self._settings.onchain_credit_authorization_ttl_minutes * 60
            authorization_expires_at = datetime.fromtimestamp(valid_until, tz=timezone.utc)
            snapshot = PaymentAuthorizationSnapshot(
                purchase_ref=new_purchase_ref(),
                payer=payer_address,
                amount=price_to_usdc_units(package["price_usd"]),
                valid_until=valid_until,
                chain_id=network_profile.chain_id,
                verifying_contract=contract_address,
                contract_version=self._settings.nodo_credit_payment_contract_version,
            )
            signed = sign_payment_authorization(
                snapshot,
                signer_key=self._settings.nodo_credit_auth_signer_key or "",
                configured_signer_address=self._settings.nodo_credit_auth_signer_address or "",
            )
            purchase, created = self._repository.create_contract_purchase(
                business_id=business.id,
                package_code=payload.package_code,
                idempotency_key=stable_key,
                expected_amount_units=snapshot.amount,
                chain_id=network_profile.chain_id,
                network=network_profile.network,
                token_symbol=network_profile.token_symbol,
                token_contract_address=network_profile.token_contract_address,
                token_decimals=network_profile.token_decimals,
                destination_wallet_address=treasury_address,
                purchase_ref=snapshot.purchase_ref,
                payer_address=payer_address,
                contract_address=contract_address,
                contract_version=snapshot.contract_version,
                authorization_expires_at=authorization_expires_at,
                authorization_digest=signed.digest,
                authorization_signature=signed.signature,
                signer_address=signed.signer_address,
                signer_version=self._settings.nodo_credit_auth_signer_version or "",
                signed_at=signed_at,
                max_pending=self._settings.credit_contract_pending_purchase_limit,
            )
            if created:
                self._audit.write(
                    event_type="crypto_contract_credit_purchase_authorized",
                    actor_user_id=user.id,
                    actor_role=user.role,
                    resource_type="credit_purchase",
                    resource_id=purchase.id,
                    request_id=request_id,
                    metadata_json={
                        "payment_method": "base_usdc_contract",
                        "signer_version": purchase.payment_authorization_signer_version,
                    },
                )
            return self._contract_payment_response(purchase)

        response = self._idempotency.replay_or_store(
            f"credits:base_usdc_payment:{business.id}:{stable_key}",
            payload={"package_code": payload.package_code, "payer_wallet_address": payer_address},
            compute=compute,
        )
        payment = response.get("payment")
        valid_until = payment.get("authorization_valid_until") if isinstance(payment, dict) else None
        if not isinstance(valid_until, int):
            raise ApiError("CRYPTO_PAYMENT_AUTHORIZATION_REISSUE_REQUIRED", status_code=409)
        if authorization_is_expired(valid_until=valid_until, now=utc_now()):
            raise ApiError("CRYPTO_PAYMENT_AUTHORIZATION_EXPIRED", status_code=409)
        return response

    def _contract_configuration(self) -> tuple[str, str, CreditPaymentNetworkProfile]:
        if self._settings.nodo_credit_payment_contract_paused:
            raise ApiError(
                "CRYPTO_PAYMENT_CONTRACT_PAUSED",
                message="Este metodo de pago no esta disponible temporalmente.",
                status_code=503,
            )
        network_profile = credit_payment_network_profile(self._settings.nodo_credit_payment_network)
        if network_profile is None:
            raise ApiError(
                "CRYPTO_CONTRACT_PAYMENT_NOT_CONFIGURED",
                message="Este metodo de pago no esta disponible temporalmente.",
                status_code=503,
            )
        try:
            contract_address = normalize_payment_address(self._settings.nodo_credit_payment_contract_address or "")
            treasury_address = normalize_payment_address(self._settings.nodo_credit_receiving_wallet_base or "")
        except ApiError as exc:
            raise ApiError(
                "CRYPTO_CONTRACT_PAYMENT_NOT_CONFIGURED",
                message="Este metodo de pago no esta disponible temporalmente.",
                status_code=503,
            ) from exc
        if self._settings.nodo_credit_payment_contract_version is None:
            raise ApiError(
                "CRYPTO_CONTRACT_PAYMENT_NOT_CONFIGURED",
                message="Este metodo de pago no esta disponible temporalmente.",
                status_code=503,
            )
        if not self._settings.nodo_credit_auth_signer_key or not self._settings.nodo_credit_auth_signer_address or not self._settings.nodo_credit_auth_signer_version:
            raise ApiError(
                "CRYPTO_PAYMENT_SIGNER_UNAVAILABLE",
                message="No pudimos preparar el pago en este momento.",
                status_code=503,
            )
        return contract_address, treasury_address, network_profile

    def ensure_contract_payment_available(self) -> None:
        self._contract_configuration()

    def contract_network_profile(self) -> CreditPaymentNetworkProfile:
        return self._contract_configuration()[2]

    def contract_purchase_detail_for_id(
        self,
        purchase_id: str,
        *,
        business_id: str,
    ) -> dict[str, Any]:
        purchase = self._repository.get_purchase(purchase_id)
        if (
            purchase is None
            or purchase.business_id != business_id
            or purchase.payment_method != "base_usdc_contract"
        ):
            raise ApiError("PURCHASE_NOT_FOUND", status_code=404)
        return self.contract_purchase_detail(purchase)

    def _contract_payment_response(self, purchase: CreditPurchaseRecord) -> dict[str, Any]:
        response = self.contract_purchase_detail(purchase)
        authorization_status = response["payment"]["authorization_status"]
        if authorization_status == "expired":
            raise ApiError("CRYPTO_PAYMENT_AUTHORIZATION_EXPIRED", status_code=409)
        if authorization_status != "valid":
            raise ApiError("CRYPTO_PAYMENT_AUTHORIZATION_REISSUE_REQUIRED", status_code=409)
        return response

    def contract_purchase_detail(self, purchase: CreditPurchaseRecord) -> dict[str, Any]:
        valid_until = (
            int(purchase.payment_authorization_expires_at.timestamp())
            if purchase.payment_authorization_expires_at is not None
            else None
        )
        authorization_status = self._contract_authorization_status(
            purchase,
            valid_until=valid_until,
        )
        network_profile = credit_payment_network_profile(purchase.network)
        payment: dict[str, Any] = {
            "network": purchase.network,
            "chain_id": purchase.chain_id,
            "network_display_name": network_profile.display_name if network_profile else None,
            "is_testnet": network_profile.is_testnet if network_profile else None,
            "token_symbol": purchase.token_symbol,
            "token_contract_address": purchase.token_contract_address,
            "token_decimals": purchase.token_decimals,
            "expected_amount_units": (
                str(purchase.expected_amount_units)
                if purchase.expected_amount_units is not None
                else None
            ),
            "expected_amount_display": str(purchase.price_usd),
            "contract_address": purchase.payment_contract_address,
            "contract_version": purchase.payment_contract_version,
            "purchase_ref": purchase.onchain_purchase_ref,
            "payer_wallet_address": purchase.onchain_payer_address,
            "authorization_valid_until": valid_until,
            "authorization_status": authorization_status,
            "capabilities": {"can_pay": authorization_status == "valid"},
            "min_confirmations": self._settings.onchain_credit_min_confirmations,
        }
        if authorization_status == "valid":
            snapshot = PaymentAuthorizationSnapshot(
                purchase_ref=purchase.onchain_purchase_ref,
                payer=purchase.onchain_payer_address,
                amount=purchase.expected_amount_units,
                valid_until=valid_until,
                chain_id=purchase.chain_id,
                verifying_contract=purchase.payment_contract_address,
                contract_version=purchase.payment_contract_version,
            )
            payment["authorization_typed_data"] = build_payment_authorization_typed_data(snapshot)
            payment["authorization_signature"] = purchase.payment_authorization_signature
        return {
            "purchase": purchase_public(purchase),
            "payment": payment,
            "disclaimer": "La autorizacion inicia una compra de creditos; firmarla no acredita creditos.",
        }

    def _contract_authorization_status(
        self,
        purchase: CreditPurchaseRecord,
        *,
        valid_until: int | None,
    ) -> str:
        if not self._contract_snapshot_is_complete(purchase, valid_until=valid_until):
            return "reissue_required"
        if not self._contract_snapshot_matches_configuration(purchase):
            return "reissue_required"
        if authorization_is_expired(valid_until=valid_until, now=utc_now()):
            return "expired"
        return "valid"

    @staticmethod
    def _contract_snapshot_is_complete(
        purchase: CreditPurchaseRecord,
        *,
        valid_until: int | None,
    ) -> bool:
        return bool(
            purchase.expected_amount_units is not None
            and valid_until is not None
            and purchase.payment_contract_version is not None
            and purchase.onchain_purchase_ref
            and purchase.onchain_payer_address
            and purchase.payment_contract_address
            and purchase.payment_authorization_digest
            and purchase.payment_authorization_signature
            and purchase.payment_authorization_signer_address
            and purchase.payment_authorization_signer_version
            and purchase.payment_authorization_signed_at
        )

    def _contract_snapshot_matches_configuration(self, purchase: CreditPurchaseRecord) -> bool:
        profile = credit_payment_network_profile(self._settings.nodo_credit_payment_network)
        if profile is None:
            return False
        try:
            contract_address = normalize_payment_address(
                self._settings.nodo_credit_payment_contract_address or ""
            )
            treasury_address = normalize_payment_address(
                self._settings.nodo_credit_receiving_wallet_base or ""
            )
            signer_address = normalize_payment_address(
                self._settings.nodo_credit_auth_signer_address or ""
            )
            payer_address = normalize_payment_address(purchase.onchain_payer_address or "")
            stored_contract = normalize_payment_address(purchase.payment_contract_address or "")
            stored_treasury = normalize_payment_address(
                purchase.destination_wallet_address or ""
            )
            stored_signer = normalize_payment_address(
                purchase.payment_authorization_signer_address or ""
            )
        except ApiError:
            return False
        return bool(
            not self._settings.nodo_credit_payment_contract_paused
            and payer_address == purchase.onchain_payer_address
            and stored_contract == contract_address
            and stored_treasury == treasury_address
            and stored_signer == signer_address
            and purchase.payment_contract_version
            == self._settings.nodo_credit_payment_contract_version
            and purchase.payment_authorization_signer_version
            == self._settings.nodo_credit_auth_signer_version
            and purchase.chain_id == profile.chain_id
            and purchase.network == profile.network
            and purchase.token_symbol == profile.token_symbol
            and purchase.token_contract_address == profile.token_contract_address
            and purchase.token_decimals == profile.token_decimals
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
            if purchase.payment_method == "base_usdc_contract":
                raise ApiError("CRYPTO_PAYMENT_TX_HASH_NOT_ACCEPTED", status_code=409)
            if purchase.payment_method != "base_usdc_onchain":
                raise ApiError("PURCHASE_STATUS_INVALID", status_code=409)
            if purchase.status == "credited":
                return {"purchase": purchase_public(purchase), "credited": False}
            if purchase.status not in {"pending_payment", "pending_onchain_confirmation", "detected"}:
                raise ApiError("PURCHASE_STATUS_INVALID", status_code=409)
            if purchase.expected_amount_units is None or not purchase.destination_wallet_address:
                raise ApiError("ONCHAIN_VERIFICATION_FAILED", status_code=409)
            self._audit.write(
                event_type="onchain_tx_hash_submitted",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="credit_purchase",
                resource_id=purchase.id,
                request_id=request_id,
                metadata_json={"tx_hash_masked": _mask_tx_hash(tx_hash)},
            )
            try:
                verification = self._onchain_verifier.verify(
                    tx_hash=tx_hash,
                    expected_amount_units=purchase.expected_amount_units,
                    destination_wallet_address=purchase.destination_wallet_address,
                    min_confirmations=self._settings.onchain_credit_min_confirmations,
                )
                verification = normalize_credit_verification(
                    purchase=purchase,
                    verification=verification,
                    submitted_tx_hash=tx_hash,
                    min_confirmations=self._settings.onchain_credit_min_confirmations,
                    now=utc_now(),
                )
                updated, ledger = self._repository.apply_onchain_verification(
                    purchase=purchase,
                    verification=verification,
                    actor_user_id=user.id,
                    min_confirmations=self._settings.onchain_credit_min_confirmations,
                )
            except ApiError as exc:
                self._audit.write(
                    event_type="onchain_payment_verification_failed",
                    actor_user_id=user.id,
                    actor_role=user.role,
                    resource_type="credit_purchase",
                    resource_id=purchase.id,
                    request_id=request_id,
                    metadata_json={"tx_hash_masked": _mask_tx_hash(tx_hash), "code": exc.code},
                )
                raise
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
