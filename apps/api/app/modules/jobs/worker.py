from __future__ import annotations

import time
from datetime import datetime

from app.modules.jobs.models import (
    JOB_LOCK_EXPIRE_AND_ESCALATE,
    JOB_LOCK_TTL_SECONDS,
    JOB_TYPE_EXPIRE_AND_ESCALATE,
    new_id,
    utc_now,
)
from app.modules.jobs.ad_founder_expiration_processor import AdFounderExpirationProcessor
from app.modules.jobs.order_expiration_processor import OrderExpirationProcessor
from app.modules.jobs.run_lifecycle import JobRunLifecycleMixin
from app.modules.jobs.worker_side_effects import JobWorkerSideEffectsMixin
from app.modules.jobs.worker_support import JobCounters, attach_profile, counter_payload, profile_enabled, profile_mark, serialize_run


class ExpireAndEscalateOrdersWorker(JobRunLifecycleMixin, JobWorkerSideEffectsMixin):
    def __init__(
        self,
        *,
        job_repository,
        lock_manager,
        order_repository,
        ad_repository,
        business_repository,
        dispute_repository,
        audit_writer,
    ) -> None:
        self._jobs = job_repository
        self._locks = lock_manager
        self._orders = order_repository
        self._businesses = business_repository
        self._audit = audit_writer
        self._order_processor = OrderExpirationProcessor(
            order_repository=order_repository,
            ad_repository=ad_repository,
            business_repository=business_repository,
            dispute_repository=dispute_repository,
            audit_writer=audit_writer,
            notify=self._notify,
            state_event=self._state_event,
            audit_notification=self._audit_notification,
        )
        self._ad_founder_processor = AdFounderExpirationProcessor(
            ad_repository=ad_repository,
            business_repository=business_repository,
            audit_writer=audit_writer,
            notify=self._notify,
        )

    def run(self, *, current_time: datetime | None = None, batch_size: int = 100, dry_run: bool = False, request_id: str = "job_request") -> dict:
        profile = [] if profile_enabled() else None
        profile_started = time.perf_counter()
        now = current_time or utc_now()
        owner = new_id()
        stage_started = time.perf_counter()
        lock_acquired = self._locks.acquire(JOB_LOCK_EXPIRE_AND_ESCALATE, owner, JOB_LOCK_TTL_SECONDS)
        profile_mark(profile, "lock:acquire", stage_started)
        if not lock_acquired:
            return self._lock_not_acquired_response(now=now, dry_run=dry_run, request_id=request_id, profile=profile, profile_started=profile_started)

        if dry_run:
            return self._run_dry_locked(
                now=now,
                batch_size=batch_size,
                request_id=request_id,
                owner=owner,
                profile=profile,
                profile_started=profile_started,
            )

        run = self._create_started_run(now=now, dry_run=dry_run, profile=profile)
        stage_started = time.perf_counter()
        self._audit_job("job_started", run, request_id=request_id)
        profile_mark(profile, "audit:job_started", stage_started)
        counters = JobCounters()
        try:
            self._process_all(now=now, batch_size=batch_size, dry_run=dry_run, request_id=request_id, counters=counters, profile=profile)
            run = self._finish_started_run(run=run, now=now, dry_run=dry_run, counters=counters, profile=profile)
            stage_started = time.perf_counter()
            self._audit_job("job_finished", run, request_id=request_id, extra=counter_payload(counters))
            profile_mark(profile, "audit:job_finished", stage_started)
        except Exception as exc:
            counters.failed += 1
            run = self._fail_started_run(run=run, now=now, dry_run=dry_run, counters=counters, exc=exc, profile=profile)
            stage_started = time.perf_counter()
            self._audit_job("job_failed", run, request_id=request_id, extra={"error_code": getattr(exc, "code", "INTERNAL_ERROR")})
            profile_mark(profile, "audit:job_failed", stage_started)
        finally:
            stage_started = time.perf_counter()
            self._locks.release(JOB_LOCK_EXPIRE_AND_ESCALATE, owner)
            profile_mark(profile, "lock:release", stage_started)
        return attach_profile({"job_run": serialize_run(run), "counters": counter_payload(counters)}, profile, profile_started)

    def _run_dry_locked(
        self,
        *,
        now: datetime,
        batch_size: int,
        request_id: str,
        owner: str,
        profile: list[dict] | None,
        profile_started: float,
    ) -> dict:
        counters = JobCounters()
        started_at = now
        try:
            self._process_all(now=now, batch_size=batch_size, dry_run=True, request_id=request_id, counters=counters, profile=profile)
            run = self._create_dry_run_terminal(started_at=started_at, counters=counters, profile=profile)
        except Exception as exc:
            counters.failed += 1
            run = self._create_dry_run_failed(started_at=started_at, counters=counters, exc=exc, profile=profile)
            stage_started = time.perf_counter()
            self._audit_job("job_failed", run, request_id=request_id, extra={"error_code": getattr(exc, "code", "INTERNAL_ERROR")})
            profile_mark(profile, "audit:job_failed_dry_run", stage_started)
        finally:
            stage_started = time.perf_counter()
            self._locks.release(JOB_LOCK_EXPIRE_AND_ESCALATE, owner)
            profile_mark(profile, "lock:release", stage_started)
        return attach_profile({"job_run": serialize_run(run), "counters": counter_payload(counters)}, profile, profile_started)

    def _lock_not_acquired_response(self, *, now: datetime, dry_run: bool, request_id: str, profile: list[dict] | None, profile_started: float) -> dict:
        stage_started = time.perf_counter()
        run = self._jobs.create_job_run(
            job_type=JOB_TYPE_EXPIRE_AND_ESCALATE,
            status="lock_not_acquired",
            lock_key=JOB_LOCK_EXPIRE_AND_ESCALATE,
            lock_acquired=False,
            attempts=1,
            started_at=now,
            finished_at=now,
            duration_ms=0,
            error_code="JOB_LOCK_NOT_ACQUIRED",
            error_message_safe="No se obtuvo el lock del job.",
            metadata_json={"dry_run": dry_run},
        )
        profile_mark(profile, "repo:create_job_run_lock_not_acquired", stage_started)
        stage_started = time.perf_counter()
        self._audit_job("job_failed", run, request_id=request_id, extra={"error_code": "JOB_LOCK_NOT_ACQUIRED"})
        profile_mark(profile, "audit:job_failed_lock_not_acquired", stage_started)
        return attach_profile({"job_run": serialize_run(run), "counters": counter_payload(JobCounters())}, profile, profile_started)

    def _process_all(self, *, now: datetime, batch_size: int, dry_run: bool, request_id: str, counters: JobCounters, profile: list[dict] | None) -> None:
        stage_started = time.perf_counter()
        self._process_orders(now=now, batch_size=batch_size, dry_run=dry_run, request_id=request_id, counters=counters)
        profile_mark(profile, "worker:process_orders", stage_started)
        stage_started = time.perf_counter()
        self._process_ads(now=now, batch_size=batch_size, dry_run=dry_run, request_id=request_id, counters=counters)
        profile_mark(profile, "worker:process_ads", stage_started)
        stage_started = time.perf_counter()
        self._process_founders(now=now, batch_size=batch_size, dry_run=dry_run, request_id=request_id, counters=counters)
        profile_mark(profile, "worker:process_founders", stage_started)
        stage_started = time.perf_counter()
        self._process_public_reputation_snapshots(
            now=now,
            batch_size=batch_size,
            dry_run=dry_run,
            counters=counters,
        )
        profile_mark(profile, "worker:process_public_reputation_snapshots", stage_started)

    def _process_orders(self, *, now: datetime, batch_size: int, dry_run: bool, request_id: str, counters: JobCounters) -> None:
        self._order_processor.process_orders(now=now, batch_size=batch_size, dry_run=dry_run, request_id=request_id, counters=counters)

    def _process_ads(self, *, now: datetime, batch_size: int, dry_run: bool, request_id: str, counters: JobCounters) -> None:
        self._ad_founder_processor.process_ads(now=now, batch_size=batch_size, dry_run=dry_run, request_id=request_id, counters=counters)

    def _process_founders(self, *, now: datetime, batch_size: int, dry_run: bool, request_id: str, counters: JobCounters) -> None:
        self._ad_founder_processor.process_founders(now=now, batch_size=batch_size, dry_run=dry_run, request_id=request_id, counters=counters)

    def _process_public_reputation_snapshots(
        self,
        *,
        now: datetime,
        batch_size: int,
        dry_run: bool,
        counters: JobCounters,
    ) -> None:
        business_ids = self._businesses.publish_due_public_reputation_snapshots(
            current_time=now,
            limit=batch_size,
            dry_run=dry_run,
        )
        counters.processed += len(business_ids)
        if dry_run:
            counters.skipped += len(business_ids)
        else:
            counters.changed += len(business_ids)

