from __future__ import annotations

from threading import RLock

from app.core.errors import ApiError
from app.modules.ads.models import CreditLedgerRecord, CreditWalletRecord, new_id, utc_now


class InMemoryCreditWalletStore:
    def __init__(self, *, lock: RLock, ad_repository) -> None:  # type: ignore[no-untyped-def]
        self._lock = lock
        self._ads = ad_repository

    def ensure_wallet(self, business_id: str) -> CreditWalletRecord:
        return self._ads.ensure_wallet(business_id)

    def get_wallet(self, business_id: str) -> CreditWalletRecord | None:
        return self._ads.get_wallet(business_id)

    def list_ledger(self, *, business_id: str, ledger_type: str | None, cursor: str | None, limit: int) -> tuple[list[CreditLedgerRecord], str | None]:
        items = [item for item in self._ads.ledger.values() if item.business_id == business_id]
        if ledger_type:
            items = [item for item in items if item.type == ledger_type]
        if cursor:
            items = [item for item in items if item.created_at.isoformat() < cursor]
        items.sort(key=lambda item: item.created_at, reverse=True)
        page = items[:limit]
        return page, page[-1].created_at.isoformat() if len(page) == limit else None

    def adjust_wallet(self, *, business_id: str, amount: int, direction: str, reason: str, notes: str | None, created_by: str) -> CreditLedgerRecord:
        signed_amount = amount if direction == "add" else -amount
        return self.credit_wallet(
            business_id=business_id,
            amount=signed_amount,
            ledger_type="admin_adjustment",
            reason=reason,
            source="admin",
            reference_type="business",
            reference_id=business_id,
            created_by=created_by,
            notes=notes,
            lifetime_field="lifetime_adjusted_credits",
        )

    def ledger_for_purchase(self, purchase_id: str) -> CreditLedgerRecord | None:
        return next((item for item in self._ads.ledger.values() if item.related_credit_purchase_id == purchase_id and item.type == "purchase"), None)

    def credit_wallet(
        self,
        *,
        business_id: str,
        amount: int,
        ledger_type: str,
        reason: str,
        source: str,
        reference_type: str,
        reference_id: str,
        created_by: str | None,
        related_credit_purchase_id: str | None = None,
        related_referral_id: str | None = None,
        notes: str | None = None,
        lifetime_field: str | None = None,
    ) -> CreditLedgerRecord:
        with self._lock:
            wallet = self.ensure_wallet(business_id)
            before_available = wallet.available_credits
            if before_available + amount < 0:
                raise ApiError("CREDIT_BALANCE_INSUFFICIENT", status_code=409)
            wallet.available_credits += amount
            if lifetime_field and amount > 0:
                setattr(wallet, lifetime_field, getattr(wallet, lifetime_field) + amount)
            wallet.updated_at = utc_now()
            ledger = CreditLedgerRecord(
                id=new_id(),
                business_id=business_id,
                type=ledger_type,
                amount=abs(amount),
                available_before=before_available,
                available_after=wallet.available_credits,
                blocked_before=wallet.blocked_credits,
                blocked_after=wallet.blocked_credits,
                consumed_before=wallet.consumed_credits,
                consumed_after=wallet.consumed_credits,
                reason=reason,
                source=source,
                reference_type=reference_type,
                reference_id=reference_id,
                related_referral_id=related_referral_id,
                related_credit_purchase_id=related_credit_purchase_id,
                notes=notes,
                created_by=created_by,
            )
            self._ads.ledger[ledger.id] = ledger
            return ledger
