from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.auth.dependencies import require_current_user
from app.modules.admin_notifications.service import AdminNotificationService
from app.modules.users.models import UserRecord

router = APIRouter(prefix="/admin/notifications", tags=["admin-notifications"])


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "request_id_unavailable")


def _service(request: Request) -> AdminNotificationService:
    return request.app.state.admin_notification_service


@router.get("")
def list_admin_notifications(
    request: Request,
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: UserRecord = Depends(require_current_user),
) -> dict:
    return {
        "data": _service(request).list_notifications(
            user=user,
            status=status,
            priority=priority,
            cursor=cursor,
            limit=limit,
            request_id=_request_id(request),
        ),
        "request_id": _request_id(request),
    }


@router.get("/unread-count")
def admin_notifications_unread_count(request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).unread_count(user=user, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.post("/{notification_id}/read")
def mark_admin_notification_read(notification_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).mark_read(user=user, notification_id=notification_id, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.post("/{notification_id}/dismiss")
def dismiss_admin_notification(notification_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).dismiss(user=user, notification_id=notification_id, request_id=_request_id(request)), "request_id": _request_id(request)}


@router.post("/{notification_id}/resolve")
def resolve_admin_notification(notification_id: str, request: Request, user: UserRecord = Depends(require_current_user)) -> dict:
    return {"data": _service(request).resolve(user=user, notification_id=notification_id, request_id=_request_id(request)), "request_id": _request_id(request)}
