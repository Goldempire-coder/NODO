from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from fastapi import Header, Request

from app.auth.jwt import decode_access_token
from app.core.errors import ApiError
from app.modules.users.models import UserRecord
from app.modules.users.terms import require_current_terms
from app.shared.profiling import internal_profile_enabled, profile_mark, staging_response_profile_enabled

OPERATE_ALLOWED_STATUSES_BY_ROLE = {
    "remitter": {"active", "restricted"},
    "business_owner": {"active", "restricted"},
    "admin": {"active"},
    "super_admin": {"active"},
    "support": {"active"},
}


def _profile_enabled(request: Request | None = None) -> bool:
    return internal_profile_enabled() or (request is not None and staging_response_profile_enabled(request))


def _profile_mark(profile: list[dict] | None, stage: str, started: float) -> None:
    profile_mark(profile, stage, started)


def require_authenticated_user(request: Request, authorization: str | None = Header(default=None)) -> UserRecord:
    profile = [] if _profile_enabled(request) else None
    profile_started = time.perf_counter()
    stage_started = time.perf_counter()
    settings = request.app.state.settings
    if not settings.jwt_secret:
        raise ApiError("UNAUTHENTICATED", status_code=401)
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError("UNAUTHENTICATED", status_code=401)
    _profile_mark(profile, "auth:validate_header", stage_started)
    stage_started = time.perf_counter()
    payload = decode_access_token(authorization.removeprefix("Bearer ").strip(), settings.jwt_secret)
    _profile_mark(profile, "auth:decode_access_token", stage_started)
    stage_started = time.perf_counter()
    user_id = payload.get("sub")
    access_token_jti = payload.get("jti")
    if not isinstance(user_id, str) or not user_id or not isinstance(access_token_jti, str) or not access_token_jti:
        raise ApiError("UNAUTHENTICATED", status_code=401)
    session = request.app.state.user_repository.get_session_by_access_token_jti(access_token_jti)
    _profile_mark(profile, "auth:get_session_by_access_token_jti", stage_started)
    if (
        session is None
        or session.user_id != user_id
        or session.status != "active"
        or request.app.state.user_repository.session_is_expired(session)
    ):
        raise ApiError("SESSION_EXPIRED", status_code=401)
    stage_started = time.perf_counter()
    # Strong auth must observe a status change on the next request. Only the
    # explicitly read-only marketplace dependency may trust fresh JWT claims.
    user = request.app.state.user_repository.get_user_by_id(user_id)
    _profile_mark(profile, "auth:get_user_by_id_fresh", stage_started)
    if user is None:
        raise ApiError("UNAUTHENTICATED", status_code=401)
    if profile is not None:
        request.state.nodo_auth_profile = {
            "total_ms": round((time.perf_counter() - profile_started) * 1000, 4),
            "stages": profile,
        }
    return user


def require_current_user(request: Request, authorization: str | None = Header(default=None)) -> UserRecord:
    user = require_authenticated_user(request, authorization)
    stage_started = time.perf_counter()
    allowed_statuses = OPERATE_ALLOWED_STATUSES_BY_ROLE.get(user.role, {"active"})
    if user.status not in allowed_statuses:
        raise ApiError("USER_SUSPENDED", status_code=403)
    if _profile_enabled(request) and hasattr(request.state, "nodo_auth_profile"):
        request.state.nodo_auth_profile["stages"].append(
            {"stage": "auth:status_check", "elapsed_ms": round((time.perf_counter() - stage_started) * 1000, 4)}
        )
    return user


def require_current_user_with_terms(request: Request, authorization: str | None = Header(default=None)) -> UserRecord:
    user = require_current_user(request, authorization)
    if user.role in {"remitter", "business_owner"}:
        require_current_terms(user)
    return user


def _user_from_fresh_marketplace_claims(payload: dict[str, Any], max_age_seconds: int) -> UserRecord | None:
    issued_at = payload.get("iat")
    if not isinstance(issued_at, int):
        return None
    if max_age_seconds <= 0:
        return None
    if int(time.time()) - issued_at > max_age_seconds:
        return None
    role = payload.get("role")
    status = payload.get("status")
    if not isinstance(role, str) or not isinstance(status, str):
        return None
    return UserRecord(
        id=payload["sub"],
        telegram_id=0,
        username=None,
        first_name=None,
        last_name=None,
        role=role,
        status=status,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def require_marketplace_read_user(request: Request, authorization: str | None = Header(default=None)) -> UserRecord:
    """Lightweight auth for public-safe marketplace reads only.

    Fresh JWT claims avoid a DB user lookup for read-only marketplace endpoints.
    Older tokens fall back to the strong auth path so user status changes are
    bounded by MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS.
    """
    profile = [] if _profile_enabled(request) else None
    profile_started = time.perf_counter()
    stage_started = time.perf_counter()
    settings = request.app.state.settings
    if not settings.jwt_secret:
        raise ApiError("UNAUTHENTICATED", status_code=401)
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError("UNAUTHENTICATED", status_code=401)
    _profile_mark(profile, "auth:marketplace_validate_header", stage_started)
    stage_started = time.perf_counter()
    payload = decode_access_token(authorization.removeprefix("Bearer ").strip(), settings.jwt_secret)
    _profile_mark(profile, "auth:marketplace_decode_access_token", stage_started)
    stage_started = time.perf_counter()
    user = _user_from_fresh_marketplace_claims(payload, settings.marketplace_read_auth_claim_ttl_seconds)
    if user is not None:
        _profile_mark(profile, "auth:marketplace_claim_user", stage_started)
        if profile is not None:
            request.state.nodo_auth_profile = {
                "mode": "marketplace_claims",
                "total_ms": round((time.perf_counter() - profile_started) * 1000, 4),
                "stages": profile,
            }
        return user
    user = require_current_user(request, authorization)
    if _profile_enabled(request) and hasattr(request.state, "nodo_auth_profile"):
        request.state.nodo_auth_profile["mode"] = "marketplace_fallback_db"
    return user
