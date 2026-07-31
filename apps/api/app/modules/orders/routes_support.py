from __future__ import annotations

from fastapi import Request

from app.modules.notifications.order_notifications import OrderNotificationService
from app.modules.orders.service import OrderService
from app.shared.observability import get_correlation_id, get_operation_id, get_request_id


def request_id(request: Request) -> str:
    return get_request_id(request)


def order_service(request: Request) -> OrderService:
    notifications = OrderNotificationService(
        settings=request.app.state.settings,
        job_repository=request.app.state.job_repository,
        business_repository=request.app.state.business_repository,
        correlation_id=get_correlation_id(request),
        operation_id=get_operation_id(request),
    )
    return OrderService(
        settings=request.app.state.settings,
        repository=request.app.state.order_repository,
        ad_repository=request.app.state.ad_repository,
        business_repository=request.app.state.business_repository,
        capacity_repository=request.app.state.capacity_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
        idempotency_store=request.app.state.idempotency_store,
        chat_repository=request.app.state.chat_repository,
        storage=request.app.state.private_storage,
        marketplace_cache=request.app.state.marketplace_cache,
        notification_service=notifications,
        rating_repository=request.app.state.rating_repository,
    )
