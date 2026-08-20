from __future__ import annotations

from threading import RLock

from app.core.errors import ApiError
from app.modules.ads.models import new_id, utc_now
from app.modules.credits.models import ReferralApprovalResult, ReferralCodeRecord, ReferralEventRecord
from app.modules.credits.referral_codes import normalize_referral_code


class InMemoryReferralStore:
    def __init__(
        self,
        *,
        lock: RLock,
        referral_codes: dict[str, ReferralCodeRecord],
        referral_events: dict[str, ReferralEventRecord],
        business_repository,
    ) -> None:  # type: ignore[no-untyped-def]
        self._lock = lock
        self.referral_codes = referral_codes
        self.referral_events = referral_events
        self._businesses = business_repository

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
            if any(event.referred_business_id == referred_business_id for event in self.referral_events.values()):
                raise ApiError("REFERRAL_ALREADY_USED", status_code=409)
            normalized = normalize_referral_code(referral_code)
            code = next((item for item in self.referral_codes.values() if item.code == normalized and item.status == "active"), None)
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

    def award_referral_on_business_approval(
        self,
        *,
        referred_business_id: str,
        referral_code: str | None,
        actor_user_id: str | None,
        credit_wallet,
    ) -> ReferralApprovalResult:  # type: ignore[no-untyped-def]
        with self._lock:
            referred = self._businesses.get_business(referred_business_id)
            if referred is None:
                raise ApiError("REFERRAL_NOT_ALLOWED", status_code=409)
            business_approved = referred.verification_status != "approved"
            if business_approved:
                now = utc_now()
                referred.verification_status = "approved"
                referred.approved_at = now
                referred.updated_at = now
            existing = next(
                (event for event in self.referral_events.values() if event.referred_business_id == referred_business_id),
                None,
            )
            if existing is not None:
                if existing.status != "pending":
                    return ReferralApprovalResult(
                        event=existing,
                        outcome="already_processed",
                        created=False,
                        business_approved=business_approved,
                    )
                if existing.referrer_business_id == referred_business_id:
                    now = utc_now()
                    existing.status = "rejected"
                    existing.reject_reason = "self_referral"
                    existing.rejected_at = now
                    return ReferralApprovalResult(
                        event=existing,
                        outcome="self_referral",
                        created=False,
                        business_approved=business_approved,
                        event_changed=True,
                    )
                return self._finalize_pending_referral(
                    event=existing,
                    actor_user_id=actor_user_id,
                    credit_wallet=credit_wallet,
                    created=False,
                    business_approved=business_approved,
                )
            normalized = normalize_referral_code(referral_code)
            if normalized is None:
                return ReferralApprovalResult(
                    event=None,
                    outcome="no_code",
                    created=False,
                    business_approved=business_approved,
                )
            code = next(
                (item for item in self.referral_codes.values() if item.code == normalized and item.status == "active"),
                None,
            )
            if code is None:
                return ReferralApprovalResult(
                    event=None,
                    outcome="invalid_code",
                    created=False,
                    business_approved=business_approved,
                )
            if code.business_id == referred_business_id:
                return ReferralApprovalResult(
                    event=None,
                    outcome="self_referral",
                    created=False,
                    business_approved=business_approved,
                )

            event = ReferralEventRecord(
                id=new_id(),
                referral_code_id=code.id,
                referrer_business_id=code.business_id,
                referred_business_id=referred_business_id,
                status="pending",
            )
            self.referral_events[event.id] = event
            return self._finalize_pending_referral(
                event=event,
                actor_user_id=actor_user_id,
                credit_wallet=credit_wallet,
                created=True,
                business_approved=business_approved,
            )

    def _finalize_pending_referral(
        self,
        *,
        event: ReferralEventRecord,
        actor_user_id: str | None,
        credit_wallet,
        created: bool,
        business_approved: bool,
    ) -> ReferralApprovalResult:  # type: ignore[no-untyped-def]
        referrer = self._businesses.get_business(event.referrer_business_id)
        remaining = max(0, 20 - (referrer.referral_credits_earned if referrer else 20))
        award = min(5, remaining)
        now = utc_now()
        if referrer is None or award == 0:
            event.status = "rejected"
            event.reject_reason = "referral_cap_reached"
            event.rejected_at = now
            return ReferralApprovalResult(
                event=event,
                outcome="cap_reached",
                created=created,
                business_approved=business_approved,
                event_changed=True,
            )

        event.status = "rewarded"
        event.credits_awarded = award
        event.approved_at = now
        event.rewarded_at = now
        referrer.referral_credits_earned += award
        referrer.updated_at = now
        credit_wallet(
            business_id=event.referrer_business_id,
            amount=award,
            ledger_type="referral_bonus",
            reason="referral_bonus_business_approval",
            source="referral_events",
            reference_type="referral_event",
            reference_id=event.id,
            created_by=actor_user_id,
            related_referral_id=event.id,
            lifetime_field="lifetime_bonus_credits",
        )
        return ReferralApprovalResult(
            event=event,
            outcome="rewarded",
            created=created,
            business_approved=business_approved,
            event_changed=True,
        )

    def list_referral_events_for_business(self, business_id: str) -> list[ReferralEventRecord]:
        return sorted(
            [event for event in self.referral_events.values() if event.referrer_business_id == business_id or event.referred_business_id == business_id],
            key=lambda event: event.created_at,
            reverse=True,
        )

    def admin_referral_summary(self, business_id: str) -> dict:
        with self._lock:
            business = self._businesses.get_business(business_id)
            incoming = next(
                (event for event in self.referral_events.values() if event.referred_business_id == business_id),
                None,
            )
            code = self.referral_codes.get(incoming.referral_code_id) if incoming else None
            referrer = self._businesses.get_business(incoming.referrer_business_id) if incoming else None
            outgoing = sorted(
                (event for event in self.referral_events.values() if event.referrer_business_id == business_id),
                key=lambda event: (event.created_at, event.id),
                reverse=True,
            )
            outgoing_page = outgoing[:50]
            earned = business.referral_credits_earned if business else 0
            return {
                "referred_by": (
                    {"business_id": referrer.id, "business_name": referrer.business_name}
                    if referrer is not None
                    else None
                ),
                "code_used": code.code if code else None,
                "earned_credits": earned,
                "remaining_bonus_credits": max(0, 20 - earned),
                "cap": 20,
                "referred_businesses_truncated": len(outgoing) > 50,
                "referred_businesses": [
                    {
                        "business_id": event.referred_business_id,
                        "business_name": (
                            referred.business_name
                            if (referred := self._businesses.get_business(event.referred_business_id)) is not None
                            else None
                        ),
                        "status": event.status,
                        "credits_awarded": event.credits_awarded,
                        "created_at": event.created_at.isoformat(),
                        "rewarded_at": event.rewarded_at.isoformat() if event.rewarded_at else None,
                    }
                    for event in outgoing_page
                ],
            }
