from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from threading import RLock

from app.core.errors import ApiError
from app.modules.ads.memory_credits import InMemoryAdCreditsMixin
from app.modules.ads.models import AdRecord, CreditLedgerRecord, CreditWalletRecord, new_id, utc_now


class InMemoryAdRepository(InMemoryAdCreditsMixin):
    def __init__(self) -> None:
        self._lock = RLock()
        self.ads: dict[str, AdRecord] = {}
        self.wallets: dict[str, CreditWalletRecord] = {}
        self.ledger: dict[str, CreditLedgerRecord] = {}

    def get_ad(self, ad_id: str) -> AdRecord | None:
        return self.ads.get(ad_id)

    def has_overlapping_ad(
        self,
        *,
        business_id: str,
        payment_method: str,
        delivery_method: str,
        amount_min_usd: Decimal,
        amount_max_usd: Decimal,
        exclude_ad_id: str | None = None,
    ) -> bool:
        for ad in self.ads.values():
            if ad.id == exclude_ad_id:
                continue
            if ad.business_id != business_id or ad.payment_method != payment_method or ad.delivery_method != delivery_method:
                continue
            if ad.status not in {"active", "paused"}:
                continue
            if amount_min_usd <= ad.amount_max_usd and amount_max_usd >= ad.amount_min_usd:
                return True
        return False

    def business_open_exposure_usd(self, *, business_id: str, exclude_ad_id: str | None = None) -> Decimal:
        return sum(
            (ad.amount_max_usd for ad in self.ads.values() if ad.business_id == business_id and ad.id != exclude_ad_id and ad.status in {"active", "in_order"}),
            Decimal("0.00"),
        )

    def publish_ad(
        self,
        *,
        business_id: str,
        payment_method_id: str,
        payment_method: str,
        delivery_method: str,
        rate_bs_per_usd: Decimal,
        amount_min_usd: Decimal,
        amount_max_usd: Decimal,
        required_credits: int,
        created_by: str,
        use_founder_access: bool,
    ) -> AdRecord:
        with self._lock:
            wallet = self.ensure_wallet(business_id)
            if not use_founder_access and wallet.available_credits < required_credits:
                raise ApiError("CREDIT_BALANCE_INSUFFICIENT", status_code=409)
            now = utc_now()
            ad = AdRecord(
                id=new_id(),
                business_id=business_id,
                payment_method_id=payment_method_id,
                payment_method=payment_method,
                delivery_method=delivery_method,
                rate_bs_per_usd=rate_bs_per_usd,
                amount_min_usd=amount_min_usd,
                amount_max_usd=amount_max_usd,
                required_credits=required_credits,
                status="active",
                credit_hold_ledger_id=None,
                credit_consumed_ledger_id=None,
                created_at=now,
                updated_at=now,
                activated_at=now,
                expires_at=now + timedelta(days=7),
                last_rate_updated_at=now,
            )
            self.ads[ad.id] = ad
            if use_founder_access:
                self._write_ledger(
                    wallet=wallet,
                    ledger_type="founder_free_use",
                    amount=required_credits,
                    related_ad_id=ad.id,
                    reason="founder_access_ad_publish",
                    source="ads",
                    created_by=created_by,
                )
                return ad
            hold = self._hold_credits(wallet=wallet, amount=required_credits, ad_id=ad.id, created_by=created_by)
            ad.credit_hold_ledger_id = hold.id
            ad.updated_at = utc_now()
            return ad

    def update_ad(
        self,
        ad: AdRecord,
        *,
        payment_method_id: str | None,
        rate_bs_per_usd: Decimal | None,
        amount_min_usd: Decimal | None,
        amount_max_usd: Decimal | None,
    ) -> AdRecord:
        with self._lock:
            if payment_method_id is not None:
                ad.payment_method_id = payment_method_id
            if rate_bs_per_usd is not None:
                ad.rate_bs_per_usd = rate_bs_per_usd
                ad.last_rate_updated_at = utc_now()
            if amount_min_usd is not None:
                ad.amount_min_usd = amount_min_usd
            if amount_max_usd is not None:
                ad.amount_max_usd = amount_max_usd
            ad.updated_at = utc_now()
            return ad

    def set_status(self, ad: AdRecord, status: str) -> AdRecord:
        with self._lock:
            ad.status = status
            ad.updated_at = utc_now()
            return ad

    def list_marketplace_ads(
        self,
        *,
        amount_usd: Decimal | None,
        payment_method: str | None,
        delivery_method: str | None,
        eligible_business_ids: set[str],
        cursor: str | None,
        limit: int,
    ) -> tuple[list[AdRecord], str | None]:
        items = [
            ad
            for ad in self.ads.values()
            if ad.business_id in eligible_business_ids
            and ad.status == "active"
            and ad.expires_at is not None
            and ad.expires_at > utc_now()
            and (payment_method is None or ad.payment_method == payment_method)
            and (delivery_method is None or ad.delivery_method == delivery_method)
            and (amount_usd is None or ad.amount_min_usd <= amount_usd <= ad.amount_max_usd)
        ]
        if cursor:
            items = [ad for ad in items if ad.created_at.isoformat() < cursor]
        items.sort(key=lambda ad: (ad.rate_bs_per_usd, ad.created_at), reverse=True)
        page = items[:limit]
        next_cursor = page[-1].created_at.isoformat() if len(page) == limit else None
        return page, next_cursor

    def list_business_ads(self, *, business_id: str, archived: bool, cursor: str | None, limit: int) -> tuple[list[AdRecord], str | None]:
        allowed = {"archived", "expired"} if archived else {"active", "paused", "in_order", "suspended"}
        items = [ad for ad in self.ads.values() if ad.business_id == business_id and ad.status in allowed]
        if cursor:
            items = [ad for ad in items if ad.created_at.isoformat() < cursor]
        items.sort(key=lambda ad: ad.created_at, reverse=True)
        page = items[:limit]
        next_cursor = page[-1].created_at.isoformat() if len(page) == limit else None
        return page, next_cursor

    def list_expirable_ads(self, *, limit: int) -> list[AdRecord]:
        now = utc_now()
        items = [
            ad
            for ad in self.ads.values()
            if ad.status in {"active", "paused"}
            and ad.expires_at is not None
            and ad.expires_at <= now
        ]
        items.sort(key=lambda ad: ad.expires_at or ad.created_at)
        return items[:limit]

