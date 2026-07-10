from __future__ import annotations

import time
from datetime import datetime

from app.modules.jobs.models import JOB_LOCK_EXPIRE_AND_ESCALATE, JOB_TYPE_EXPIRE_AND_ESCALATE, JobRunRecord, utc_now
from app.modules.jobs.worker_support import JobCounters, profile_mark


class JobRunLifecycleMixin:
    def _create_started_run(self, *, now: datetime, dry_run: bool, profile: list[dict] | None) -> JobRunRecord:
        stage_started = time.perf_counter()
        run = self._jobs.create_job_run(  # type: ignore[attr-defined]
            job_type=JOB_TYPE_EXPIRE_AND_ESCALATE,
            status="started",
            lock_key=JOB_LOCK_EXPIRE_AND_ESCALATE,
            lock_acquired=True,
            attempts=1,
            started_at=now,
            metadata_json={"dry_run": dry_run},
        )
        profile_mark(profile, "repo:create_job_run_started", stage_started)
        return run

    def _finish_started_run(self, *, run: JobRunRecord, now: datetime, dry_run: bool, counters: JobCounters, profile: list[dict] | None) -> JobRunRecord:
        finished_at = utc_now()
        duration_ms = int((finished_at - (run.started_at or now)).total_seconds() * 1000)
        status = "skipped" if counters.changed == 0 else "finished"
        stage_started = time.perf_counter()
        updated = self._jobs.update_job_run(  # type: ignore[attr-defined]
            run,
            status=status,
            finished_at=finished_at,
            duration_ms=max(duration_ms, 0),
            processed_count=counters.processed,
            changed_count=counters.changed,
            skipped_count=counters.skipped,
            failed_count=counters.failed,
            metadata_json={"dry_run": dry_run},
        )
        profile_mark(profile, "repo:update_job_run_terminal", stage_started)
        return updated

    def _fail_started_run(self, *, run: JobRunRecord, now: datetime, dry_run: bool, counters: JobCounters, exc: Exception, profile: list[dict] | None) -> JobRunRecord:
        finished_at = utc_now()
        stage_started = time.perf_counter()
        failed = self._jobs.update_job_run(  # type: ignore[attr-defined]
            run,
            status="failed",
            finished_at=finished_at,
            duration_ms=int((finished_at - (run.started_at or now)).total_seconds() * 1000),
            processed_count=counters.processed,
            changed_count=counters.changed,
            skipped_count=counters.skipped,
            failed_count=counters.failed,
            error_code=getattr(exc, "code", "INTERNAL_ERROR"),
            error_message_safe="No se pudo completar el job.",
            metadata_json={"dry_run": dry_run},
        )
        profile_mark(profile, "repo:update_job_run_failed", stage_started)
        return failed

    def _create_dry_run_terminal(self, *, started_at: datetime, counters: JobCounters, profile: list[dict] | None) -> JobRunRecord:
        finished_at = utc_now()
        status = "skipped" if counters.changed == 0 else "finished"
        stage_started = time.perf_counter()
        run = self._jobs.create_job_run(  # type: ignore[attr-defined]
            job_type=JOB_TYPE_EXPIRE_AND_ESCALATE,
            status=status,
            lock_key=JOB_LOCK_EXPIRE_AND_ESCALATE,
            lock_acquired=True,
            attempts=1,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=max(int((finished_at - started_at).total_seconds() * 1000), 0),
            processed_count=counters.processed,
            changed_count=counters.changed,
            skipped_count=counters.skipped,
            failed_count=counters.failed,
            metadata_json={"dry_run": True},
        )
        profile_mark(profile, "repo:create_job_run_terminal_dry_run", stage_started)
        return run

    def _create_dry_run_failed(self, *, started_at: datetime, counters: JobCounters, exc: Exception, profile: list[dict] | None) -> JobRunRecord:
        finished_at = utc_now()
        stage_started = time.perf_counter()
        run = self._jobs.create_job_run(  # type: ignore[attr-defined]
            job_type=JOB_TYPE_EXPIRE_AND_ESCALATE,
            status="failed",
            lock_key=JOB_LOCK_EXPIRE_AND_ESCALATE,
            lock_acquired=True,
            attempts=1,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=max(int((finished_at - started_at).total_seconds() * 1000), 0),
            processed_count=counters.processed,
            changed_count=counters.changed,
            skipped_count=counters.skipped,
            failed_count=counters.failed,
            error_code=getattr(exc, "code", "INTERNAL_ERROR"),
            error_message_safe="No se pudo completar el dry-run del job.",
            metadata_json={"dry_run": True},
        )
        profile_mark(profile, "repo:create_job_run_failed_dry_run", stage_started)
        return run
