from __future__ import annotations

from fastapi import Request

from app.core.errors import ApiError
from app.modules.businesses.legacy_onboarding_service import LegacyBusinessOnboardingService
from app.modules.businesses.service import BusinessService

TEST_FIXTURE_BUSINESS_CREATE_HEADER = "x-nodo-test-fixture"
TEST_FIXTURE_BUSINESS_CREATE_VALUE = "business_create"


def request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def business_service(request: Request) -> BusinessService:
    return BusinessService(
        settings=request.app.state.settings,
        repository=request.app.state.business_repository,
        user_repository=request.app.state.user_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
        idempotency_store=request.app.state.idempotency_store,
        storage=request.app.state.private_storage,
        marketplace_cache=getattr(request.app.state, "marketplace_cache", None),
    )


def legacy_onboarding_service(request: Request) -> LegacyBusinessOnboardingService:
    return LegacyBusinessOnboardingService(
        settings=request.app.state.settings,
        repository=request.app.state.business_repository,
        user_repository=request.app.state.user_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
        idempotency_store=request.app.state.idempotency_store,
        storage=request.app.state.private_storage,
    )


def require_test_fixture_business_endpoint(request: Request) -> None:
    if not (
        request.app.state.settings.app_env == "test"
        and request.headers.get(TEST_FIXTURE_BUSINESS_CREATE_HEADER) == TEST_FIXTURE_BUSINESS_CREATE_VALUE
    ):
        raise ApiError("BUSINESS_SELF_ONBOARDING_DISABLED", status_code=403)
