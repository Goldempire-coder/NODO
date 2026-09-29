from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any

from app.core.errors import ApiError
from app.modules.admin.policy import require_admin_mutation, require_admin_read
from app.modules.jobs.models import JOB_RUN_STATUSES, JOB_TYPE_EXPIRE_AND_ESCALATE
from app.modules.jobs.serializers import job_run_detail, job_run_summary
from app.modules.users.models import UserRecord


def _profile_enabled() -> bool:
    return os.getenv("NODO_INTERNAL_PROFILING") == "1"


def _profile_mark(profile: list[dict] | None, stage: str, started_at: float) -> None:
    if profile is not None:
        profile.append({"stage": stage, "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 4)})


def _profile_attach(payload: dict[str, Any], profile: list[dict] | None, started_at: float) -> dict[str, Any]:
    if profile is not None:
        existing_profile = payload.get("_profile")
        payload["_profile"] = {
            "total_ms": round((time.perf_counter() - started_at) * 1000, 4),
            "stages": profile,
            "worker": existing_profile,
        }
    return payload


class JobService:
    def __init__(self, *, repository, worker, audit_writer, rate_limiter, idempotency_store, settings) -> None:
        self._repository = repository
        self._worker = worker
        self._audit = audit_writer
        self._rate_limiter = rate_limiter
        self._idempotency = idempotency_store
        self._settings = settings

    def list_runs(self, *, user: UserRecord, job_type: str | None, status: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit(user.id, "jobs_read")
        if job_type and job_type != JOB_TYPE_EXPIRE_AND_ESCALATE:
            raise ApiError("JOB_NOT_FOUND", status_code=404)
        if status and status not in JOB_RUN_STATUSES:
            raise ApiError("VALIDATION_ERROR", status_code=422)
        items, next_cursor = self._repository.list_job_runs(job_type=job_type, status=status, cursor=cursor, limit=limit)
        self._audit.write(
            event_type="admin_viewed_job_runs",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="job_run",
            resource_id=None,
            request_id=request_id,
            metadata_json={"job_type": job_type, "status": status},
        )
        return {"items": [job_run_summary(item) for item in items], "next_cursor": next_cursor}

    def run_detail(self, *, user: UserRecord, run_id: str, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit(user.id, "jobs_read")
        run = self._repository.get_job_run(run_id)
        if run is None:
            raise ApiError("JOB_NOT_FOUND", status_code=404)
        self._audit.write(
            event_type="admin_viewed_job_run_detail",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="job_run",
            resource_id=run.id,
            request_id=request_id,
            metadata_json={"job_type": run.job_type},
        )
        return job_run_detail(run)

    def dry_run(self, *, user: UserRecord, current_time: datetime | None, batch_size: int, idempotency_key: str | None, request_id: str) -> dict[str, Any]:
        profile = [] if _profile_enabled() else None
        profile_started = time.perf_counter()
        stage_started = time.perf_counter()
        require_admin_mutation(user)
        self._rate_limit(user.id, "jobs_dry_run")
        _profile_mark(profile, "service:auth_and_rate_limit", stage_started)
        clean_idempotency_key = (idempotency_key or "").strip()
        if not clean_idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        payload = {"job_type": JOB_TYPE_EXPIRE_AND_ESCALATE, "current_time": current_time.isoformat() if current_time else None, "batch_size": batch_size}

        def compute() -> dict[str, Any]:
            stage_started = time.perf_counter()
            result = self._worker.run(current_time=current_time, batch_size=batch_size, dry_run=True, request_id=request_id)
            _profile_mark(profile, "worker:run_dry_run", stage_started)
            stage_started = time.perf_counter()
            self._audit.write(
                event_type="job_dry_run_executed",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="job_run",
                resource_id=result["job_run"]["id"],
                request_id=request_id,
                metadata_json={
                    "job_type": JOB_TYPE_EXPIRE_AND_ESCALATE,
                    "current_time": result["job_run"]["started_at"],
                },
            )
            _profile_mark(profile, "audit:job_dry_run_executed", stage_started)
            return _profile_attach(result, profile, profile_started)

        stage_started = time.perf_counter()
        result = self._idempotency.replay_or_store(f"jobs:dry_run:{user.id}:{clean_idempotency_key}", payload=payload, compute=compute)
        _profile_mark(profile, "service:idempotency_replay_or_store", stage_started)
        if _profile_enabled():
            if "_profile" in result:
                result["_profile"]["total_ms"] = round((time.perf_counter() - profile_started) * 1000, 4)
                result["_profile"]["stages"] = profile
            else:
                result = _profile_attach(result, profile, profile_started)
        return result

    def _rate_limit(self, user_id: str, action: str) -> None:
        key = f"jobs:{action}:{user_id}"
        if not self._rate_limiter.allow(key, max_attempts=60, window_seconds=60):
            raise ApiError("RATE_LIMITED", status_code=429)
