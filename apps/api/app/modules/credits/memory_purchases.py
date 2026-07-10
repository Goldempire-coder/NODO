from __future__ import annotations

from threading import RLock

from app.core.errors import ApiError
from app.modules.ads.models import CreditLedgerRecord, new_id, utc_now
from app.modules.businesses.models import FileAssetRecord
from app.modules.credits.models import CREDIT_PACKAGES, CreditPurchaseRecord


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

    def reject_purchase(self, *, purchase: CreditPurchaseRecord, admin_user_id: str, reason: str) -> CreditPurchaseRecord:
        with self._lock:
            if purchase.status != "pending_manual_review":
                raise ApiError("MANUAL_PAYMENT_ALREADY_REVIEWED", status_code=409)
            now = utc_now()
            purchase.status = "rejected"
            purchase.rejected_by_admin_id = admin_user_id
            purchase.admin_note = reason
            purchase.rejected_at = now
            purchase.updated_at = now
            return purchase

    def list_purchases(self, *, status: str | None, business_id: str | None, cursor: str | None, limit: int) -> tuple[list[CreditPurchaseRecord], str | None]:
        items = list(self.purchases.values())
        if status:
            items = [item for item in items if item.status == status]
        if business_id:
            items = [item for item in items if item.business_id == business_id]
        if cursor:
            items = [item for item in items if item.created_at.isoformat() < cursor]
        items.sort(key=lambda item: item.created_at, reverse=True)
        page = items[:limit]
        return page, page[-1].created_at.isoformat() if len(page) == limit else None
