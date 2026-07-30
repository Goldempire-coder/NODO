from __future__ import annotations

from app.core.errors import ApiError
from app.modules.ads.marketplace_cache import MARKETPLACE_CACHE_PREFIX, MARKETPLACE_ORDER_INVALIDATION_DEBOUNCE_SECONDS
from app.modules.ads.models import AdRecord
from app.modules.businesses.access_control import require_active_business_access
from app.modules.businesses.models import BusinessPaymentMethodRecord, BusinessRecord
from app.modules.orders.helpers import require_uuid
from app.modules.orders.state_machine import ensure_aware, is_waiting_payment_expired, now_utc
from app.modules.users.models import UserRecord


class OrderServiceSupportMixin:
    def _clear_marketplace_cache(self) -> None:
        if self._marketplace_cache is not None:  # type: ignore[attr-defined]
            self._marketplace_cache.clear_prefix(MARKETPLACE_CACHE_PREFIX)  # type: ignore[attr-defined]

    def _clear_marketplace_cache_after_order(self, ad_id: str) -> None:
        if self._marketplace_cache is None:  # type: ignore[attr-defined]
            return
        cache = self._marketplace_cache  # type: ignore[attr-defined]
        marked = False
        if hasattr(cache, "set_marker"):
            marked = bool(cache.set_marker(f"ad_unavailable:{ad_id}", self._settings.marketplace_cache_ttl_seconds))  # type: ignore[attr-defined]
        if marked and hasattr(cache, "clear_prefix_debounced"):
            cache.clear_prefix_debounced(  # type: ignore[attr-defined]
                MARKETPLACE_CACHE_PREFIX,
                debounce_key="order_create",
                debounce_seconds=MARKETPLACE_ORDER_INVALIDATION_DEBOUNCE_SECONDS,
            )
            return
        self._clear_marketplace_cache()

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
        if not business.is_accepting_orders:
            raise ApiError("BUSINESS_OFFLINE", status_code=409)
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

    def _return_or_expire_ad(self, ad: AdRecord, *, actor: UserRecord | None, request_id: str, related_order_id: str | None = None) -> None:
        if self._ad_expired(ad):
            ledger = self._ads.expire_hold(  # type: ignore[attr-defined]
                ad=ad,
                created_by=actor.id if actor else None,
                reason="ad_expired_after_order_without_purchase",
                related_order_id=related_order_id,
                source="orders",
            )
            self._clear_marketplace_cache()
            self._audit.write(  # type: ignore[attr-defined]
                event_type="ad_expired",
                actor_user_id=actor.id if actor else None,
                actor_role=actor.role if actor else None,
                resource_type="ad",
                resource_id=ad.id,
                request_id=request_id,
            )
            if ledger is not None:
                self._audit.write(  # type: ignore[attr-defined]
                    event_type="credits_consumed",
                    actor_user_id=actor.id if actor else None,
                    actor_role=actor.role if actor else None,
                    resource_type="order" if related_order_id else "ad",
                    resource_id=related_order_id or ad.id,
                    request_id=request_id,
                    metadata_json={"ledger_id": ledger.id, "amount": ledger.amount, "ad_id": ad.id, "reason": "ad_expired_after_order_without_purchase"},
                )
            return
        self._ads.set_status(ad, "active")  # type: ignore[attr-defined]
        self._clear_marketplace_cache()

    def _finalize_cancelled_ad(
        self,
        ad: AdRecord,
        *,
        actor: UserRecord | None,
        request_id: str,
        related_order_id: str | None = None,
    ) -> None:
        self._return_or_expire_ad(
            ad,
            actor=actor,
            request_id=request_id,
            related_order_id=related_order_id,
        )

    def _materialize_order_expiration(self, order, *, actor: UserRecord | None, request_id: str):  # type: ignore[no-untyped-def]
        if not is_waiting_payment_expired(order):
            return order
        try:
            result = self._repository.cancel_waiting_payment_atomically(  # type: ignore[attr-defined]
                order_id=order.id,
                expected_remitter_user_id=None,
                expected_business_id=None,
                transition_at=now_utc(),
                require_expired=True,
                enforce_payment_not_sent_confirmation=False,
                payment_not_sent_confirmed=False,
                cancel_reason="payment_not_reported_in_time",
                event_type="order_cancelled_by_timeout",
                actor_user_id=actor.id if actor else None,
                actor_role=actor.role if actor else None,
                event_reason="payment_not_reported_in_time",
                request_id=request_id,
                event_metadata={"ad_id": order.ad_id},
                audit_event_type="order_expired",
                audit_metadata={
                    "from_status": "waiting_payment",
                    "to_status": "cancelled",
                    "reason": "payment_not_reported_in_time",
                },
            )
        except ApiError as exc:
            if exc.code != "ORDER_STATE_CONFLICT":
                raise
            current = self._repository.get_by_id(order.id)  # type: ignore[attr-defined]
            return current or order
        if (
            not self._repository.moves_ad_on_atomic_cancel  # type: ignore[attr-defined]
            or result.ad_requires_expiration
        ):
            ad = self._ads.get_ad(order.ad_id)  # type: ignore[attr-defined]
            if ad is not None:
                self._finalize_cancelled_ad(
                    ad,
                    actor=actor,
                    request_id=request_id,
                    related_order_id=order.id,
                )
        else:
            self._clear_marketplace_cache()
        return result.order
