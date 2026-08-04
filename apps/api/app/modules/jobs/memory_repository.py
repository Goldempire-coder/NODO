from __future__ import annotations

from datetime import datetime, timedelta
from threading import RLock
from typing import Any

from app.modules.jobs.models import JobRunRecord, NotificationJobRecord, mask_metadata, new_id, utc_now


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self.job_runs: dict[str, JobRunRecord] = {}
        self.notification_jobs: dict[str, NotificationJobRecord] = {}

    def create_job_run(self, **fields: Any) -> JobRunRecord:
        with self._lock:
            now = utc_now()
            run = JobRunRecord(id=new_id(), created_at=now, updated_at=now, **fields)
            self.job_runs[run.id] = run
            return run

    def update_job_run(self, run: JobRunRecord, **fields: Any) -> JobRunRecord:
        with self._lock:
            for key, value in fields.items():
                setattr(run, key, value)
            run.updated_at = utc_now()
            return run

    def list_job_runs(self, *, job_type: str | None, status: str | None, cursor: str | None, limit: int) -> tuple[list[JobRunRecord], str | None]:
        items = list(self.job_runs.values())
        if job_type:
            items = [item for item in items if item.job_type == job_type]
        if status:
            items = [item for item in items if item.status == status]
        if cursor:
            items = [item for item in items if item.created_at.isoformat() < cursor]
        items.sort(key=lambda item: item.created_at, reverse=True)
        page = items[:limit]
        return page, page[-1].created_at.isoformat() if len(page) == limit else None

    def get_job_run(self, run_id: str) -> JobRunRecord | None:
        return self.job_runs.get(run_id)

    def enqueue_notification(self, **fields: Any) -> tuple[NotificationJobRecord, bool]:
        with self._lock:
            for notification in self.notification_jobs.values():
                if notification.dedupe_key == fields["dedupe_key"]:
                    return notification, False
            now = utc_now()
            notification = NotificationJobRecord(id=new_id(), status="pending", created_at=now, updated_at=now, **fields)
            self.notification_jobs[notification.id] = notification
            return notification, True

    def enqueue_notification_in_transaction(self, _conn=None, **fields: Any) -> tuple[NotificationJobRecord, bool]:  # type: ignore[no-untyped-def]
        return self.enqueue_notification(**fields)

    def list_due_notifications(self, *, now: datetime, limit: int) -> list[NotificationJobRecord]:
        with self._lock:
            items = [
                item
                for item in self.notification_jobs.values()
                if item.status == "pending" and item.scheduled_for <= now
            ]
            items.sort(key=lambda item: item.scheduled_for)
            claimed = items[:limit]
            for item in claimed:
                item.scheduled_for = now + timedelta(minutes=5)
                item.metadata_json = {
                    **(item.metadata_json or {}),
                    "delivery_state": "processing",
                    "claimed_at": now.isoformat(),
                }
                item.updated_at = utc_now()
            return claimed

    def list_due_telegram_notifications(self, *, now: datetime, limit: int, notification_types: set[str]) -> list[NotificationJobRecord]:
        with self._lock:
            items = [
                item
                for item in self.notification_jobs.values()
                if item.status == "pending"
                and item.scheduled_for <= now
                and item.recipient_user_id is not None
                and item.notification_type in notification_types
                and _is_processable_telegram_notification(item.metadata_json)
            ]
            items.sort(key=lambda item: item.scheduled_for)
            claimed = items[:limit]
            for item in claimed:
                item.scheduled_for = now + timedelta(minutes=5)
                item.metadata_json = {
                    **(item.metadata_json or {}),
                    "delivery_state": "processing",
                    "claimed_at": now.isoformat(),
                }
                item.updated_at = utc_now()
            return claimed

    def update_notification(self, notification: NotificationJobRecord, **fields: Any) -> NotificationJobRecord:
        with self._lock:
            for key, value in fields.items():
                setattr(notification, key, value)
            notification.updated_at = utc_now()
            return notification

    def notification_incident_summary(self, *, limit: int) -> dict[str, Any]:
        with self._lock:
            items = list(self.notification_jobs.values())
        status_counts = {status: sum(1 for item in items if item.status == status) for status in ["pending", "sent", "failed", "skipped", "cancelled"]}
        problem_items = [
            item
            for item in items
            if item.status == "failed" or item.attempts > 0 or item.last_error_code
        ]
        problem_items.sort(key=lambda item: item.updated_at, reverse=True)
        return {
            "status_counts": status_counts,
            "pending_due": sum(1 for item in items if item.status == "pending" and item.scheduled_for <= utc_now()),
            "recent_problems": [_notification_incident_item(item) for item in problem_items[:limit]],
        }


def _is_processable_telegram_notification(metadata: dict | None) -> bool:
    if not metadata:
        return False
    if metadata.get("channel") != "telegram":
        return False
    if metadata.get("target_surface") not in {"business_mini_app", "client_mini_app"}:
        return False
    return bool(str(metadata.get("message_text") or "").strip())


def _notification_incident_item(item: NotificationJobRecord) -> dict[str, Any]:
    return {
        "id": item.id,
        "notification_type": item.notification_type,
        "status": item.status,
        "recipient_role": item.recipient_role,
        "recipient_user_id": item.recipient_user_id,
        "order_id": item.order_id,
        "business_id": item.business_id,
        "attempts": item.attempts,
        "last_error_code": item.last_error_code,
        "metadata": mask_metadata(item.metadata_json),
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }
