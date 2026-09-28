from __future__ import annotations

from datetime import datetime

from app.modules.jobs.models import JOB_TYPE_EXPIRE_AND_ESCALATE
from app.modules.jobs.worker_support import JobCounters


class OrderDisputeEscalationMixin:
    def _open_dispute(self, order, *, reason: str, event_type: str, now: datetime, dry_run: bool, request_id: str, counters: JobCounters) -> None:  # type: ignore[no-untyped-def]
        if self._disputes.get_open_for_order(order.id) is not None:  # type: ignore[attr-defined]
            counters.skipped += 1
            return
        if dry_run:
            counters.changed += 1
            return
        result = self._orders.open_overdue_dispute_atomically(  # type: ignore[attr-defined]
            order_id=order.id, reason=reason, transition_at=now,
            request_id=request_id,
            event_metadata={"job_type": JOB_TYPE_EXPIRE_AND_ESCALATE},
        )
        if result is None:
            counters.skipped += 1
            return
        updated, dispute = result
        self._notify_dispute_opened(updated, dispute=dispute, event_type=event_type, now=now)
        counters.changed += 1

    def _notify_dispute_opened(self, order, *, dispute, event_type: str, now: datetime) -> None:  # type: ignore[no-untyped-def]
        business = self._businesses.get_business(order.business_id)  # type: ignore[attr-defined]
        self._notify(  # type: ignore[attr-defined]
            notification_type=event_type,
            dedupe_key=f"order:{order.id}:{event_type}:remitter",
            scheduled_for=now,
            recipient_user_id=order.remitter_user_id,
            order_id=order.id,
            business_id=order.business_id,
            dispute_id=dispute.id,
        )
        if business is not None:
            self._notify(  # type: ignore[attr-defined]
                notification_type=event_type,
                dedupe_key=f"order:{order.id}:{event_type}:business",
                scheduled_for=now,
                recipient_user_id=business.owner_user_id,
                order_id=order.id,
                business_id=order.business_id,
                dispute_id=dispute.id,
            )
        for role in ("admin", "support"):
            self._notify(  # type: ignore[attr-defined]
                notification_type=event_type,
                dedupe_key=f"order:{order.id}:{event_type}:{role}",
                scheduled_for=now,
                recipient_role=role,
                order_id=order.id,
                business_id=order.business_id,
                dispute_id=dispute.id,
            )
