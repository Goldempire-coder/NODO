from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response

from app.auth.dependencies import require_current_user_with_terms
from app.modules.notifications.attention import SurfaceAttentionService
from app.modules.notifications.schemas import AttentionAcknowledgeRequest
from app.modules.users.models import UserRecord


router = APIRouter(tags=["notifications"])


@router.get("/notifications/attention-summary")
def attention_summary(
    request: Request,
    response: Response,
    user: UserRecord = Depends(require_current_user_with_terms),
    surface: str = Header(alias="X-NODO-Surface"),
) -> dict:
    service = SurfaceAttentionService(
        business_repository=request.app.state.business_repository,
        order_repository=request.app.state.order_repository,
        support_repository=request.app.state.support_repository,
        chat_repository=request.app.state.chat_repository,
        read_repository=request.app.state.surface_attention_read_repository,
    )
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "data": service.summary(
            user=user,
            surface=surface,
        )
    }


@router.post("/notifications/attention/acknowledge")
def acknowledge_attention(
    payload: AttentionAcknowledgeRequest,
    request: Request,
    response: Response,
    user: UserRecord = Depends(require_current_user_with_terms),
    surface: str = Header(alias="X-NODO-Surface"),
) -> dict:
    service = SurfaceAttentionService(
        business_repository=request.app.state.business_repository,
        order_repository=request.app.state.order_repository,
        support_repository=request.app.state.support_repository,
        chat_repository=request.app.state.chat_repository,
        read_repository=request.app.state.surface_attention_read_repository,
    )
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "data": service.acknowledge(
            user=user,
            surface=surface,
            payload=payload,
        )
    }
