from __future__ import annotations

import time
from datetime import timedelta
from typing import Any, Callable

from app.core.errors import ApiError
from app.modules.ads.models import AdRecord
from app.modules.businesses.models import BusinessPaymentMethodRecord, BusinessRecord
from app.modules.orders.create_order_builder import bind_created_order_to_audit_events, build_create_order_plan
from app.modules.orders.helpers import profile_attach, profile_enabled, profile_mark, require_uuid
from app.modules.orders.order_copy import ORDER_DISCLAIMER
from app.modules.orders.policy import require_remitter
from app.modules.orders.schemas import OrderCreateRequest
from app.modules.orders.serializers import public_order_payload
from app.modules.orders.state_machine import now_utc
from app.modules.users.models import UserRecord

class OrderCreateFlow:
    def __init__(
        self,
        *,
        repository,
        ad_repository,
        audit_writer,
        idempotency_store,
        rate_limit: Callable[[str, UserRecord], None],
        ad_or_safe_error: Callable[[str], AdRecord],
        business_or_unavailable: Callable[[str], BusinessRecord],
        payment_or_unavailable: Callable[[str], BusinessPaymentMethodRecord],
        ad_expired: Callable[[AdRecord], bool],
        clear_marketplace_cache: Callable[[], None],
        clear_marketplace_cache_after_order: Callable[[str], None],
    ) -> None:  # type: ignore[no-untyped-def]
        self._repository = repository
        self._ads = ad_repository
        self._audit = audit_writer
        self._idempotency = idempotency_store
        self._rate_limit = rate_limit
        self._ad_or_safe_error = ad_or_safe_error
        self._business_or_unavailable = business_or_unavailable
        self._payment_or_unavailable = payment_or_unavailable
        self._ad_expired = ad_expired
        self._clear_marketplace_cache = clear_marketplace_cache
        self._clear_marketplace_cache_after_order = clear_marketplace_cache_after_order

    def create_order(self, *, user: UserRecord, payload: OrderCreateRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        profile = [] if profile_enabled() else None
        profile_started = time.perf_counter()
        stage_started = time.perf_counter()
        require_remitter(user)
        profile_mark(profile, "auth:require_remitter", stage_started)
        stage_started = time.perf_counter()
        self._rate_limit("create", user)
        profile_mark(profile, "rate_limit:order_create", stage_started)
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        request_payload = payload.model_dump()

        def compute() -> dict[str, Any]:
            return self._compute_create_order(
                user=user,
                payload=payload,
                request_id=request_id,
                idempotency_key=idempotency_key,
                profile=profile,
                profile_started=profile_started,
            )

        return self._idempotency.replay_or_store(f"orders:create:{user.id}:{idempotency_key}", payload=request_payload, compute=compute, profile=profile)

    def _compute_create_order(
        self,
        *,
        user: UserRecord,
        payload: OrderCreateRequest,
        request_id: str,
        idempotency_key: str,
        profile: list[dict[str, Any]] | None,
        profile_started: float,
    ) -> dict[str, Any]:
        start_context = self._order_create_start_context(user=user, payload=payload, idempotency_key=idempotency_key, profile=profile)
        existing = start_context.get("existing_order")
        if existing is not None:
            if not self._same_create_payload(existing, payload):
                raise ApiError("IDEMPOTENCY_PAYLOAD_MISMATCH", status_code=409)
            return profile_attach({"order": public_order_payload(existing), "disclaimer": ORDER_DISCLAIMER}, profile, profile_started)

        context = start_context.get("context") or self._order_create_context(user=user, payload=payload, profile=profile)
        ad = context["ad"]
        business = context["business"]
        payment = context["payment"]
        plan = build_create_order_plan(
            user=user,
            payload=payload,
            ad=ad,
            business=business,
            payment=payment,
            deadline=now_utc() + timedelta(minutes=30),
            request_id=request_id,
            idempotency_key=idempotency_key,
        )
        order = self._persist_create_order_plan(ad=ad, plan=plan, profile=profile)
        self._write_created_order_audit(plan=plan, order=order, profile=profile)
        stage_started = time.perf_counter()
        response = {"order": public_order_payload(order), "disclaimer": ORDER_DISCLAIMER}
        profile_mark(profile, "service:public_order_payload", stage_started)
        return profile_attach(response, profile, profile_started)

    def _existing_order_for_idempotency(self, *, user: UserRecord, payload: OrderCreateRequest, idempotency_key: str, profile: list[dict[str, Any]] | None):  # type: ignore[no-untyped-def]
        stage_started = time.perf_counter()
        existing = self._repository.get_by_idempotency_key(remitter_user_id=user.id, idempotency_key=idempotency_key)
        profile_mark(profile, "service:get_existing_idempotency", stage_started)
        if existing is not None and not self._same_create_payload(existing, payload):
            raise ApiError("IDEMPOTENCY_PAYLOAD_MISMATCH", status_code=409)
        return existing

    def _order_create_start_context(
        self,
        *,
        user: UserRecord,
        payload: OrderCreateRequest,
        idempotency_key: str,
        profile: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        if not hasattr(self._repository, "get_order_create_start_context"):
            existing = self._existing_order_for_idempotency(user=user, payload=payload, idempotency_key=idempotency_key, profile=profile)
            return {"existing_order": existing, "context": None}
        stage_started = time.perf_counter()
        ad_id = require_uuid(payload.ad_id, "AD_NOT_FOUND")
        start_context = self._repository.get_order_create_start_context(
            remitter_user_id=user.id,
            idempotency_key=idempotency_key,
            ad_id=ad_id,
        )
        profile_mark(profile, "db_reads:order_create_start_context", stage_started)
        return start_context

    def _available_ad_for_order(self, *, user: UserRecord, payload: OrderCreateRequest, profile: list[dict[str, Any]] | None) -> AdRecord:
        stage_started = time.perf_counter()
        ad = self._ad_or_safe_error(payload.ad_id)
        profile_mark(profile, "service:get_ad", stage_started)
        if self._ad_expired(ad):
            self._ads.set_status(ad, "expired")
            self._clear_marketplace_cache()
            self._ads.release_hold(ad=ad, created_by=user.id)
            raise ApiError("AD_EXPIRED", status_code=409)
        if ad.status != "active":
            raise ApiError("AD_NOT_AVAILABLE", status_code=409)
        return ad

    def _order_create_context(self, *, user: UserRecord, payload: OrderCreateRequest, profile: list[dict[str, Any]] | None) -> dict[str, Any]:
        if not hasattr(self._repository, "get_order_create_context"):
            ad = self._available_ad_for_order(user=user, payload=payload, profile=profile)
            business = self._business_for_order(ad=ad, profile=profile)
            self._validate_order_amount(payload=payload, ad=ad, business=business)
            self._ensure_business_capacity(business=business, profile=profile)
            payment = self._payment_for_order(ad=ad, profile=profile)
            return {"ad": ad, "business": business, "payment": payment}

        stage_started = time.perf_counter()
        ad_id = require_uuid(payload.ad_id, "AD_NOT_FOUND")
        context = self._repository.get_order_create_context(ad_id=ad_id)
        profile_mark(profile, "db_reads:order_create_context", stage_started)
        if context is None:
            raise ApiError("AD_NOT_FOUND", status_code=404)
        ad = context["ad"]
        business = context["business"]
        payment = context["payment"]
        active_order_count = int(context["active_order_count"])
        if self._ad_expired(ad):
            stage_started = time.perf_counter()
            self._ads.set_status(ad, "expired")
            self._clear_marketplace_cache()
            self._ads.release_hold(ad=ad, created_by=user.id)
            profile_mark(profile, "transaction:expire_ad_and_release_hold", stage_started)
            raise ApiError("AD_EXPIRED", status_code=409)
        if ad.status != "active":
            raise ApiError("AD_NOT_AVAILABLE", status_code=409)
        if business.verification_status != "approved" or business.risk_level in {"restricted", "high_risk"}:
            raise ApiError("BUSINESS_NOT_APPROVED", status_code=409)
        self._validate_order_amount(payload=payload, ad=ad, business=business)
        if active_order_count >= business.active_order_limit:
            raise ApiError("AD_NOT_AVAILABLE", status_code=409)
        if payment.business_id != ad.business_id or payment.verified_status != "approved" or not payment.active:
            raise ApiError("AD_NOT_AVAILABLE", status_code=404)
        return {"ad": ad, "business": business, "payment": payment}

    def _business_for_order(self, *, ad: AdRecord, profile: list[dict[str, Any]] | None) -> BusinessRecord:
        stage_started = time.perf_counter()
        business = self._business_or_unavailable(ad.business_id)
        profile_mark(profile, "service:get_business", stage_started)
        return business

    def _validate_order_amount(self, *, payload: OrderCreateRequest, ad: AdRecord, business: BusinessRecord) -> None:
        if payload.amount_usd < ad.amount_min_usd or payload.amount_usd > ad.amount_max_usd:
            raise ApiError("AMOUNT_OUT_OF_RANGE", status_code=400)
        if payload.amount_usd > business.max_order_amount_usd:
            raise ApiError("AMOUNT_OUT_OF_RANGE", status_code=400)

    def _ensure_business_capacity(self, *, business: BusinessRecord, profile: list[dict[str, Any]] | None) -> None:
        stage_started = time.perf_counter()
        if self._repository.count_active_for_business(business.id) >= business.active_order_limit:
            raise ApiError("AD_NOT_AVAILABLE", status_code=409)
        profile_mark(profile, "service:count_active_orders", stage_started)

    def _payment_for_order(self, *, ad: AdRecord, profile: list[dict[str, Any]] | None) -> BusinessPaymentMethodRecord:
        stage_started = time.perf_counter()
        payment = self._payment_or_unavailable(ad.payment_method_id)
        profile_mark(profile, "service:get_payment_method", stage_started)
        return payment

    def _persist_create_order_plan(self, *, ad: AdRecord, plan, profile: list[dict[str, Any]] | None):  # type: ignore[no-untyped-def]
        stage_started = time.perf_counter()
        create_order_fields = dict(plan.create_order_fields)
        if getattr(self._repository, "creates_initial_state_event_on_create_order", False):
            create_order_fields["initial_state_event"] = plan.initial_state_event
        if getattr(self._repository, "creates_audit_events_on_create_order", False):
            create_order_fields["audit_events"] = plan.audit_events
        order = self._repository.create_order(**create_order_fields)
        profile_mark(profile, "transaction:create_order_and_move_ad", stage_started)
        if not getattr(self._repository, "moves_ad_on_create_order", False):
            stage_started = time.perf_counter()
            self._ads.set_status(ad, "in_order")
            profile_mark(profile, "repo:set_ad_in_order", stage_started)
        stage_started = time.perf_counter()
        self._clear_marketplace_cache_after_order(ad.id)
        profile_mark(profile, "cache:marketplace_invalidation", stage_started)
        if not getattr(self._repository, "creates_initial_state_event_on_create_order", False):
            stage_started = time.perf_counter()
            self._repository.add_state_event(order_id=order.id, **plan.initial_state_event)
            profile_mark(profile, "repo:add_state_event", stage_started)
        return order

    def _write_created_order_audit(self, *, plan, order, profile: list[dict[str, Any]] | None) -> None:  # type: ignore[no-untyped-def]
        if getattr(self._repository, "creates_audit_events_on_create_order", False):
            return
        stage_started = time.perf_counter()
        audit_events = bind_created_order_to_audit_events(plan.audit_events, order_id=order.id)
        if hasattr(self._audit, "write_many"):
            self._audit.write_many(audit_events)
        else:
            for event in audit_events:
                self._audit.write(**event)
        profile_mark(profile, "audit:order_created_and_ad_moved", stage_started)

    def _same_create_payload(self, order, payload: OrderCreateRequest) -> bool:  # type: ignore[no-untyped-def]
        return (
            order.ad_id == payload.ad_id
            and order.amount_usd == payload.amount_usd
            and order.receiver_data_json == payload.receiver_data.model_dump()
        )
