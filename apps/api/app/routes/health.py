from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.errors import api_error_response
from app.services.health_service import HealthService

router = APIRouter(tags=["foundation"])


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


@router.get("/health")
def health(request: Request) -> dict:
    service = HealthService(request.app.state.settings)
    return {"data": service.health(), "request_id": _request_id(request)}


@router.get("/version")
def version(request: Request) -> dict:
    service = HealthService(request.app.state.settings)
    return {"data": service.version(), "request_id": _request_id(request)}


@router.get("/ready")
def ready(request: Request):
    service = HealthService(request.app.state.settings)
    ok, payload = service.readiness()
    if not ok:
        return api_error_response("UPSTREAM_UNAVAILABLE", "Servicio no listo.", _request_id(request), status_code=503)
    return {"data": payload, "request_id": _request_id(request)}
