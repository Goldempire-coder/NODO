from __future__ import annotations

from threading import RLock

from app.modules.ads.models import CreditLedgerRecord, CreditWalletRecord
from app.modules.businesses.models import FileAssetRecord
from app.modules.credits.memory_purchases import InMemoryCreditPurchaseStore
from app.modules.credits.memory_referrals import InMemoryReferralStore
from app.modules.credits.memory_wallet import InMemoryCreditWalletStore
from app.modules.credits.models import CreditPurchaseRecord, ReferralCodeRecord, ReferralEventRecord


class InMemoryCreditRepository:
    def __init__(self, ad_repository, business_repository) -> None:  # type: ignore[no-untyped-def]
        self._lock = RLock()
        self._ads = ad_repository
        self._businesses = business_repository
        self.purchases: dict[str, CreditPurchaseRecord] = {}
        self.files: dict[str, FileAssetRecord] = {}
        self.referral_codes: dict[str, ReferralCodeRecord] = {}
        self.referral_events: dict[str, ReferralEventRecord] = {}
        self._wallet_store = InMemoryCreditWalletStore(lock=self._lock, ad_repository=self._ads)
        self._purchase_store = InMemoryCreditPurchaseStore(lock=self._lock, files=self.files, purchases=self.purchases)
        self._referral_store = InMemoryReferralStore(
            lock=self._lock,
            referral_codes=self.referral_codes,
            referral_events=self.referral_events,
            business_repository=self._businesses,
        )

    def ensure_wallet(self, business_id: str) -> CreditWalletRecord:
        return self._wallet_store.ensure_wallet(business_id)

    def get_wallet(self, business_id: str) -> CreditWalletRecord | None:
        return self._wallet_store.get_wallet(business_id)

    def list_ledger(self, *, business_id: str, ledger_type: str | None, cursor: str | None, limit: int) -> tuple[list[CreditLedgerRecord], str | None]:
        return self._wallet_store.list_ledger(business_id=business_id, ledger_type=ledger_type, cursor=cursor, limit=limit)

    def create_stripe_purchase(self, *, business_id: str, package_code: str, idempotency_key: str) -> CreditPurchaseRecord:
        return self._purchase_store.create_stripe_purchase(business_id=business_id, package_code=package_code, idempotency_key=idempotency_key)

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
        return self._purchase_store.create_manual_purchase(
            business_id=business_id,
            owner_user_id=owner_user_id,
            package_code=package_code,
            payment_method=payment_method,
            idempotency_key=idempotency_key,
            storage_path=storage_path,
            mime_type=mime_type,
            size_bytes=size_bytes,
            manual_payment_reference=manual_payment_reference,
            manual_tx_hash=manual_tx_hash,
            manual_network=manual_network,
        )

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
        return self._purchase_store.create_base_usdc_purchase(
            business_id=business_id,
            package_code=package_code,
            idempotency_key=idempotency_key,
            expected_amount_units=expected_amount_units,
            destination_wallet_address=destination_wallet_address,
            expires_at=expires_at,
        )

    def get_purchase(self, purchase_id: str) -> CreditPurchaseRecord | None:
        return self._purchase_store.get_purchase(purchase_id)

    def find_purchase_by_checkout_session(self, session_id: str) -> CreditPurchaseRecord | None:
        return self._purchase_store.find_purchase_by_checkout_session(session_id)

    def stripe_event_processed(self, event_id: str) -> bool:
        return self._purchase_store.stripe_event_processed(event_id)

    def approve_purchase(self, *, purchase: CreditPurchaseRecord, actor_user_id: str | None, event_id: str | None = None, payment_intent_id: str | None = None, admin_note: str | None = None) -> tuple[CreditPurchaseRecord, CreditLedgerRecord | None]:
        return self._purchase_store.approve_purchase(
            purchase=purchase,
            credit_wallet=self._wallet_store.credit_wallet,
            ledger_for_purchase=self._wallet_store.ledger_for_purchase,
            actor_user_id=actor_user_id,
            event_id=event_id,
            payment_intent_id=payment_intent_id,
            admin_note=admin_note,
        )

    def apply_onchain_verification(self, *, purchase: CreditPurchaseRecord, verification, actor_user_id: str | None, min_confirmations: int) -> tuple[CreditPurchaseRecord, CreditLedgerRecord | None]:  # type: ignore[no-untyped-def]
        return self._purchase_store.apply_onchain_verification(
            purchase=purchase,
            verification=verification,
            credit_wallet=self._wallet_store.credit_wallet,
            ledger_for_purchase=self._wallet_store.ledger_for_purchase,
            actor_user_id=actor_user_id,
            min_confirmations=min_confirmations,
        )

    def reject_purchase(self, *, purchase: CreditPurchaseRecord, admin_user_id: str, reason: str) -> CreditPurchaseRecord:
        return self._purchase_store.reject_purchase(purchase=purchase, admin_user_id=admin_user_id, reason=reason)

    def list_purchases(self, *, status: str | None, business_id: str | None, cursor: str | None, limit: int) -> tuple[list[CreditPurchaseRecord], str | None]:
        return self._purchase_store.list_purchases(status=status, business_id=business_id, cursor=cursor, limit=limit)

    def list_onchain_pending_purchases(self, *, limit: int) -> list[CreditPurchaseRecord]:
        return self._purchase_store.list_onchain_pending_purchases(limit=limit)

    def adjust_wallet(self, *, business_id: str, amount: int, direction: str, reason: str, notes: str | None, created_by: str) -> CreditLedgerRecord:
        return self._wallet_store.adjust_wallet(business_id=business_id, amount=amount, direction=direction, reason=reason, notes=notes, created_by=created_by)

    def get_or_create_referral_code(self, business_id: str) -> ReferralCodeRecord:
        return self._referral_store.get_or_create_referral_code(business_id)

    def apply_referral_code(self, *, referred_business_id: str, referral_code: str) -> ReferralEventRecord:
        return self._referral_store.apply_referral_code(referred_business_id=referred_business_id, referral_code=referral_code)

    def list_referral_events_for_business(self, business_id: str) -> list[ReferralEventRecord]:
        return self._referral_store.list_referral_events_for_business(business_id)

    def award_referral_on_business_approval(self, *, referred_business_id: str, referral_code: str | None, actor_user_id: str | None):  # type: ignore[no-untyped-def]
        return self._referral_store.award_referral_on_business_approval(
            referred_business_id=referred_business_id,
            referral_code=referral_code,
            actor_user_id=actor_user_id,
            credit_wallet=self._wallet_store.credit_wallet,
        )

    def admin_referral_summary(self, business_id: str) -> dict:
        return self._referral_store.admin_referral_summary(business_id)
