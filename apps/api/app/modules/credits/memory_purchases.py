from __future__ import annotations

from threading import RLock

from app.core.errors import ApiError
from app.modules.ads.models import CreditLedgerRecord, new_id, utc_now
from app.modules.businesses.models import FileAssetRecord
from app.modules.credits.models import (
    BASE_MAINNET_CHAIN_ID,
    BASE_MAINNET_NETWORK,
    BASE_USDC_CONTRACT_ADDRESS,
    BASE_USDC_DECIMALS,
    BASE_USDC_TOKEN_SYMBOL,
    CREDIT_PACKAGES,
    ONCHAIN_CREDIT_LEDGER_REASON,
    CreditPurchaseRecord,
)
from app.modules.credits.onchain import OnchainVerificationResult, normalize_credit_verification
from app.shared.keyset_pagination import paginate_descending


class InMemoryCreditPurchaseStore:
    def __init__(self, *, lock: RLock, files: dict[str, FileAssetRecord], purchases: dict[str, CreditPurchaseRecord]) -> None:
        self._lock = lock
        self.files = files
        self.purchases = purchases

    def create_stripe_purchase(self, *, business_id: str, package_code: str, idempotency_key: str) -> CreditPurchaseRecord:
        package = CREDIT_PACKAGES[package_code]
        with self._lock:
            purchase = CreditPurchaseRecord(
                id=new_id(),
                business_id=business_id,
                package_code=package_code,
                credits_amount=package["credits"],
                price_usd=package["price_usd"],
                payment_method="stripe_checkout",
                status="pending_payment",
                idempotency_key=idempotency_key,
            )
            purchase.stripe_checkout_session_id = f"cs_test_{purchase.id.replace('-', '')}"
            self.purchases[purchase.id] = purchase
            return purchase

    def create_manual_purchase(
        self,
        *,
        business_id: str,
        owner_user_id: str,
        package_code: str,
        payment_method: str,
        idempotency_key: str,
        storage_path: str,
        mime_type: str,
        size_bytes: int,
        manual_payment_reference: str | None,
        manual_tx_hash: str | None,
        manual_network: str | None,
    ) -> tuple[CreditPurchaseRecord, FileAssetRecord]:
        package = CREDIT_PACKAGES[package_code]
        with self._lock:
            purchase = CreditPurchaseRecord(
                id=new_id(),
                business_id=business_id,
                package_code=package_code,
                credits_amount=package["credits"],
                price_usd=package["price_usd"],
                payment_method=payment_method,
                status="pending_manual_review",
                idempotency_key=idempotency_key,
                manual_payment_reference=manual_payment_reference,
                manual_tx_hash=manual_tx_hash,
                manual_network=manual_network,
            )
            file = FileAssetRecord(
                id=new_id(),
                owner_user_id=owner_user_id,
                resource_type="credit_purchase",
                resource_id=purchase.id,
                file_type="credit_purchase_proof",
                storage_path=storage_path,
                mime_type=mime_type,
                size_bytes=size_bytes,
            )
            purchase.proof_file_id = file.id
            self.purchases[purchase.id] = purchase
            self.files[file.id] = file
            return purchase, file

    def create_base_usdc_purchase(
        self,
        *,
        business_id: str,
        package_code: str,
        idempotency_key: str,
        expected_amount_units: int,
        destination_wallet_address: str,
        expires_at,
    ) -> CreditPurchaseRecord:  # type: ignore[no-untyped-def]
        package = CREDIT_PACKAGES[package_code]
        with self._lock:
            purchase = CreditPurchaseRecord(
                id=new_id(),
                business_id=business_id,
                package_code=package_code,
                credits_amount=package["credits"],
                price_usd=package["price_usd"],
                payment_method="base_usdc_onchain",
                status="pending_payment",
                idempotency_key=idempotency_key,
                chain_id=BASE_MAINNET_CHAIN_ID,
                network=BASE_MAINNET_NETWORK,
                token_symbol=BASE_USDC_TOKEN_SYMBOL,
                token_contract_address=BASE_USDC_CONTRACT_ADDRESS,
                token_decimals=BASE_USDC_DECIMALS,
                expected_amount_units=expected_amount_units,
                destination_wallet_address=destination_wallet_address,
                verification_status="pending_payment",
                expires_at=expires_at,
            )
            self.purchases[purchase.id] = purchase
            return purchase

    def get_purchase(self, purchase_id: str) -> CreditPurchaseRecord | None:
        return self.purchases.get(purchase_id)

    def find_purchase_by_checkout_session(self, session_id: str) -> CreditPurchaseRecord | None:
        return next((item for item in self.purchases.values() if item.stripe_checkout_session_id == session_id), None)

    def stripe_event_processed(self, event_id: str) -> bool:
        return any(item.stripe_event_id == event_id for item in self.purchases.values())

    def approve_purchase(
        self,
        *,
        purchase: CreditPurchaseRecord,
        credit_wallet,
        ledger_for_purchase,
        grant_referral_bonus,
        actor_user_id: str | None,
        event_id: str | None = None,
        payment_intent_id: str | None = None,
        admin_note: str | None = None,
    ) -> tuple[CreditPurchaseRecord, CreditLedgerRecord | None]:  # type: ignore[no-untyped-def]
        with self._lock:
            if purchase.status == "approved":
                return purchase, ledger_for_purchase(purchase.id)
            if purchase.status not in {"pending_payment", "paid", "pending_manual_review"}:
                raise ApiError("PURCHASE_STATUS_INVALID", status_code=409)
            now = utc_now()
            purchase.status = "approved"
            purchase.updated_at = now
            purchase.paid_at = purchase.paid_at or now
            purchase.approved_at = now
            purchase.stripe_event_id = event_id or purchase.stripe_event_id
            purchase.stripe_payment_intent_id = payment_intent_id or purchase.stripe_payment_intent_id
            purchase.approved_by_admin_id = actor_user_id if admin_note else purchase.approved_by_admin_id
            purchase.admin_note = admin_note or purchase.admin_note
            ledger = credit_wallet(
                business_id=purchase.business_id,
                amount=purchase.credits_amount,
                ledger_type="purchase",
                reason="credit_purchase_approved",
                source="credit_purchases",
                reference_type="credit_purchase",
                reference_id=purchase.id,
                created_by=actor_user_id,
                related_credit_purchase_id=purchase.id,
                lifetime_field="lifetime_purchased_credits",
            )
            grant_referral_bonus(referred_business_id=purchase.business_id, purchase_id=purchase.id, created_by=actor_user_id)
            return purchase, ledger

    def apply_onchain_verification(
        self,
        *,
        purchase: CreditPurchaseRecord,
        verification: OnchainVerificationResult,
        credit_wallet,
        ledger_for_purchase,
        grant_referral_bonus,
        actor_user_id: str | None,
        min_confirmations: int,
    ) -> tuple[CreditPurchaseRecord, CreditLedgerRecord | None]:
        with self._lock:
            existing_purchase = self.purchases.get(purchase.id)
            if existing_purchase is None:
                raise ApiError("PURCHASE_NOT_FOUND", status_code=404)
            existing_ledger = ledger_for_purchase(purchase.id)
            if existing_ledger:
                if existing_purchase.status == "credited":
                    return existing_purchase, existing_ledger
                raise ApiError("CREDIT_ALREADY_GRANTED", status_code=409)
            if existing_purchase.status not in {"pending_payment", "pending_onchain_confirmation", "detected"}:
                raise ApiError("PURCHASE_STATUS_INVALID", status_code=409)
            verification = normalize_credit_verification(
                purchase=existing_purchase,
                verification=verification,
                submitted_tx_hash=verification.tx_hash,
                min_confirmations=min_confirmations,
                now=utc_now(),
            )
            duplicate = self._duplicate_onchain_tx(existing_purchase.id, verification)
            if duplicate:
                raise ApiError("ONCHAIN_TX_ALREADY_USED", status_code=409)
            now = utc_now()
            existing_purchase.tx_hash = verification.tx_hash
            existing_purchase.tx_amount_units = verification.tx_amount_units
            existing_purchase.tx_from_address = verification.tx_from_address
            existing_purchase.tx_to_address = verification.tx_to_address
            existing_purchase.tx_block_number = verification.tx_block_number
            existing_purchase.tx_log_index = verification.tx_log_index
            existing_purchase.confirmations = verification.confirmations
            existing_purchase.verification_source = "base_rpc"
            existing_purchase.verification_status = verification.verification_status
            existing_purchase.detected_at = existing_purchase.detected_at or now
            existing_purchase.updated_at = now
            if verification.error_code:
                existing_purchase.status = "verification_failed"
                existing_purchase.failed_at = now
                raise ApiError(verification.error_code, status_code=409)
            if verification.verification_status == "pending_onchain_confirmation":
                existing_purchase.status = "pending_onchain_confirmation"
                return existing_purchase, None
            if verification.verification_status == "under_review":
                existing_purchase.status = "under_review"
                return existing_purchase, None
            if verification.verification_status != "verified":
                existing_purchase.status = "verification_failed"
                existing_purchase.failed_at = now
                raise ApiError("ONCHAIN_VERIFICATION_FAILED", status_code=409)
            existing_purchase.status = "credited"
            existing_purchase.verified_at = now
            existing_purchase.credited_at = now
            existing_purchase.paid_at = existing_purchase.paid_at or now
            existing_purchase.approved_at = existing_purchase.approved_at or now
            ledger = credit_wallet(
                business_id=existing_purchase.business_id,
                amount=existing_purchase.credits_amount,
                ledger_type="purchase",
                reason=ONCHAIN_CREDIT_LEDGER_REASON,
                source="credit_purchases",
                reference_type="credit_purchase",
                reference_id=existing_purchase.id,
                created_by=actor_user_id,
                related_credit_purchase_id=existing_purchase.id,
                lifetime_field="lifetime_purchased_credits",
            )
            grant_referral_bonus(referred_business_id=existing_purchase.business_id, purchase_id=existing_purchase.id, created_by=actor_user_id)
            return existing_purchase, ledger

    def reject_purchase(self, *, purchase: CreditPurchaseRecord, admin_user_id: str, reason: str) -> CreditPurchaseRecord:
        with self._lock:
            if purchase.status not in {"pending_manual_review", "under_review"}:
                raise ApiError("MANUAL_PAYMENT_ALREADY_REVIEWED", status_code=409)
            now = utc_now()
            purchase.status = "rejected"
            purchase.rejected_by_admin_id = admin_user_id
            purchase.admin_note = reason
            purchase.rejected_at = now
            purchase.updated_at = now
            return purchase

    def list_onchain_pending_purchases(self, *, limit: int) -> list[CreditPurchaseRecord]:
        items = [
            item
            for item in self.purchases.values()
            if item.payment_method == "base_usdc_onchain"
            and item.status in {"pending_payment", "pending_onchain_confirmation", "detected"}
            and item.tx_hash
            and item.expected_amount_units is not None
            and item.destination_wallet_address
        ]
        items.sort(key=lambda item: item.created_at)
        return items[:limit]

    def list_purchases(self, *, status: str | None, business_id: str | None, cursor: str | None, limit: int) -> tuple[list[CreditPurchaseRecord], str | None]:
        items = list(self.purchases.values())
        if status:
            items = [item for item in items if item.status == status]
        if business_id:
            items = [item for item in items if item.business_id == business_id]
        return paginate_descending(
            items,
            timestamp_of=lambda item: item.created_at,
            id_of=lambda item: item.id,
            cursor=cursor,
            limit=limit,
        )

    def _duplicate_onchain_tx(self, purchase_id: str, verification: OnchainVerificationResult) -> bool:
        if verification.tx_log_index is None:
            return False
        return any(
            item.id != purchase_id
            and item.chain_id == verification.chain_id
            and item.tx_hash == verification.tx_hash
            and item.tx_log_index == verification.tx_log_index
            for item in self.purchases.values()
        )
