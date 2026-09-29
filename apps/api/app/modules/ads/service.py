from __future__ import annotations

import time
from typing import Any

from app.modules.ads.audit_events import ad_creation_audit_events
from app.core.config import Settings
from app.core.errors import ApiError
from app.modules.ads.management import AdManagementMixin
from app.modules.ads.marketplace import AdMarketplaceMixin
from app.modules.ads.models import AdRecord
from app.modules.ads.presenters import ad_payload
from app.modules.ads.profiling import profile_attach, profile_enabled, profile_mark
from app.modules.ads.policy import require_publishable_business
from app.modules.ads.rules import calculate_required_credits
from app.modules.ads.schemas import AdCreateRequest
from app.modules.ads.state_machine import is_expired
from app.modules.businesses.access_control import require_active_business_access
from app.modules.businesses.models import BusinessPaymentMethodRecord, BusinessRecord
from app.modules.users.models import UserRecord


class AdService(AdManagementMixin, AdMarketplaceMixin):
    def __init__(
        self,
        *,
        settings: Settings,
        repository,
        business_repository,
        capacity_repository,
        audit_writer,
        rate_limiter,
        marketplace_rate_limiter,
        idempotency_store,
        marketplace_cache,
    ) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._businesses = business_repository
        self._capacity = capacity_repository
        self._audit = audit_writer
        self._rate_limiter = rate_limiter
        self._marketplace_rate_limiter = marketplace_rate_limiter
        self._idempotency = idempotency_store
        self._marketplace_cache = marketplace_cache

    def _rate_limit(self, action: str, user: UserRecord) -> None:
        key = f"ads:{action}:{user.id}"
        if not self._rate_limiter.allow(
            key,
            max_attempts=self._settings.business_rate_limit_max_attempts,
            window_seconds=self._settings.business_rate_limit_window_seconds,
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def _owner_business(self, user: UserRecord) -> BusinessRecord:
        business, _ = require_active_business_access(user=user, business_repository=self._businesses)
        return business

    def _ad_or_404(self, ad_id: str) -> AdRecord:
        ad = self._repository.get_ad(ad_id)
        if ad is None:
            raise ApiError("AD_NOT_FOUND", status_code=404)
        return ad

    def _payment_or_invalid(self, business: BusinessRecord, payment_method_id: str, payment_method: str) -> BusinessPaymentMethodRecord:
        method = self._businesses.get_payment_method(payment_method_id)
        if (
            method is None
            or method.business_id != business.id
            or method.method_type != payment_method
            or method.verified_status != "approved"
            or not method.active
        ):
            raise ApiError("PAYMENT_METHOD_NOT_APPROVED", status_code=400)
        return method

    def _materialize_expired(self, ad: AdRecord, *, actor: UserRecord | None, request_id: str) -> AdRecord:
        if not is_expired(ad):
            return ad
        expired_ledger = self._repository.expire_hold(ad=ad, created_by=actor.id if actor else None)
        ad = self._repository.get_ad(ad.id) or ad
        self._audit.write(
            event_type="ad_expired",
            actor_user_id=actor.id if actor else None,
            actor_role=actor.role if actor else None,
            resource_type="ad",
            resource_id=ad.id,
            request_id=request_id,
        )
        if expired_ledger is not None:
            self._audit.write(
                event_type="credits_consumed",
                actor_user_id=actor.id if actor else None,
                actor_role=actor.role if actor else None,
                resource_type="ad",
                resource_id=ad.id,
                request_id=request_id,
                metadata_json={"ledger_id": expired_ledger.id, "amount": expired_ledger.amount, "reason": "ad_expired_without_purchase"},
            )
        return ad

    def _validate_ad_create_rules(self, *, business: BusinessRecord, payload: AdCreateRequest) -> int:
        require_publishable_business(business)
        if payload.business_id is not None and payload.business_id != business.id:
            raise ApiError("FORBIDDEN", status_code=403)
        if payload.delivery_method != "pago_movil_ve":
            raise ApiError("INVALID_DELIVERY_METHOD", status_code=400)
        if payload.payment_method not in {"zelle", "usdt_trc20"}:
            raise ApiError("INVALID_PAYMENT_METHOD", status_code=400)
        if payload.amount_min_usd > payload.amount_max_usd:
            raise ApiError("AD_AMOUNT_RANGE_INVALID", status_code=400)
        required_credits = calculate_required_credits(payload.amount_max_usd)
        if payload.amount_min_usd < business.min_order_amount_usd:
            raise ApiError("AD_LIMIT_NOT_ALLOWED", status_code=409)
        if payload.amount_max_usd > business.max_order_amount_usd:
            raise ApiError("AD_LIMIT_NOT_ALLOWED", status_code=409)
        return required_credits

    def _publish_ad(self, *, user: UserRecord, business: BusinessRecord, payload: AdCreateRequest, required_credits: int) -> AdRecord:
        return self._repository.publish_ad(
            business_id=business.id,
            payment_method_id=payload.payment_method_id,
            payment_method=payload.payment_method,
            delivery_method=payload.delivery_method,
            rate_bs_per_usd=payload.rate_bs_per_usd,
            amount_min_usd=payload.amount_min_usd,
            amount_max_usd=payload.amount_max_usd,
            required_credits=required_credits,
            created_by=user.id,
        )

    def _write_audit_events(self, events: list[dict]) -> None:
        if hasattr(self._audit, "write_many"):
            self._audit.write_many(events)
            return
        for event in events:
            self._audit.write(**event)

    def create_ad(self, *, user: UserRecord, payload: AdCreateRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        profile = [] if profile_enabled() else None
        profile_started = time.perf_counter()
        stage_started = time.perf_counter()
        self._rate_limit("create", user)
        profile_mark(profile, "service:rate_limit", stage_started)
        stage_started = time.perf_counter()
        business = self._owner_business(user)
        profile_mark(profile, "service:business_access", stage_started)
        stage_started = time.perf_counter()
        idempotency_payload = payload.model_dump()
        profile_mark(profile, "service:idempotency_payload", stage_started)

        def compute() -> dict[str, Any]:
            stage_started = time.perf_counter()
            required_credits = self._validate_ad_create_rules(business=business, payload=payload)
            profile_mark(profile, "service:validate_rules", stage_started)
            stage_started = time.perf_counter()
            self._payment_or_invalid(business, payload.payment_method_id, payload.payment_method)
            profile_mark(profile, "service:get_payment_method", stage_started)
            stage_started = time.perf_counter()
            ad = self._publish_ad(user=user, business=business, payload=payload, required_credits=required_credits)
            profile_mark(profile, "repo:publish_ad", stage_started)
            stage_started = time.perf_counter()
            self._write_audit_events(ad_creation_audit_events(user=user, ad=ad, request_id=request_id))
            profile_mark(profile, "audit:ad_created_published_credits", stage_started)
            stage_started = time.perf_counter()
            response = {"ad": ad_payload(ad), "credit_hold": {"ledger_id": ad.credit_hold_ledger_id, "required_credits": ad.required_credits}}
            profile_mark(profile, "service:ad_payload", stage_started)
            return response

        stage_started = time.perf_counter()
        response = self._idempotency.replay_or_store(f"ads:create:{idempotency_key}" if idempotency_key else None, payload=idempotency_payload, compute=compute)
        profile_mark(profile, "service:idempotency_replay_or_store", stage_started)
        self._clear_marketplace_cache()
        return profile_attach(dict(response), profile, profile_started)


