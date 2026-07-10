from __future__ import annotations

from threading import RLock
from typing import Any

from app.modules.jobs.models import JobRunRecord, NotificationJobRecord, new_id, utc_now


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
