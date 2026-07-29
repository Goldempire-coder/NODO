from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response

from app.auth.dependencies import require_current_user_with_terms
from app.modules.notifications.attention import SurfaceAttentionService
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
    )
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "data": service.summary(
            user=user,
            surface=surface,
        )
    }
