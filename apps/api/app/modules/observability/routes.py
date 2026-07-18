from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request

from app.auth.dependencies import require_current_user
from app.modules.observability.schemas import ObservabilityEventsRequest
from app.modules.observability.service import ObservabilityIngestService
from app.modules.users.models import UserRecord
from app.shared.observability import get_request_id

router = APIRouter(tags=["observability"])


@router.post("/observability/events")
def ingest_frontend_observability_events(
    payload: ObservabilityEventsRequest,
    request: Request,
    surface: str | None = Header(default=None, alias="X-NODO-Surface"),
    user: UserRecord = Depends(require_current_user),
) -> dict[str, object]:
    resolved_surface = (surface or getattr(request.state, "surface", "") or "unknown").strip()
    request_id = get_request_id(request)
    service = ObservabilityIngestService(settings=request.app.state.settings, repository=getattr(request.app.state, "observability_repository", None))
    return {
        "data": service.ingest(
            payload=payload,
            user=user,
            surface=resolved_surface,
            request_id=request_id,
        ),
        "request_id": request_id,
    }
