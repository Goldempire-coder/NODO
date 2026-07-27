from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Header, Query, Request

from app.auth.dependencies import require_current_user_with_terms, require_marketplace_read_user
from app.modules.businesses.route_dependencies import business_service as business_access_service
from app.modules.ads.schemas import AdActionRequest, AdCreateRequest, AdUpdateRequest
from app.modules.ads.service import AdService
from app.modules.operations import require_platform_operational
from app.modules.users.models import UserRecord
from app.shared.profiling import staging_response_profile_enabled

router = APIRouter(tags=["ads"])


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def _service(request: Request) -> AdService:
    return AdService(
        settings=request.app.state.settings,
        repository=request.app.state.ad_repository,
        business_repository=request.app.state.business_repository,
        capacity_repository=request.app.state.capacity_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
        marketplace_rate_limiter=request.app.state.marketplace_rate_limiter,
        idempotency_store=request.app.state.idempotency_store,
        marketplace_cache=request.app.state.marketplace_cache,
    )


def _require_business_pin(request: Request, user: UserRecord) -> None:
    business_access_service(request).require_unlocked_business_pin(user=user)


def _attach_dependency_profile(request: Request, data: dict, *, enabled: bool) -> dict:
    if not enabled:
        return data
    auth_profile = getattr(request.state, "nodo_auth_profile", None)
    if auth_profile is None:
        return data
    profiled = dict(data)
    profile = dict(profiled.get("_profile") or {})
    profile["dependency"] = {"auth": auth_profile}
    profiled["_profile"] = profile
    return profiled


@router.get("/ads/search")
def search_ads(
    request: Request,
    amount_usd: Decimal | None = Query(default=None, ge=20),
    payment_method: str | None = Query(default=None, min_length=1),
    delivery_method: str | None = Query(default="pago_movil_ve"),
    sort: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_marketplace_read_user),
) -> dict:
    profile_enabled = staging_response_profile_enabled(request)
    data = _service(request).search(
        user=user,
        amount_usd=amount_usd,
        payment_method=payment_method,
        delivery_method=delivery_method,
        sort=sort,
        cursor=cursor,
        limit=limit,
        profile_enabled=profile_enabled,
    )
    return {
        "data": _attach_dependency_profile(request, data, enabled=profile_enabled),
        "request_id": _request_id(request),
    }


@router.get("/ads/{ad_id}")
def ad_detail(ad_id: str, request: Request, user: UserRecord = Depends(require_marketplace_read_user)) -> dict:
    return {"data": _service(request).detail(user=user, ad_id=ad_id, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.post("/business/ads", status_code=201)
def create_ad(
    payload: AdCreateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    require_platform_operational(request.app.state.emergency_mode_repository, operation="ad_create")
    _require_business_pin(request, user)
    return {
        "data": _service(request).create_ad(user=user, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.get("/business/ads")
def my_ads(
    request: Request,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user_with_terms),
) -> dict:
    return {"data": _service(request).my_ads(user=user, archived=False, cursor=cursor, limit=limit, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.get("/business/ads/archived")
def my_archived_ads(
    request: Request,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user_with_terms),
) -> dict:
    return {"data": _service(request).my_ads(user=user, archived=True, cursor=cursor, limit=limit, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.put("/business/ads/{ad_id}")
def update_ad(
    ad_id: str,
    payload: AdUpdateRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    _require_business_pin(request, user)
    return {
        "data": _service(request).update_ad(user=user, ad_id=ad_id, payload=payload, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.post("/business/ads/{ad_id}/pause")
def pause_ad(
    ad_id: str,
    request: Request,
    payload: AdActionRequest | None = None,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    _require_business_pin(request, user)
    return {
        "data": _service(request).pause_ad(user=user, ad_id=ad_id, reason=payload.reason if payload else None, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.post("/business/ads/{ad_id}/archive")
def archive_ad(
    ad_id: str,
    request: Request,
    payload: AdActionRequest | None = None,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    _require_business_pin(request, user)
    return {
        "data": _service(request).archive_ad(user=user, ad_id=ad_id, reason=payload.reason if payload else None, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.post("/business/ads/{ad_id}/reactivate")
def reactivate_ad(
    ad_id: str,
    request: Request,
    payload: AdActionRequest | None = None,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    require_platform_operational(request.app.state.emergency_mode_repository, operation="ad_reactivate")
    _require_business_pin(request, user)
    return {
        "data": _service(request).reactivate_ad(user=user, ad_id=ad_id, reason=payload.reason if payload else None, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }


@router.post("/business/ads/{ad_id}/republish")
def republish_ad(
    ad_id: str,
    request: Request,
    payload: AdActionRequest | None = None,
    user: UserRecord = Depends(require_current_user_with_terms),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    require_platform_operational(request.app.state.emergency_mode_repository, operation="ad_republish")
    _require_business_pin(request, user)
    return {
        "data": _service(request).republish_ad(user=user, ad_id=ad_id, reason=payload.reason if payload else None, request_id=_request_id(request), idempotency_key=idempotency_key),
        "request_id": _request_id(request),
    }
