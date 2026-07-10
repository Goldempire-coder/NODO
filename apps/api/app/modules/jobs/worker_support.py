from __future__ import annotations

import os
import time
from dataclasses import dataclass

from app.modules.jobs.models import JobRunRecord


@dataclass
class JobCounters:
    processed: int = 0
    changed: int = 0
    skipped: int = 0
    failed: int = 0


def profile_enabled() -> bool:
    return os.getenv("NODO_INTERNAL_PROFILING") == "1"


def profile_mark(profile: list[dict] | None, stage: str, started_at: float) -> None:
    if profile is not None:
        profile.append({"stage": stage, "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 4)})


def serialize_run(run: JobRunRecord) -> dict:
    return {
        "id": run.id,
        "job_type": run.job_type,
        "status": run.status,
        "lock_key": run.lock_key,
        "lock_acquired": run.lock_acquired,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "duration_ms": run.duration_ms,
        "processed_count": run.processed_count,
        "changed_count": run.changed_count,
        "skipped_count": run.skipped_count,
        "failed_count": run.failed_count,
        "error_code": run.error_code,
        "error_message_safe": run.error_message_safe,
    }


def counter_payload(counters: JobCounters) -> dict:
    payload = {
        "processed_count": counters.processed,
        "changed_count": counters.changed,
        "skipped_count": counters.skipped,
        "failed_count": counters.failed,
    }
    if profile_enabled():
        orders_profile = getattr(counters, "_orders_profile", None)
        if orders_profile is not None:
            payload["_orders_profile"] = orders_profile
    return payload


def attach_profile(payload: dict, profile: list[dict] | None, started_at: float) -> dict:
    if profile is not None:
        payload["_profile"] = {
            "total_ms": round((time.perf_counter() - started_at) * 1000, 4),
            "stages": profile,
        }
    return payload
