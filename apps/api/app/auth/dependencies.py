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


def _datetime_to_cache(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _datetime_from_cache(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _user_to_cache(user: UserRecord) -> dict[str, Any]:
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "role": user.role,
        "status": user.status,
        "trust_level": user.trust_level,
        "created_at": _datetime_to_cache(user.created_at),
        "updated_at": _datetime_to_cache(user.updated_at),
        "last_seen_at": _datetime_to_cache(user.last_seen_at),
        "terms_accepted_at": _datetime_to_cache(user.terms_accepted_at),
        "terms_version": user.terms_version,
    }


def _user_from_cache(payload: dict[str, Any]) -> UserRecord:
    return UserRecord(
        id=payload["id"],
        telegram_id=int(payload["telegram_id"]),
        username=payload.get("username"),
        first_name=payload.get("first_name"),
        last_name=payload.get("last_name"),
        phone=payload.get("phone"),
        role=payload.get("role", "remitter"),
        status=payload.get("status", "active"),
        trust_level=payload.get("trust_level"),
        created_at=_datetime_from_cache(payload.get("created_at")) or datetime.now(timezone.utc),
        updated_at=_datetime_from_cache(payload.get("updated_at")) or datetime.now(timezone.utc),
        last_seen_at=_datetime_from_cache(payload.get("last_seen_at")),
        terms_accepted_at=_datetime_from_cache(payload.get("terms_accepted_at")),
        terms_version=payload.get("terms_version"),
    )


def _cached_user(request: Request, user_id: str, profile: list[dict] | None) -> UserRecord | None:
    cache = getattr(request.app.state, "auth_user_cache", None)
    ttl_seconds = getattr(request.app.state.settings, "auth_user_cache_ttl_seconds", 0)
    if cache is None or ttl_seconds <= 0:
        return None
    stage_started = time.perf_counter()
    cached = cache.get_json(f"auth:user:{user_id}")
    _profile_mark(profile, "auth:user_cache_get", stage_started)
    if cached is None:
        return None
    return _user_from_cache(cached)


def _cache_user(request: Request, user: UserRecord, profile: list[dict] | None) -> None:
    cache = getattr(request.app.state, "auth_user_cache", None)
    ttl_seconds = getattr(request.app.state.settings, "auth_user_cache_ttl_seconds", 0)
    if cache is None or ttl_seconds <= 0:
        return
    stage_started = time.perf_counter()
    cache.set_json(f"auth:user:{user.id}", _user_to_cache(user), ttl_seconds)
    _profile_mark(profile, "auth:user_cache_set", stage_started)


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
    user = _cached_user(request, payload["sub"], profile)
    if user is None:
        user = request.app.state.user_repository.get_user_by_id(payload["sub"])
        if user is not None:
            _cache_user(request, user, profile)
    _profile_mark(profile, "auth:get_user_by_id", stage_started)
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
    if user.role == "remitter":
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
