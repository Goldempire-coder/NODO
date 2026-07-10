from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import require_current_user
from app.modules.users.models import UserRecord
from app.modules.users.schemas import LogoutRequest, RefreshRequest, TelegramAuthRequest
from app.modules.users.service import AuthService

router = APIRouter(tags=["auth"])


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def _auth_service(request: Request) -> AuthService:
    return AuthService(
        settings=request.app.state.settings,
        repository=request.app.state.user_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
    )


@router.post("/auth/telegram")
def auth_telegram(payload: TelegramAuthRequest, request: Request) -> dict:
    service = _auth_service(request)
    data = service.login_with_telegram(
        init_data=payload.init_data,
        request_id=_request_id(request),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"data": data, "request_id": _request_id(request)}


@router.post("/auth/refresh")
def refresh(payload: RefreshRequest, request: Request) -> dict:
    service = _auth_service(request)
    data = service.refresh(refresh_token=payload.refresh_token, request_id=_request_id(request))
    return {"data": data, "request_id": _request_id(request)}


@router.post("/auth/logout")
def logout(payload: LogoutRequest, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    service = _auth_service(request)
    data = service.logout(refresh_token=payload.refresh_token, user=user, request_id=_request_id(request))
    return {"data": data, "request_id": _request_id(request)}
