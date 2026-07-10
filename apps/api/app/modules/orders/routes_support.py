from __future__ import annotations

from fastapi import Request

from app.modules.orders.service import OrderService


def request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def order_service(request: Request) -> OrderService:
    return OrderService(
        settings=request.app.state.settings,
        repository=request.app.state.order_repository,
        ad_repository=request.app.state.ad_repository,
        business_repository=request.app.state.business_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
        idempotency_store=request.app.state.idempotency_store,
        storage=request.app.state.private_storage,
        marketplace_cache=request.app.state.marketplace_cache,
    )
