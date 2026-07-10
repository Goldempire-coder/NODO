from __future__ import annotations

from typing import Any

from app.modules.jobs.models import JobRunRecord, mask_metadata


def job_run_summary(run: JobRunRecord) -> dict[str, Any]:
    return {
        "id": run.id,
        "job_type": run.job_type,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "duration_ms": run.duration_ms,
        "processed_count": run.processed_count,
        "changed_count": run.changed_count,
        "skipped_count": run.skipped_count,
        "failed_count": run.failed_count,
        "error_code": run.error_code,
    }


def job_run_detail(run: JobRunRecord) -> dict[str, Any]:
    return {
        **job_run_summary(run),
        "lock_key": run.lock_key,
        "lock_acquired": run.lock_acquired,
        "error_message_safe": run.error_message_safe,
        "metadata": mask_metadata(run.metadata_json),
    }
