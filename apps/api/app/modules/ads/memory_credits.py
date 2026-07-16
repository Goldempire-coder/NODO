from __future__ import annotations

from app.core.errors import ApiError
from app.modules.ads.models import AdRecord, CreditLedgerRecord, CreditWalletRecord, new_id, utc_now


class InMemoryAdCreditsMixin:
    def ensure_wallet(self, business_id: str) -> CreditWalletRecord:
        with self._lock:  # type: ignore[attr-defined]
            wallet = self.wallets.get(business_id)  # type: ignore[attr-defined]
            if wallet is None:
                wallet = CreditWalletRecord(id=new_id(), business_id=business_id)
                self.wallets[business_id] = wallet  # type: ignore[attr-defined]
            return wallet

    def grant_test_credits(
        self,
        *,
        business_id: str,
        amount: int,
        created_by: str | None = None,
    ) -> CreditWalletRecord:
        with self._lock:  # type: ignore[attr-defined]
            wallet = self.ensure_wallet(business_id)
            before = wallet.available_credits
            wallet.available_credits += amount
            wallet.updated_at = utc_now()
            self.ledger[new_id()] = CreditLedgerRecord(  # type: ignore[attr-defined]
                id=new_id(),
                business_id=business_id,
                type="purchase",
                amount=amount,
                available_before=before,
                available_after=wallet.available_credits,
                blocked_before=wallet.blocked_credits,
                blocked_after=wallet.blocked_credits,
                consumed_before=wallet.consumed_credits,
                consumed_after=wallet.consumed_credits,
                reason="test_credit_seed",
                source="test",
                reference_type="test",
                reference_id=business_id,
                created_by=created_by,
            )
            return wallet

    def get_wallet(self, business_id: str) -> CreditWalletRecord | None:
        return self.wallets.get(business_id)  # type: ignore[attr-defined]

    def release_hold(
        self,
        *,
        ad: AdRecord,
        created_by: str | None,
        reason: str = "ad_expired_without_order_or_payment",
        related_order_id: str | None = None,
        source: str = "ads",
    ) -> CreditLedgerRecord | None:
        if ad.credit_hold_ledger_id is None:
            return None
        with self._lock:  # type: ignore[attr-defined]
            if any(item.type == "release" and item.related_ad_id == ad.id for item in self.ledger.values()):  # type: ignore[attr-defined]
                return None
            wallet = self.ensure_wallet(ad.business_id)
            if wallet.blocked_credits < ad.required_credits:
                return None
            wallet.available_credits += ad.required_credits
            wallet.blocked_credits -= ad.required_credits
            wallet.updated_at = utc_now()
            return self._write_ledger(
                wallet=wallet,
                ledger_type="release",
                amount=ad.required_credits,
                related_ad_id=ad.id,
                reason=reason,
                source=source,
                created_by=created_by,
                related_order_id=related_order_id,
                reference_type="order" if related_order_id else "ad",
                reference_id=related_order_id or ad.id,
            )

    def expire_hold(
        self,
        *,
        ad: AdRecord,
        created_by: str | None,
        reason: str = "ad_expired_without_purchase",
        related_order_id: str | None = None,
        source: str = "ads",
    ) -> CreditLedgerRecord | None:
        with self._lock:  # type: ignore[attr-defined]
            ad.status = "archived"
            ad.updated_at = utc_now()
            if ad.credit_hold_ledger_id is None:
                return None
            if any(item.type == "expire" and item.related_ad_id == ad.id for item in self.ledger.values()):  # type: ignore[attr-defined]
                return None
            wallet = self.ensure_wallet(ad.business_id)
            if wallet.blocked_credits < ad.required_credits:
                return None
            wallet.blocked_credits -= ad.required_credits
            wallet.consumed_credits += ad.required_credits
            wallet.updated_at = utc_now()
            ledger = self._write_ledger(
                wallet=wallet,
                ledger_type="expire",
                amount=ad.required_credits,
                related_ad_id=ad.id,
                reason=reason,
                source=source,
                created_by=created_by,
                related_order_id=related_order_id,
                reference_type="order" if related_order_id else "ad",
                reference_id=related_order_id or ad.id,
            )
            ad.credit_consumed_ledger_id = ledger.id
            return ledger

    def consume_hold_for_order(
        self,
        *,
        ad: AdRecord,
        order_id: str,
        created_by: str,
        reason: str = "business_confirmed_payment_received",
        source: str = "orders",
    ) -> CreditLedgerRecord:
        if ad.credit_hold_ledger_id is None:
            raise ApiError("CREDIT_HOLD_NOT_FOUND", status_code=409)
        with self._lock:  # type: ignore[attr-defined]
            if any(item.type == "consume" and item.related_order_id == order_id for item in self.ledger.values()):  # type: ignore[attr-defined]
                raise ApiError("CREDIT_ALREADY_CONSUMED", status_code=409)
            wallet = self.ensure_wallet(ad.business_id)
            if wallet.blocked_credits < ad.required_credits:
                raise ApiError("CREDIT_HOLD_NOT_FOUND", status_code=409)
            wallet.blocked_credits -= ad.required_credits
            wallet.consumed_credits += ad.required_credits
            wallet.updated_at = utc_now()
            ledger = self._write_ledger(
                wallet=wallet,
                ledger_type="consume",
                amount=ad.required_credits,
                related_ad_id=ad.id,
                reason=reason,
                source=source,
                created_by=created_by,
                related_order_id=order_id,
                reference_type="order",
                reference_id=order_id,
            )
            ad.credit_consumed_ledger_id = ledger.id
            ad.status = "archived"
            ad.updated_at = utc_now()
            return ledger

    def _hold_credits(
        self,
        *,
        wallet: CreditWalletRecord,
        amount: int,
        ad_id: str,
        created_by: str,
    ) -> CreditLedgerRecord:
        wallet.available_credits -= amount
        wallet.blocked_credits += amount
        wallet.updated_at = utc_now()
        return self._write_ledger(
            wallet=wallet,
            ledger_type="hold",
            amount=amount,
            related_ad_id=ad_id,
            reason="ad_publish_credit_hold",
            source="ads",
            created_by=created_by,
        )

    def _write_ledger(
        self,
        *,
        wallet: CreditWalletRecord,
        ledger_type: str,
        amount: int,
        related_ad_id: str,
        reason: str,
        source: str,
        created_by: str | None,
        related_order_id: str | None = None,
        reference_type: str = "ad",
        reference_id: str | None = None,
    ) -> CreditLedgerRecord:
        ledger = CreditLedgerRecord(
            id=new_id(),
            business_id=wallet.business_id,
            type=ledger_type,
            amount=amount,
            available_before=wallet.available_credits + amount if ledger_type == "hold" else wallet.available_credits - amount if ledger_type == "release" else wallet.available_credits,
            available_after=wallet.available_credits,
            blocked_before=wallet.blocked_credits - amount if ledger_type == "hold" else wallet.blocked_credits + amount if ledger_type in {"release", "consume", "expire"} else wallet.blocked_credits,
            blocked_after=wallet.blocked_credits,
            consumed_before=wallet.consumed_credits - amount if ledger_type in {"consume", "expire"} else wallet.consumed_credits,
            consumed_after=wallet.consumed_credits,
            reason=reason,
            source=source,
            reference_type=reference_type,
            reference_id=reference_id or related_ad_id,
            related_ad_id=related_ad_id,
            related_order_id=related_order_id,
            created_by=created_by,
        )
        self.ledger[ledger.id] = ledger  # type: ignore[attr-defined]
        return ledger
