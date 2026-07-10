from __future__ import annotations

from threading import RLock

from app.core.errors import ApiError
from app.modules.ads.models import new_id, utc_now
from app.modules.credits.models import ReferralCodeRecord, ReferralEventRecord


class InMemoryReferralStore:
    def __init__(
        self,
        *,
        lock: RLock,
        referral_codes: dict[str, ReferralCodeRecord],
        referral_events: dict[str, ReferralEventRecord],
        business_repository,
        ledger_values,
    ) -> None:  # type: ignore[no-untyped-def]
        self._lock = lock
        self.referral_codes = referral_codes
        self.referral_events = referral_events
        self._businesses = business_repository
        self._ledger_values = ledger_values

    def get_or_create_referral_code(self, business_id: str) -> ReferralCodeRecord:
        with self._lock:
            for code in self.referral_codes.values():
                if code.business_id == business_id:
                    return code
            code = ReferralCodeRecord(id=new_id(), business_id=business_id, code=f"NODO{business_id.replace('-', '')[:8].upper()}")
            self.referral_codes[code.id] = code
            business = self._businesses.get_business(business_id)
            if business is not None:
                business.referral_code = code.code
                business.updated_at = utc_now()
            return code

    def apply_referral_code(self, *, referred_business_id: str, referral_code: str) -> ReferralEventRecord:
        with self._lock:
            if any(event.referred_business_id == referred_business_id and event.status in {"pending", "approved", "rewarded"} for event in self.referral_events.values()):
                raise ApiError("REFERRAL_ALREADY_USED", status_code=409)
            code = next((item for item in self.referral_codes.values() if item.code == referral_code and item.status == "active"), None)
            if code is None:
                raise ApiError("REFERRAL_CODE_NOT_FOUND", status_code=404)
            if code.business_id == referred_business_id:
                raise ApiError("REFERRAL_NOT_ALLOWED", status_code=409)
            event = ReferralEventRecord(
                id=new_id(),
                referral_code_id=code.id,
                referrer_business_id=code.business_id,
                referred_business_id=referred_business_id,
                status="pending",
            )
            self.referral_events[event.id] = event
            return event

    def list_referral_events_for_business(self, business_id: str) -> list[ReferralEventRecord]:
        return sorted(
            [event for event in self.referral_events.values() if event.referrer_business_id == business_id or event.referred_business_id == business_id],
            key=lambda event: event.created_at,
            reverse=True,
        )

    def grant_referral_bonus_if_eligible(self, *, referred_business_id: str, purchase_id: str, created_by: str | None, credit_wallet) -> None:  # type: ignore[no-untyped-def]
        event = next((item for item in self.referral_events.values() if item.referred_business_id == referred_business_id and item.status == "pending"), None)
        if event is None:
            return
        if any(item.related_credit_purchase_id == purchase_id and item.type == "referral_bonus" for item in self._ledger_values()):
            return
        referrer = self._businesses.get_business(event.referrer_business_id)
        if referrer is None or referrer.referral_credits_earned >= 20:
            event.status = "rejected"
            event.reject_reason = "referral_cap_reached"
            event.rejected_at = utc_now()
            return
        now = utc_now()
        event.status = "rewarded"
        event.related_credit_purchase_id = purchase_id
        event.credits_awarded = 1
        event.approved_at = now
        event.rewarded_at = now
        referrer.referral_credits_earned += 1
        referrer.updated_at = now
        credit_wallet(
            business_id=event.referrer_business_id,
            amount=1,
            ledger_type="referral_bonus",
            reason="referral_bonus_first_approved_purchase",
            source="referral_events",
            reference_type="referral_event",
            reference_id=event.id,
            created_by=created_by,
            related_referral_id=event.id,
            related_credit_purchase_id=purchase_id,
            lifetime_field="lifetime_bonus_credits",
        )
