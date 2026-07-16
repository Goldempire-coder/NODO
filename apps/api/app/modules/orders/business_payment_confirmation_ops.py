from __future__ import annotations

import time
from datetime import timedelta
from typing import Any

from app.core.errors import ApiError
from app.modules.businesses.models import BusinessRecord
from app.modules.orders.business_payment_confirmation_builder import (
    business_payment_confirmation_response,
    payment_confirmation_audit_events,
    payment_confirmed_state_metadata,
)
from app.modules.orders.helpers import profile_attach, profile_enabled, profile_mark, require_uuid
from app.modules.orders.order_copy import ORDER_DISCLAIMER
from app.modules.orders.schemas import OrderActionRequest
from app.modules.orders.state_machine import now_utc, require_business_payment_confirmation_allowed
from app.modules.users.models import UserRecord


class OrderBusinessPaymentConfirmationMixin:
    def confirm_business_payment(self, *, user: UserRecord, order_id: str, payload: OrderActionRequest | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        profile = [] if profile_enabled() else None
        profile_started = time.perf_counter()
        stage_started = time.perf_counter()
        business = self._approved_business_for_owner(user)  # type: ignore[attr-defined]
        profile_mark(profile, "service:business_access", stage_started)
        stage_started = time.perf_counter()
        self._rate_limit("business_confirm_payment", user)  # type: ignore[attr-defined]
        profile_mark(profile, "service:rate_limit", stage_started)
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND") or order_id

        def compute() -> dict[str, Any]:
            return self._compute_confirm_business_payment(
                order_id=order_id,
                business=business,
                user=user,
                payload=payload,
                request_id=request_id,
                idempotency_key=idempotency_key,
                profile=profile,
                profile_started=profile_started,
            )

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"orders:business_confirm:{user.id}:{order_id}:{idempotency_key}",
            payload={"order_id": order_id, "reason": payload.reason if payload else None},
            compute=compute,
        )

    def _compute_confirm_business_payment(
        self,
        *,
        order_id: str,
        business: BusinessRecord,
        user: UserRecord,
        payload: OrderActionRequest | None,
        request_id: str,
        idempotency_key: str,
        profile: list[dict[str, Any]] | None,
        profile_started: float,
    ) -> dict[str, Any]:
        stage_started = time.perf_counter()
        updated, updated_report, ledger = self._confirm_payment_records(order_id=order_id, business=business, user=user, profile=profile)
        profile_mark(profile, "repo:confirm_payment_atomic", stage_started)

        reason = payload.reason if payload else None
        self._record_payment_confirmation(
            updated=updated,
            updated_report=updated_report,
            ledger=ledger,
            user=user,
            reason=reason,
            request_id=request_id,
            idempotency_key=idempotency_key,
            profile=profile,
        )
        self._notifications.payment_confirmed_client(order=updated, request_id=request_id)  # type: ignore[attr-defined]

        stage_started = time.perf_counter()
        response = business_payment_confirmation_response(order=updated, report=updated_report, ledger=ledger, disclaimer=ORDER_DISCLAIMER)
        profile_mark(profile, "service:public_business_order_payload", stage_started)
        return profile_attach(response, profile, profile_started)

    def _confirm_payment_records(self, *, order_id: str, business: BusinessRecord, user: UserRecord, profile: list[dict[str, Any]] | None) -> tuple[Any, Any, Any]:
        if hasattr(self._repository, "confirm_business_payment_with_credit_consumption"):  # type: ignore[attr-defined]
            return self._repository.confirm_business_payment_with_credit_consumption(order_id=order_id, business_id=business.id, actor_user_id=user.id, profile=profile)  # type: ignore[attr-defined]

        order = self._repository.get_by_id_for_business(order_id=order_id, business_id=business.id)  # type: ignore[attr-defined]
        if order is None:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        require_business_payment_confirmation_allowed(order)
        report = self._repository.get_submitted_payment_report_for_order(order.id)  # type: ignore[attr-defined]
        if report is None:
            raise ApiError("PAYMENT_REPORT_NOT_FOUND", status_code=404)
        ad = self._ads.get_ad(order.ad_id)  # type: ignore[attr-defined]
        if ad is None or ad.business_id != business.id:
            raise ApiError("AD_NOT_FOUND", status_code=404)

        now = now_utc()
        ledger = self._ads.consume_hold_for_order(ad=ad, order_id=order.id, created_by=user.id)  # type: ignore[attr-defined]
        updated_report = self._repository.update_payment_report(report, status="accepted")  # type: ignore[attr-defined]
        updated = self._repository.update_order(  # type: ignore[attr-defined]
            order,
            status="payment_confirmed",
            payment_confirmed_at=now,
            delivery_warning_at=now + timedelta(minutes=30),
            delivery_deadline_at=now + timedelta(hours=2),
        )
        return updated, updated_report, ledger

    def _record_payment_confirmation(
        self,
        *,
        updated,
        updated_report,
        ledger,
        user: UserRecord,
        reason: str | None,
        request_id: str,
        idempotency_key: str,
        profile: list[dict[str, Any]] | None,
    ) -> None:  # type: ignore[no-untyped-def]
        stage_started = time.perf_counter()
        self._repository.add_state_event(  # type: ignore[attr-defined]
            order_id=updated.id,
            from_status="payment_reported",
            to_status="payment_confirmed",
            event_type="payment_confirmed",
            actor_user_id=user.id,
            actor_role=user.role,
            reason=reason,
            request_id=request_id,
            metadata_json=payment_confirmed_state_metadata(report=updated_report, ledger=ledger, order=updated, idempotency_key=idempotency_key),
        )
        profile_mark(profile, "repo:add_state_event", stage_started)

        stage_started = time.perf_counter()
        audit_events = payment_confirmation_audit_events(user=user, order=updated, report=updated_report, ledger=ledger, reason=reason, request_id=request_id)
        if hasattr(self._audit, "write_many"):  # type: ignore[attr-defined]
            self._audit.write_many(audit_events)  # type: ignore[attr-defined]
        else:
            for event in audit_events:
                self._audit.write(**event)  # type: ignore[attr-defined]
        profile_mark(profile, "audit:confirm_credits_ad", stage_started)
