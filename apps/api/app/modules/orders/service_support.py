from __future__ import annotations

from app.core.errors import ApiError
from app.modules.ads.models import AdRecord
from app.modules.businesses.access_control import require_active_business_access
from app.modules.businesses.models import BusinessPaymentMethodRecord, BusinessRecord
from app.modules.orders.helpers import require_uuid
from app.modules.orders.state_machine import ensure_aware, is_waiting_payment_expired, now_utc
from app.modules.users.models import UserRecord

MARKETPLACE_CACHE_PREFIX = "marketplace:ads:"


class OrderServiceSupportMixin:
    def _clear_marketplace_cache(self) -> None:
        if self._marketplace_cache is not None:  # type: ignore[attr-defined]
            self._marketplace_cache.clear_prefix(MARKETPLACE_CACHE_PREFIX)  # type: ignore[attr-defined]

    def _rate_limit(self, action: str, user: UserRecord) -> None:
        key = f"orders:{action}:{user.id}"
        if not self._rate_limiter.allow(  # type: ignore[attr-defined]
            key,
            max_attempts=self._settings.business_rate_limit_max_attempts,  # type: ignore[attr-defined]
            window_seconds=self._settings.business_rate_limit_window_seconds,  # type: ignore[attr-defined]
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def _ad_or_safe_error(self, ad_id: str) -> AdRecord:
        ad_id = require_uuid(ad_id, "AD_NOT_FOUND") or ad_id
        ad = self._ads.get_ad(ad_id)  # type: ignore[attr-defined]
        if ad is None:
            raise ApiError("AD_NOT_FOUND", status_code=404)
        return ad

    def _business_or_unavailable(self, business_id: str) -> BusinessRecord:
        business = self._businesses.get_business(business_id)  # type: ignore[attr-defined]
        if business is None or business.verification_status != "approved" or business.risk_level in {"restricted", "high_risk"}:
            raise ApiError("BUSINESS_NOT_APPROVED", status_code=409)
        return business

    def _payment_or_unavailable(self, payment_method_id: str) -> BusinessPaymentMethodRecord:
        payment = self._businesses.get_payment_method(payment_method_id)  # type: ignore[attr-defined]
        if payment is None or payment.verified_status != "approved" or not payment.active:
            raise ApiError("AD_NOT_AVAILABLE", status_code=404)
        return payment

    def _approved_business_for_owner(self, user: UserRecord) -> BusinessRecord:
        business, _ = require_active_business_access(user=user, business_repository=self._businesses)  # type: ignore[attr-defined]
        if business.verification_status != "approved" or business.risk_level in {"restricted", "high_risk"}:
            raise ApiError("BUSINESS_NOT_APPROVED", status_code=403)
        return business

    def _ad_expired(self, ad: AdRecord) -> bool:
        return ad.expires_at is not None and ensure_aware(ad.expires_at) <= now_utc()

    def _return_or_expire_ad(self, ad: AdRecord, *, actor: UserRecord | None, request_id: str) -> None:
        next_status = "expired" if self._ad_expired(ad) else "active"
        self._ads.set_status(ad, next_status)  # type: ignore[attr-defined]
        self._clear_marketplace_cache()
        released = self._ads.release_hold(ad=ad, created_by=actor.id if actor else None)  # type: ignore[attr-defined]
        if released is not None:
            self._audit.write(  # type: ignore[attr-defined]
                event_type="credits_released",
                actor_user_id=actor.id if actor else None,
                actor_role=actor.role if actor else None,
                resource_type="order",
                resource_id=None,
                request_id=request_id,
                metadata_json={"ledger_id": released.id, "amount": released.amount, "ad_id": ad.id},
            )

    def _materialize_order_expiration(self, order, *, actor: UserRecord | None, request_id: str):  # type: ignore[no-untyped-def]
        if not is_waiting_payment_expired(order):
            return order
        old_status = order.status
        expired = self._repository.update_order(order, status="cancelled", cancel_reason="payment_not_reported_in_time")  # type: ignore[attr-defined]
        ad = self._ads.get_ad(order.ad_id)  # type: ignore[attr-defined]
        if ad is not None:
            self._return_or_expire_ad(ad, actor=actor, request_id=request_id)
        self._repository.add_state_event(  # type: ignore[attr-defined]
            order_id=order.id,
            from_status=old_status,
            to_status="cancelled",
            event_type="order_cancelled_by_timeout",
            actor_user_id=actor.id if actor else None,
            actor_role=actor.role if actor else None,
            reason="payment_not_reported_in_time",
            request_id=request_id,
            metadata_json={"ad_id": order.ad_id},
        )
        self._audit.write(  # type: ignore[attr-defined]
            event_type="order_expired",
            actor_user_id=actor.id if actor else None,
            actor_role=actor.role if actor else None,
            resource_type="order",
            resource_id=order.id,
            request_id=request_id,
            metadata_json={"from_status": old_status, "to_status": "cancelled"},
        )
        self._audit.write(  # type: ignore[attr-defined]
            event_type="order_cancelled",
            actor_user_id=actor.id if actor else None,
            actor_role=actor.role if actor else None,
            resource_type="order",
            resource_id=order.id,
            request_id=request_id,
            metadata_json={"reason": "payment_not_reported_in_time"},
        )
        return expired
