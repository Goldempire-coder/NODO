from __future__ import annotations

from fastapi import Request

from app.modules.business_intake.policy import require_bot_secret
from app.modules.business_intake.service import BusinessIntakeService


def request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def service(request: Request) -> BusinessIntakeService:
    return BusinessIntakeService(
        settings=request.app.state.settings,
        repository=request.app.state.business_intake_repository,
        business_repository=request.app.state.business_repository,
        credit_repository=request.app.state.credit_repository,
        user_repository=request.app.state.user_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
        idempotency_store=request.app.state.idempotency_store,
        storage=request.app.state.private_storage,
        admin_notifications=getattr(request.app.state, "admin_notification_service", None),
    )


def require_business_intake_bot(request: Request, secret: str | None) -> None:
    require_bot_secret(
        provided_secret=secret,
        bot_token=request.app.state.settings.business_intake_bot_token,
    )
