from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import require_current_user
from app.core.errors import ApiError
from app.modules.users.models import UserRecord
from app.modules.users.schemas import TermsAcceptanceRequest, UserProfileUpdateRequest
from app.modules.users.service import public_user_payload
from app.modules.users.terms import CURRENT_TERMS_VERSION

router = APIRouter(tags=["users"])


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


@router.get("/users/me")
def me(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": public_user_payload(user), "request_id": _request_id(request)}


@router.post("/users/me/terms-acceptance")
def accept_terms(payload: TermsAcceptanceRequest, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    if payload.terms_version != CURRENT_TERMS_VERSION:
        raise ApiError("TERMS_VERSION_NOT_CURRENT", status_code=400)
    updated = request.app.state.user_repository.accept_terms(user.id, payload.terms_version)
    auth_cache = getattr(request.app.state, "auth_user_cache", None)
    if auth_cache is not None:
        auth_cache.clear_prefix(f"auth:user:{user.id}")
    request.app.state.audit_writer.write(
        event_type="terms_accepted",
        actor_user_id=user.id,
        actor_role=user.role,
        resource_type="user",
        resource_id=user.id,
        request_id=_request_id(request),
        metadata_json={"terms_version": payload.terms_version},
    )
    return {"data": public_user_payload(updated), "request_id": _request_id(request)}


@router.post("/users/me/profile")
def update_profile(payload: UserProfileUpdateRequest, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    first_name = " ".join(payload.first_name.strip().split())
    phone = " ".join(payload.phone.strip().split())
    updated = request.app.state.user_repository.update_profile(user.id, first_name=first_name, phone=phone)
    request.app.state.audit_writer.write(
        event_type="client_profile_completed",
        actor_user_id=user.id,
        actor_role=user.role,
        resource_type="user",
        resource_id=user.id,
        request_id=_request_id(request),
        metadata_json={"has_phone": True},
    )
    return {"data": public_user_payload(updated), "request_id": _request_id(request)}
