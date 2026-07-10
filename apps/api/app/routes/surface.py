from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request

from app.auth.dependencies import require_authenticated_user
from app.core.errors import ApiError
from app.modules.businesses.access_control import (
    BUSINESS_CAPABILITIES,
    evaluate_business_access,
    public_business_for_surface,
    public_user_for_surface,
)
from app.modules.users.models import UserRecord

router = APIRouter(tags=["surface"])


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def _surface_access_denied_response(*, request: Request, user: UserRecord, code: str) -> dict:
    request.app.state.audit_writer.write(
        event_type="surface_access_denied",
        actor_user_id=user.id,
        actor_role=user.role,
        resource_type="surface",
        resource_id="business_mini_app",
        request_id=_request_id(request),
        metadata_json={"error_code": code},
    )
    raise ApiError(code, status_code=403 if code != "BUSINESS_NOT_APPROVED" else 409)


@router.get("/surface/session")
def surface_session(
    request: Request,
    user: UserRecord = Depends(require_authenticated_user),
    surface: str | None = Header(default=None, alias="X-NODO-Surface"),
) -> dict:
    requested_surface = (surface or "").strip()
    if requested_surface == "business_mini_app":
        business = request.app.state.business_repository.get_active_business_for_owner(user.id)
        try:
            business, link = evaluate_business_access(
                user=user,
                business=business,
                business_repository=request.app.state.business_repository,
            )
        except ApiError as exc:
            _surface_access_denied_response(request=request, user=user, code=exc.code)
        return {
            "data": {
                "allowed": True,
                "surface": "business_mini_app",
                "actor_role": user.role,
                "access_state": "allowed",
                "capabilities": BUSINESS_CAPABILITIES,
                "user": public_user_for_surface(user),
                "business": public_business_for_surface(business, link),
            },
            "request_id": _request_id(request),
        }
    if requested_surface in {"client_mini_app", "admin_web"}:
        allowed = user.status == "active" and (
            requested_surface == "client_mini_app" or user.role in {"admin", "super_admin", "support"}
        )
        if not allowed:
            raise ApiError("SURFACE_ACCESS_DENIED", status_code=403)
        return {
            "data": {
                "allowed": True,
                "surface": requested_surface,
                "actor_role": user.role,
                "access_state": "allowed",
                "capabilities": [],
                "user": public_user_for_surface(user),
                "business": None,
            },
            "request_id": _request_id(request),
        }
    raise ApiError("SURFACE_ACCESS_DENIED", status_code=403, message=f"Surface no permitida: {requested_surface or 'missing'}")
