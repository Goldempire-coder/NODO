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
        dispute = self._create_operational_dispute(order, reason=reason)
        self._mark_order_disputed(order, dispute=dispute, reason=reason, event_type=event_type, request_id=request_id)
        self._notify_dispute_opened(order, dispute=dispute, event_type=event_type, now=now)
        counters.changed += 1

    def _create_operational_dispute(self, order, *, reason: str):  # type: ignore[no-untyped-def]
        dispute = self._disputes.create_dispute(  # type: ignore[attr-defined]
            order_id=order.id,
            opened_by_user_id=order.remitter_user_id,
            opened_by_role="remitter",
            previous_order_status=order.status,
            reason=reason,
            description="Disputa abierta automaticamente por vencimiento de deadline operativo.",
        )
        self._disputes.add_event(  # type: ignore[attr-defined]
            dispute_id=dispute.id,
            order_id=order.id,
            actor_user_id=order.remitter_user_id,
            actor_role="remitter",
            event_type="dispute_opened",
            old_status=None,
            new_status=dispute.status,
            reason=reason,
            metadata_json={"job_type": JOB_TYPE_EXPIRE_AND_ESCALATE},
        )
        return dispute

    def _mark_order_disputed(self, order, *, dispute, reason: str, event_type: str, request_id: str) -> None:  # type: ignore[no-untyped-def]
        previous = order.status
        self._orders.update_order(order, status="disputed", dispute_reason=reason)  # type: ignore[attr-defined]
        self._state_event(order.id, previous, "disputed", event_type, reason, request_id)  # type: ignore[attr-defined]
        self._audit.write(  # type: ignore[attr-defined]
            event_type=event_type,
            actor_user_id=None,
            actor_role=None,
            resource_type="order",
            resource_id=order.id,
            request_id=request_id,
            metadata_json={"job_type": JOB_TYPE_EXPIRE_AND_ESCALATE, "dispute_id": dispute.id},
        )

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
