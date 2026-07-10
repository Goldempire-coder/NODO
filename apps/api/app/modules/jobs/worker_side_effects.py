from __future__ import annotations

from datetime import datetime

from app.modules.jobs.models import JOB_TYPE_EXPIRE_AND_ESCALATE, JobRunRecord


class JobWorkerSideEffectsMixin:
    def _state_event(self, order_id: str, from_status: str | None, to_status: str, event_type: str, reason: str | None, request_id: str) -> None:
        self._orders.add_state_event(  # type: ignore[attr-defined]
            order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            event_type=event_type,
            actor_user_id=None,
            actor_role=None,
            reason=reason,
            request_id=request_id,
            metadata_json={"job_type": JOB_TYPE_EXPIRE_AND_ESCALATE},
        )

    def _notify(
        self,
        *,
        notification_type: str,
        dedupe_key: str,
        scheduled_for: datetime,
        recipient_user_id: str | None = None,
        recipient_role: str | None = None,
        order_id: str | None = None,
        business_id: str | None = None,
        dispute_id: str | None = None,
        metadata_json: dict | None = None,
    ) -> bool:
        _, created = self._jobs.enqueue_notification(  # type: ignore[attr-defined]
            notification_type=notification_type,
            recipient_user_id=recipient_user_id,
            recipient_role=recipient_role,
            order_id=order_id,
            business_id=business_id,
            dispute_id=dispute_id,
            scheduled_for=scheduled_for,
            dedupe_key=dedupe_key,
            metadata_json=metadata_json or {},
        )
        return created

    def _audit_notification(self, event_type: str, order_id: str, request_id: str, metadata: dict | None = None) -> None:
        self._audit.write(  # type: ignore[attr-defined]
            event_type=event_type,
            actor_user_id=None,
            actor_role=None,
            resource_type="order",
            resource_id=order_id,
            request_id=request_id,
            metadata_json={"job_type": JOB_TYPE_EXPIRE_AND_ESCALATE, **(metadata or {})},
        )

    def _audit_job(self, event_type: str, run: JobRunRecord, *, request_id: str, extra: dict | None = None) -> None:
        self._audit.write(  # type: ignore[attr-defined]
            event_type=event_type,
            actor_user_id=None,
            actor_role=None,
            resource_type="job_run",
            resource_id=run.id,
            request_id=request_id,
            metadata_json={"job_type": run.job_type, "job_id": run.id, **(extra or {})},
        )
