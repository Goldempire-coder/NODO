from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Callable

from app.modules.jobs.models import JOB_TYPE_EXPIRE_AND_ESCALATE
from app.modules.jobs.order_completion import OrderCompletionMixin
from app.modules.jobs.order_dispute_escalation import OrderDisputeEscalationMixin
from app.modules.jobs.worker_support import JobCounters, profile_enabled, profile_mark


class OrderExpirationProcessor(OrderCompletionMixin, OrderDisputeEscalationMixin):
    def __init__(
        self,
        *,
        order_repository: Any,
        ad_repository: Any,
        business_repository: Any,
        dispute_repository: Any,
        audit_writer: Any,
        notify: Callable[..., bool],
        state_event: Callable[..., None],
        audit_notification: Callable[..., None],
    ) -> None:
        self._orders = order_repository
        self._ads = ad_repository
        self._businesses = business_repository
        self._disputes = dispute_repository
        self._audit = audit_writer
        self._notify = notify
        self._state_event = state_event
        self._audit_notification = audit_notification

    def process_orders(self, *, now: datetime, batch_size: int, dry_run: bool, request_id: str, counters: JobCounters) -> None:
        profile = [] if profile_enabled() else None
        stage_started = time.perf_counter()
        orders = self._orders.list_job_candidate_orders(limit=batch_size)
        profile_mark(profile, "repo:list_job_candidate_orders", stage_started)
        stage_started = time.perf_counter()
        delivered_auto_complete_order_ids = [
            order.id
            for order in orders
            if order.status == "delivered" and order.auto_complete_at and order.auto_complete_at <= now
        ]
        profile_mark(profile, "worker:filter_delivered_auto_complete_ids", stage_started)
        stage_started = time.perf_counter()
        open_dispute_order_ids = self._disputes.list_open_order_ids(delivered_auto_complete_order_ids)
        profile_mark(profile, "repo:list_open_order_ids", stage_started)
        stage_started = time.perf_counter()
        for order in orders:
            counters.processed += 1
            if order.status == "waiting_payment" and order.payment_report_deadline_at <= now:
                self._cancel_waiting_payment(order, now=now, dry_run=dry_run, request_id=request_id, counters=counters)
            elif order.status == "payment_reported":
                self._handle_payment_reported(order, now=now, dry_run=dry_run, request_id=request_id, counters=counters)
            elif order.status == "payment_confirmed":
                self._handle_payment_confirmed(order, now=now, dry_run=dry_run, request_id=request_id, counters=counters)
            elif order.status == "delivered":
                self._handle_delivered(
                    order,
                    now=now,
                    dry_run=dry_run,
                    request_id=request_id,
                    counters=counters,
                    open_dispute_order_ids=open_dispute_order_ids,
                )
            else:
                counters.skipped += 1
        profile_mark(profile, f"worker:evaluate_orders:{len(orders)}", stage_started)
        if profile is not None:
            setattr(counters, "_orders_profile", profile)

    def _cancel_waiting_payment(self, order, *, now: datetime, dry_run: bool, request_id: str, counters: JobCounters) -> None:  # type: ignore[no-untyped-def]
        if dry_run:
            counters.changed += 1
            return
        ad = self._ads.get_ad(order.ad_id)
        previous = order.status
        self._orders.update_order(order, status="cancelled", cancel_reason="payment_not_reported_in_time")
        business = self._businesses.get_business(order.business_id)
        if ad is not None:
            new_ad_status = "expired" if ad.expires_at and ad.expires_at <= now else "active"
            self._ads.set_status(ad, new_ad_status)
            self._ads.release_hold(ad=ad, created_by=None, reason="payment_not_reported_in_time", related_order_id=order.id, source="jobs")
        self._state_event(order.id, previous, "cancelled", "order_cancelled_payment_not_reported", "payment_not_reported_in_time", request_id)
        self._audit.write(
            event_type="order_cancelled_payment_not_reported",
            actor_user_id=None,
            actor_role=None,
            resource_type="order",
            resource_id=order.id,
            request_id=request_id,
            metadata_json={"job_type": JOB_TYPE_EXPIRE_AND_ESCALATE},
        )
        self._notify(
            notification_type="order_cancelled_payment_not_reported",
            dedupe_key=f"order:{order.id}:payment_not_reported:remitter",
            scheduled_for=now,
            recipient_user_id=order.remitter_user_id,
            order_id=order.id,
            business_id=order.business_id,
        )
        if business is not None:
            self._notify(
                notification_type="order_cancelled_payment_not_reported",
                dedupe_key=f"order:{order.id}:payment_not_reported:business",
                scheduled_for=now,
                recipient_user_id=business.owner_user_id,
                order_id=order.id,
                business_id=order.business_id,
            )
        counters.changed += 1

    def _handle_payment_reported(self, order, *, now: datetime, dry_run: bool, request_id: str, counters: JobCounters) -> None:  # type: ignore[no-untyped-def]
        if order.business_response_deadline_at and order.business_response_deadline_at <= now:
            self._open_dispute(
                order,
                reason="business_no_payment_confirmation",
                event_type="order_disputed_business_no_payment_confirmation",
                now=now,
                dry_run=dry_run,
                request_id=request_id,
                counters=counters,
            )
            return
        if order.business_response_warning_at and order.business_response_warning_at <= now:
            if not dry_run:
                business = self._businesses.get_business(order.business_id)
                created = self._notify(
                    notification_type="order_business_response_warning",
                    dedupe_key=f"order:{order.id}:business_response_warning",
                    scheduled_for=now,
                    recipient_user_id=business.owner_user_id if business else None,
                    recipient_role=None if business else "admin",
                    order_id=order.id,
                    business_id=order.business_id,
                )
                if created:
                    self._audit_notification("order_business_response_warning_sent", order.id, request_id)
                    counters.changed += 1
                else:
                    counters.skipped += 1
            else:
                counters.changed += 1
            return
        counters.skipped += 1

    def _handle_payment_confirmed(self, order, *, now: datetime, dry_run: bool, request_id: str, counters: JobCounters) -> None:  # type: ignore[no-untyped-def]
        if order.delivery_deadline_at and order.delivery_deadline_at <= now:
            self._open_dispute(
                order,
                reason="business_confirmed_payment_but_not_delivered",
                event_type="order_disputed_business_confirmed_payment_but_not_delivered",
                now=now,
                dry_run=dry_run,
                request_id=request_id,
                counters=counters,
            )
            return
        if order.delivery_warning_at and order.delivery_warning_at <= now:
            if not dry_run:
                business = self._businesses.get_business(order.business_id)
                created = self._notify(
                    notification_type="order_delivery_warning",
                    dedupe_key=f"order:{order.id}:delivery_warning",
                    scheduled_for=now,
                    recipient_user_id=business.owner_user_id if business else None,
                    recipient_role=None if business else "admin",
                    order_id=order.id,
                    business_id=order.business_id,
                )
                if created:
                    self._audit_notification("order_delivery_warning_sent", order.id, request_id)
                    counters.changed += 1
                else:
                    counters.skipped += 1
            else:
                counters.changed += 1
            return
        counters.skipped += 1
