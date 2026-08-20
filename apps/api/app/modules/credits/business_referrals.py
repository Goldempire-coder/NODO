from __future__ import annotations

from typing import Any, Callable

from app.core.errors import ApiError
from app.modules.businesses.models import BusinessRecord
from app.modules.credits.schemas import ReferralApplyRequest
from app.modules.credits.referral_codes import normalize_referral_code
from app.modules.credits.serializers import referral_public
from app.modules.users.models import UserRecord

CREDITS_DISCLAIMER = "Asegurate de usar la red Base para comprar tus creditos."


class CreditBusinessReferrals:
    def __init__(
        self,
        *,
        repository,
        audit_writer,
        idempotency_store,
        rate_limit: Callable[[str, str], None],
        require_idempotency_key: Callable[[str | None], str],
    ) -> None:  # type: ignore[no-untyped-def]
        self._repository = repository
        self._audit = audit_writer
        self._idempotency = idempotency_store
        self._rate_limit = rate_limit
        self._require_idempotency_key = require_idempotency_key

    def referrals(self, *, user: UserRecord, business: BusinessRecord) -> dict[str, Any]:
        self._rate_limit("referrals", business.id)
        code = self._repository.get_or_create_referral_code(business.id)
        if business.referral_code is None:
            self._audit.write(event_type="referral_code_created", actor_user_id=user.id, actor_role=user.role, resource_type="business", resource_id=business.id, request_id="request_id_unavailable")
        events = self._repository.list_referral_events_for_business(business.id)
        earned = business.referral_credits_earned
        return {
            "referral_code": code.code,
            "status": code.status,
            "cap": 20,
            "earned_credits": earned,
            "remaining_bonus_credits": max(0, 20 - earned),
            "events": [referral_public(event, business.id) for event in events],
            "disclaimer": CREDITS_DISCLAIMER,
        }

    def apply_referral(self, *, user: UserRecord, business: BusinessRecord, payload: ReferralApplyRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        self._rate_limit("apply_referral", business.id)
        stable_key = self._require_idempotency_key(idempotency_key)
        if business.verification_status == "approved":
            raise ApiError("REFERRAL_NOT_ALLOWED", status_code=409)
        referral_code = normalize_referral_code(payload.referral_code)

        def compute() -> dict[str, Any]:
            event = self._repository.apply_referral_code(referred_business_id=business.id, referral_code=referral_code or "")
            self._audit.write(event_type="referral_code_applied", actor_user_id=user.id, actor_role=user.role, resource_type="referral_event", resource_id=event.id, request_id=request_id)
            return {"referral_event": referral_public(event, business.id), "disclaimer": CREDITS_DISCLAIMER}

        return self._idempotency.replay_or_store(
            f"credits:referral_apply:{business.id}:{stable_key}",
            payload={"referral_code": referral_code},
            compute=compute,
        )
