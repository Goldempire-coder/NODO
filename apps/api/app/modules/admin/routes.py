from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from pydantic import Field

from app.auth.dependencies import require_current_user
from app.core.errors import ApiError
from app.modules.admin.investigation_candidates import AdminInvestigationCandidatesService
from app.modules.admin.investigation_case_file import AdminInvestigationCaseFileService
from app.modules.admin.order_chat_evidence import AdminOrderChatEvidenceService
from app.modules.admin.policy import require_admin_mutation
from app.modules.admin.service import AdminService
from app.modules.users.admin_telegram_links import generate_admin_telegram_link_code, hash_admin_telegram_link_code
from app.modules.users.models import UserRecord
from app.shared.validation import StrictRequestModel

router = APIRouter(prefix="/admin", tags=["admin-console"])


class AdminReasonRequest(StrictRequestModel):
    reason: str = Field(default="", max_length=500)


class AdminEmergencyModeRequest(AdminReasonRequest):
    message: str | None = Field(default=None, max_length=280)


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def _service(request: Request) -> AdminService:
    return AdminService(
        settings=request.app.state.settings,
        repository=request.app.state.admin_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
        read_model_cache=request.app.state.admin_read_model_cache,
        idempotency_store=request.app.state.idempotency_store,
        auth_user_cache=request.app.state.auth_user_cache,
        emergency_mode_repository=request.app.state.emergency_mode_repository,
        job_repository=request.app.state.job_repository,
        observability_repository=getattr(request.app.state, "observability_repository", None),
    )


def _order_chat_evidence_service(request: Request) -> AdminOrderChatEvidenceService:
    return AdminOrderChatEvidenceService(
        settings=request.app.state.settings,
        order_repository=request.app.state.order_repository,
        chat_repository=request.app.state.chat_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
    )


def _investigation_case_file_service(request: Request) -> AdminInvestigationCaseFileService:
    return AdminInvestigationCaseFileService(
        settings=request.app.state.settings,
        repository=request.app.state.admin_case_file_repository,
        staff_repository=request.app.state.staff_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
    )


def _investigation_candidates_service(request: Request) -> AdminInvestigationCandidatesService:
    return AdminInvestigationCandidatesService(
        settings=request.app.state.settings,
        repository=request.app.state.admin_investigation_candidates_repository,
        staff_repository=request.app.state.staff_repository,
        audit_writer=request.app.state.audit_writer,
        rate_limiter=request.app.state.rate_limiter,
    )


@router.get("/dashboard")
def dashboard(request: Request, response: Response, user: UserRecord = Depends(require_current_user)) -> dict:
    response.headers["Cache-Control"] = "private, no-store"
    return {"data": _service(request).dashboard(user=user, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.post("/telegram-alerts/link-code")
def create_admin_telegram_alert_link_code(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    require_admin_mutation(user)
    rate_key = f"admin:telegram_alert_link_code:{user.id}"
    if not request.app.state.rate_limiter.allow(rate_key, max_attempts=5, window_seconds=600):
        raise ApiError("RATE_LIMITED", status_code=429)

    code = generate_admin_telegram_link_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    record = request.app.state.user_repository.create_admin_telegram_link_code(
        user_id=user.id,
        code_hash=hash_admin_telegram_link_code(code),
        expires_at=expires_at,
    )
    request.app.state.audit_writer.write(
        event_type="admin_telegram_alert_link_code_created",
        actor_user_id=user.id,
        actor_role=user.role,
        resource_type="admin_telegram_alerts",
        resource_id=user.id,
        request_id=_request_id(request),
        metadata_json={"link_code_id": record.id, "expires_at": expires_at.isoformat()},
    )
    return {
        "data": {
            "code": code,
            "expires_at": expires_at.isoformat(),
            "instructions": "Envia /start CODIGO al bot Admin de NODO desde el Telegram que recibira las alertas.",
        },
        "request_id": _request_id(request),
    }


@router.post("/telegram-alerts/test")
def send_admin_telegram_alert_test(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    require_admin_mutation(user)
    rate_key = f"admin:telegram_alert_test:{user.id}"
    if not request.app.state.rate_limiter.allow(rate_key, max_attempts=5, window_seconds=600):
        raise ApiError("RATE_LIMITED", status_code=429)

    data = request.app.state.admin_notification_service.admin_telegram_alert_test(
        user=user,
        request_id=_request_id(request),
    )
    sender_result = request.app.state.notification_sender_worker.run(
        batch_size=10,
        request_id=f"{_request_id(request)}:admin_telegram_alert_test",
    )
    return {
        "data": {
            **data,
            "sender_result": sender_result,
        },
        "request_id": _request_id(request),
    }


@router.get("/emergency-mode")
def emergency_mode(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).emergency_mode(user=user, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.post("/emergency-mode/activate")
def activate_emergency_mode(
    payload: AdminEmergencyModeRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).activate_emergency_mode(
            user=user,
            reason=payload.reason,
            message=payload.message,
            request_id=_request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": _request_id(request),
    }


@router.post("/emergency-mode/deactivate")
def deactivate_emergency_mode(
    payload: AdminReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return {
        "data": _service(request).deactivate_emergency_mode(
            user=user,
            reason=payload.reason,
            request_id=_request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": _request_id(request),
    }


@router.get("/metrics")
def metrics(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).metrics(user=user, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.get("/incident-console")
def incident_console(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).incident_console(user=user, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.get("/ux-friction")
def ux_friction(
    request: Request,
    window_hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=10, ge=1, le=25),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).ux_friction(user=user, window_hours=window_hours, limit=limit, request_id=_request_id(request)),
        "request_id": _request_id(request),
    }


@router.get("/investigation/search")
def operational_search(
    request: Request,
    response: Response,
    q: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=20, ge=1, le=20),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "data": _service(request).operational_search(user=user, query=q, limit=limit, request_id=_request_id(request)),
        "request_id": _request_id(request),
    }


@router.get("/investigation/case-file")
def investigation_case_file(
    request: Request,
    response: Response,
    anchor_type: str = Query(min_length=1, max_length=32),
    anchor_id: str = Query(min_length=1, max_length=64),
    section: str = Query(default="all", min_length=1, max_length=32),
    cursor: str | None = Query(default=None, max_length=2048),
    limit: int = Query(default=25, ge=1, le=50),
    include_archived: bool = Query(default=True),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "data": _investigation_case_file_service(request).get_case_file(
            user=user,
            anchor_type=anchor_type,
            anchor_id=anchor_id,
            section=section,
            cursor=cursor,
            limit=limit,
            include_archived=include_archived,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.get("/investigation/order-candidates")
def investigation_order_candidates(
    request: Request,
    response: Response,
    client_hint: str | None = Query(default=None, max_length=120),
    business_hint: str | None = Query(default=None, max_length=120),
    amount_min_usd: str | None = Query(default=None, max_length=40),
    amount_max_usd: str | None = Query(default=None, max_length=40),
    created_from: str | None = Query(default=None, max_length=64),
    created_to: str | None = Query(default=None, max_length=64),
    order_status: str | None = Query(default=None, max_length=32),
    support_status_group: str = Query(default="all", max_length=16),
    cursor: str | None = Query(default=None, max_length=2048),
    limit: int = Query(default=10, ge=1, le=25),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "data": _investigation_candidates_service(request).search(
            user=user,
            client_hint=client_hint,
            business_hint=business_hint,
            amount_min_usd=amount_min_usd,
            amount_max_usd=amount_max_usd,
            created_from=created_from,
            created_to=created_to,
            order_status=order_status,
            support_status_group=support_status_group,
            cursor=cursor,
            limit=limit,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.get("/businesses")
def list_businesses(
    request: Request,
    verification_status: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    business_id: str | None = Query(default=None),
    business_name: str | None = Query(default=None, max_length=160),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).list_businesses(
            user=user,
            verification_status=verification_status,
            risk_level=risk_level,
            business_id=business_id,
            business_name=business_name,
            cursor=cursor,
            limit=limit,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.get("/users")
def list_users(
    request: Request,
    phone: str | None = Query(default=None),
    telegram_id: str | None = Query(default=None),
    username: str | None = Query(default=None),
    role: str | None = Query(default=None),
    status: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).list_users(
            user=user,
            phone=phone,
            telegram_id=telegram_id,
            username=username,
            role=role,
            status=status,
            cursor=cursor,
            limit=limit,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.get("/users/{user_id}")
def user_detail(user_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).user_detail(user=user, target_user_id=user_id, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.post("/users/{user_id}/phone/reveal")
def reveal_user_phone(user_id: str, payload: AdminReasonRequest, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {
        "data": _service(request).reveal_user_phone(
            user=user,
            target_user_id=user_id,
            reason=payload.reason,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.get("/users/{user_id}/access-links")
def user_access_links(user_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).list_user_access_links(user=user, target_user_id=user_id, request_id=_request_id(request)), "request_id": _request_id(request)}


def _change_user_status(
    *,
    action: str,
    user_id: str,
    payload: AdminReasonRequest,
    request: Request,
    user: UserRecord,
    idempotency_key: str | None,
) -> dict:
    service = _service(request)
    method = {
        "suspend": service.suspend_user,
        "reactivate": service.reactivate_user,
        "block": service.block_user,
    }[action]
    return {
        "data": method(
            user=user,
            target_user_id=user_id,
            reason=payload.reason,
            request_id=_request_id(request),
            idempotency_key=idempotency_key,
        ),
        "request_id": _request_id(request),
    }


@router.post("/users/{user_id}/suspend")
def suspend_user(
    user_id: str,
    payload: AdminReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return _change_user_status(action="suspend", user_id=user_id, payload=payload, request=request, user=user, idempotency_key=idempotency_key)


@router.post("/users/{user_id}/reactivate")
def reactivate_user(
    user_id: str,
    payload: AdminReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return _change_user_status(action="reactivate", user_id=user_id, payload=payload, request=request, user=user, idempotency_key=idempotency_key)


@router.post("/users/{user_id}/block")
def block_user(
    user_id: str,
    payload: AdminReasonRequest,
    request: Request,
    user: UserRecord = Depends(require_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    return _change_user_status(action="block", user_id=user_id, payload=payload, request=request, user=user, idempotency_key=idempotency_key)


@router.get("/businesses/{business_id}/access-links")
def business_access_links(business_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).list_business_access_links(user=user, business_id=business_id, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.get("/businesses/{business_id}")
def business_detail(business_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).business_detail(user=user, business_id=business_id, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.get("/orders")
def list_orders(
    request: Request,
    status: str | None = Query(default=None),
    business_id: str | None = Query(default=None),
    remitter_user_id: str | None = Query(default=None),
    public_order_code: str | None = Query(default=None, max_length=32),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).list_orders(
            user=user,
            status=status,
            business_id=business_id,
            remitter_user_id=remitter_user_id,
            public_order_code=public_order_code,
            cursor=cursor,
            limit=limit,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.get("/orders/{order_id}")
def order_detail(order_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).order_detail(user=user, order_id=order_id, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.get("/orders/{order_id}/chat-evidence")
def order_chat_evidence(
    order_id: str,
    request: Request,
    response: Response,
    cursor: str | None = Query(default=None),
    direction: str | None = Query(default=None, pattern="^(older|newer)$"),
    highlight_message_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "data": _order_chat_evidence_service(request).list_evidence(
            user=user,
            order_id=order_id,
            cursor=cursor,
            direction=direction,
            limit=limit,
            highlight_message_id=highlight_message_id,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.get("/audit-logs")
def audit_logs(
    request: Request,
    event_type: str | None = Query(default=None),
    actor_user_id: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).audit_logs(
            user=user,
            event_type=event_type,
            actor_user_id=actor_user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            cursor=cursor,
            limit=limit,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }
