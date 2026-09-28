from __future__ import annotations

from datetime import datetime

from app.modules.jobs.models import JOB_TYPE_EXPIRE_AND_ESCALATE
from app.modules.jobs.worker_support import JobCounters


class OrderCompletionMixin:
    def _handle_delivered(
        self,
        order,
        *,
        now: datetime,
        dry_run: bool,
        request_id: str,
        counters: JobCounters,
        open_dispute_order_ids: set[str] | None = None,
    ) -> None:  # type: ignore[no-untyped-def]
        if order.auto_complete_at and order.auto_complete_at <= now:
            self._auto_complete_delivered_order(
                order,
                now=now,
                dry_run=dry_run,
                request_id=request_id,
                counters=counters,
                open_dispute_order_ids=open_dispute_order_ids,
            )
            return
        self._send_delivered_reminder_if_due(order, now=now, dry_run=dry_run, request_id=request_id, counters=counters)

    def _auto_complete_delivered_order(
        self,
        order,
        *,
        now: datetime,
        dry_run: bool,
        request_id: str,
        counters: JobCounters,
        open_dispute_order_ids: set[str] | None,
    ) -> None:  # type: ignore[no-untyped-def]
        if self._has_open_dispute(order, open_dispute_order_ids):
            counters.skipped += 1
            return
        if dry_run:
            counters.changed += 1
            return
        updated = self._orders.auto_complete_delivered_atomically(  # type: ignore[attr-defined]
            order_id=order.id,
            completed_at=now,
            request_id=request_id,
            event_metadata={"job_type": JOB_TYPE_EXPIRE_AND_ESCALATE},
            audit_metadata={"job_type": JOB_TYPE_EXPIRE_AND_ESCALATE},
        )
        if updated is None:
            counters.skipped += 1
            return
        self._notify_order_auto_completed(updated, now=now)
        counters.changed += 1

    def _has_open_dispute(self, order, open_dispute_order_ids: set[str] | None) -> bool:  # type: ignore[no-untyped-def]
        if open_dispute_order_ids is not None:
            return order.id in open_dispute_order_ids
        return self._disputes.get_open_for_order(order.id) is not None  # type: ignore[attr-defined]

    def _notify_order_auto_completed(self, order, *, now: datetime) -> None:  # type: ignore[no-untyped-def]
        self._notify(  # type: ignore[attr-defined]
            notification_type="order_auto_completed_after_24h",
            dedupe_key=f"order:{order.id}:auto_completed_after_24h:remitter",
            scheduled_for=now,
            recipient_user_id=order.remitter_user_id,
            order_id=order.id,
            business_id=order.business_id,
        )
        business = self._businesses.get_business(order.business_id)  # type: ignore[attr-defined]
        if business is not None:
            self._notify(  # type: ignore[attr-defined]
                notification_type="order_auto_completed_after_24h",
                dedupe_key=f"order:{order.id}:auto_completed_after_24h:business",
                scheduled_for=now,
                recipient_user_id=business.owner_user_id,
                order_id=order.id,
                business_id=order.business_id,
            )

    def _send_delivered_reminder_if_due(self, order, *, now: datetime, dry_run: bool, request_id: str, counters: JobCounters) -> None:  # type: ignore[no-untyped-def]
        windows = [
            ("immediate", order.delivered_at),
            ("12h", order.auto_complete_warning_12h_at),
            ("23h", order.auto_complete_warning_23h_at),
        ]
        for label, deadline in windows:
            if deadline and deadline <= now:
                if dry_run:
                    counters.changed += 1
                    return
                created = self._notify(  # type: ignore[attr-defined]
                    notification_type=f"delivered_reminder_{label}",
                    dedupe_key=f"order:{order.id}:delivered_reminder:{label}",
                    scheduled_for=now,
                    recipient_user_id=order.remitter_user_id,
                    order_id=order.id,
                    business_id=order.business_id,
                    metadata_json={"window": label},
                )
                if created:
                    self._audit_notification("delivered_reminder_sent", order.id, request_id, {"window": label})  # type: ignore[attr-defined]
                    counters.changed += 1
                    return
        counters.skipped += 1
