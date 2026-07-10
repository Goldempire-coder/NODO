from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Header, Query, Request

from app.auth.dependencies import require_current_user
from app.modules.jobs.service import JobService
from app.modules.users.models import UserRecord

router = APIRouter(prefix="/admin/jobs", tags=["jobs-notifications"])


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def _service(request: Request) -> JobService:
    return JobService(
        repository=request.app.state.job_repository,
        worker=request.app.state.expire_and_escalate_orders_worker,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
        idempotency_store=request.app.state.idempotency_store,
        settings=request.app.state.settings,
    )


@router.get("/runs")
def list_runs(
    request: Request,
    job_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).list_runs(
            user=user,
            job_type=job_type,
            status=status,
            cursor=cursor,
            limit=limit,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.get("/runs/{run_id}")
def run_detail(run_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).run_detail(user=user, run_id=run_id, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.post("/expire-and-escalate-orders/dry-run")
def dry_run(
    request: Request,
    current_time: datetime | None = Query(default=None),
    batch_size: int = Query(default=100, ge=1, le=500),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).dry_run(
            user=user,
            current_time=current_time,
            batch_size=batch_size,
            idempotency_key=idempotency_key,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }
