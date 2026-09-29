from __future__ import annotations

import json

from fastapi import APIRouter, Header, Request
from pydantic import Field, ValidationError

from app.core.errors import ApiError
from app.modules.users.schemas import AdminCredentialLoginRequest, LogoutRequest, RefreshRequest, TelegramAuthRequest
from app.modules.users.service import AuthService
from app.shared.rate_limit.request_identity import current_request_ip_hash

router = APIRouter(tags=["auth"])


class TelegramAuthEnvelope(TelegramAuthRequest):
    surface: str | None = Field(default=None, max_length=64)


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
async def auth_telegram(
    request: Request,
    surface: str | None = Header(default=None, alias="X-NODO-Surface"),
) -> dict:
    raw_body = await request.body()
    try:
        body = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApiError("TELEGRAM_INIT_DATA_INVALID", status_code=401) from exc
    if not isinstance(body, dict):
        raise ApiError("TELEGRAM_INIT_DATA_INVALID", status_code=401)
    try:
        payload = TelegramAuthEnvelope.model_validate(body)
    except ValidationError as exc:
        raise ApiError("VALIDATION_ERROR", status_code=422) from exc
    body_surface = payload.surface.strip() if isinstance(payload.surface, str) and payload.surface.strip() else None
    raw_header_surface = surface.strip() if isinstance(surface, str) and surface.strip() else None
    header_surface = raw_header_surface if raw_header_surface != "unknown" else None
    service = _auth_service(request)
    data = service.login_with_telegram(
        init_data=payload.init_data,
        rate_limit_ip_hash=current_request_ip_hash(),
        surface=header_surface or body_surface,
        request_id=_request_id(request),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"data": data, "request_id": _request_id(request)}


@router.post("/auth/admin/login")
def auth_admin_login(payload: AdminCredentialLoginRequest, request: Request) -> dict:
    service = _auth_service(request)
    data = service.login_with_admin_credentials(
        username=payload.username,
        rate_limit_ip_hash=current_request_ip_hash(),
        password=payload.password,
        request_id=_request_id(request),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"data": data, "request_id": _request_id(request)}


@router.post("/auth/refresh")
def refresh(payload: RefreshRequest, request: Request) -> dict:
    service = _auth_service(request)
    data = service.refresh(
        rate_limit_ip_hash=current_request_ip_hash(),
        refresh_token=payload.refresh_token,
        request_id=_request_id(request),
        ip_address=request.client.host if request.client else None,
    )
    return {"data": data, "request_id": _request_id(request)}


@router.post("/auth/logout")
def logout(payload: LogoutRequest, request: Request) -> dict:
    service = _auth_service(request)
    data = service.logout(
        rate_limit_ip_hash=current_request_ip_hash(),
        refresh_token=payload.refresh_token,
        request_id=_request_id(request),
        ip_address=request.client.host if request.client else None,
    )
    return {"data": data, "request_id": _request_id(request)}
