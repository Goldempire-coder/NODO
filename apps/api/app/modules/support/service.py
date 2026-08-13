from __future__ import annotations

import hashlib
import re
from typing import Any
from uuid import UUID

from app.core.config import Settings
from app.core.errors import ApiError
from app.core.logging import get_logger
from app.modules.businesses.access_control import evaluate_business_access
from app.modules.businesses.models import BusinessRecord
from app.modules.ads.marketplace_cache import MARKETPLACE_CACHE_PREFIX
from app.modules.support.models import (
    ACTIVE_SUPPORT_STATUSES,
    MAX_SUPPORT_ATTACHMENT_SIZE_BYTES,
    SUPPORT_CATEGORIES,
    SUPPORT_MESSAGE_VISIBILITIES,
    SUPPORT_SCOPES,
    SUPPORT_STATUS_GROUPS,
    SUPPORT_STATUSES,
    STRUCTURED_OPERATION_REPORT,
    SupportTicketRecord,
    new_id,
    utc_now,
)
from app.modules.notifications.support_notifications import NoopSupportNotificationService
from app.modules.support.presenters import (
    event_public,
    file_asset_public,
    message_public,
    publication_hold_admin,
    ticket_summary,
)
from app.modules.support.schemas import (
    AdminSupportMessageCreateRequest,
    OperationReportCreateRequest,
    SupportEscalateRequest,
    SupportMessageCreateRequest,
    SupportReasonRequest,
    SupportTicketCreateRequest,
)
from app.modules.staff.service import require_staff_permission
from app.modules.users.models import UserRecord
from app.shared.photo_uploads import PHOTO_UPLOAD_ERROR_MESSAGE, ValidatedPhoto, validate_photo_upload


SUPPORT_DISCLAIMER = "NODO registra evidencia y estado; no recibe, retiene, transfiere ni garantiza fondos."
ADMIN_ROLES = {"admin", "super_admin", "support"}
logger = get_logger(__name__)

OPERATION_REPORT_CATEGORIES = {
    "order_help",
    "payment_report_help",
    "suspicious_activity",
    "other",
}
REPORTABLE_OPERATION_STATUSES = {
    "payment_confirmed",
    "delivered",
    "completed",
    "payment_rejected",
    "disputed",
    "cancelled",
}


def _require_uuid(value: str | None, code: str = "NOT_FOUND") -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(value))
    except (TypeError, ValueError) as exc:
        raise ApiError(code, status_code=404 if code.endswith("NOT_FOUND") else 400) from exc


def _sanitize_text(value: str, max_length: int) -> str:
    clean = re.sub(r"<[^>]*>", "", value).strip()
    return clean[:max_length]


def _attachment_payload(file) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    return file_asset_public(file)


def _support_statuses(*, status: str | None, status_group: str | None) -> set[str] | None:
    if status and status_group:
        raise ApiError("SUPPORT_TICKET_STATUS_FILTER_CONFLICT", status_code=400)
    if status_group:
        statuses = SUPPORT_STATUS_GROUPS.get(status_group)
        if statuses is None:
            raise ApiError("SUPPORT_TICKET_STATUS_GROUP_INVALID", status_code=400)
        return set(statuses)
    if status:
        if status not in SUPPORT_STATUSES:
            raise ApiError("SUPPORT_TICKET_STATUS_INVALID", status_code=400)
        return {status}
    return None


def _attachment_download_filename(*, ticket: SupportTicketRecord, file) -> str:  # type: ignore[no-untyped-def]
    extension = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "application/pdf": "pdf",
    }.get(file.mime_type, "bin")
    return f"nodo-support-{ticket.id[:8]}-{file.id[:8]}.{extension}"


class SupportService:
    def __init__(
        self,
        *,
        settings: Settings,
        repository,
        order_repository,
        business_repository,
        ad_repository,
        credit_repository,
        dispute_repository,
        user_repository,
        staff_repository,
        audit_writer,
        rate_limiter,
        idempotency_store,
        storage,
        admin_notifications=None,
        notification_service=None,
        marketplace_cache=None,
    ) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._orders = order_repository
        self._businesses = business_repository
        self._ads = ad_repository
        self._credits = credit_repository
        self._disputes = dispute_repository
        self._users = user_repository
        self._staff = staff_repository
        self._audit = audit_writer
        self._rate = rate_limiter
        self._idempotency = idempotency_store
        self._storage = storage
        self._admin_notifications = admin_notifications
        self._notifications = notification_service or NoopSupportNotificationService()
        self._marketplace_cache = marketplace_cache

    def _rate_limit(self, action: str, user: UserRecord, ticket_id: str | None = None) -> None:
        key = f"support:{action}:{user.id}:{ticket_id or 'global'}"
        if not self._rate.allow(
            key,
            max_attempts=self._settings.business_rate_limit_max_attempts,
            window_seconds=self._settings.business_rate_limit_window_seconds,
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def _require_admin_actor(self, user: UserRecord) -> None:
        if user.role not in ADMIN_ROLES or user.status != "active":
            raise ApiError("FORBIDDEN", status_code=403)

    def _require_support_permission(self, user: UserRecord, permission: str, ticket: SupportTicketRecord | None = None) -> None:
        if user.role in {"admin", "super_admin"}:
            self._require_admin_actor(user)
            return
        self._require_admin_actor(user)
        require_staff_permission(self._staff, user=user, permission=permission, ticket=ticket)

    def _active_business_for_user(self, user: UserRecord) -> BusinessRecord:
        business = self._businesses.get_active_business_for_owner(user.id)
        business, _link = evaluate_business_access(user=user, business=business, business_repository=self._businesses)
        return business

    def _ticket_visible_to_user(self, *, ticket: SupportTicketRecord, user: UserRecord) -> bool:
        if user.role in ADMIN_ROLES:
            return user.status == "active"
        if user.role == "business_owner" and ticket.business_id:
            if ticket.report_kind == STRUCTURED_OPERATION_REPORT:
                return False
            try:
                business = self._active_business_for_user(user)
            except ApiError:
                return False
            return business.id == ticket.business_id
        if ticket.requester_user_id == user.id:
            return True
        if user.role == "remitter" and ticket.order_id:
            order = self._orders.get_by_id(ticket.order_id)
            return order is not None and order.remitter_user_id == user.id
        return False

    def _support_business_names(self, tickets: list[SupportTicketRecord]) -> dict[str, str]:
        business_ids = {ticket.business_id for ticket in tickets if ticket.business_id}
        if not business_ids:
            return {}
        return {
            business_id: business.business_name
            for business_id, business in self._businesses.get_businesses_by_ids(business_ids).items()
        }

    def _ticket_summary_payload(
        self,
        ticket: SupportTicketRecord,
        *,
        business_names: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        payload = ticket_summary(ticket)
        if ticket.business_id is None:
            payload["business_name"] = None
            return payload
        if business_names is not None:
            payload["business_name"] = business_names.get(ticket.business_id)
            return payload
        business = self._businesses.get_business(ticket.business_id)
        payload["business_name"] = business.business_name if business else None
        return payload

    def _validate_ticket_payload(self, *, user: UserRecord, payload: SupportTicketCreateRequest, surface: str | None) -> dict[str, str | None]:
        if payload.scope not in SUPPORT_SCOPES or payload.scope == "admin_internal":
            raise ApiError("SUPPORT_SCOPE_INVALID", status_code=400)
        if payload.category not in SUPPORT_CATEGORIES:
            raise ApiError("SUPPORT_CATEGORY_INVALID", status_code=400)
        if payload.attachment_ids:
            raise ApiError("SUPPORT_ATTACHMENT_INVALID", status_code=400)
        fields: dict[str, str | None] = {
            "business_id": None,
            "order_id": None,
            "ad_id": None,
            "credit_purchase_id": None,
            "dispute_id": None,
        }
        if payload.scope == "client_general":
            if user.role != "remitter":
                raise ApiError("FORBIDDEN", status_code=403)
        elif payload.scope == "client_order":
            if user.role != "remitter":
                raise ApiError("FORBIDDEN", status_code=403)
            order_id = _require_uuid(payload.order_id, "ORDER_NOT_FOUND")
            order = self._orders.get_by_id(order_id)
            if order is None or order.remitter_user_id != user.id:
                raise ApiError("ORDER_NOT_OWNED", status_code=404)
            fields["order_id"] = order.id
            fields["business_id"] = order.business_id
        elif payload.scope.startswith("business_"):
            business = self._active_business_for_user(user)
            fields["business_id"] = business.id
            if payload.scope == "business_order":
                order_id = _require_uuid(payload.order_id, "ORDER_NOT_FOUND")
                order = self._orders.get_by_id(order_id)
                if order is None or order.business_id != business.id:
                    raise ApiError("ORDER_NOT_OWNED", status_code=404)
                fields["order_id"] = order.id
            elif payload.scope == "business_ad":
                ad_id = _require_uuid(payload.ad_id, "AD_NOT_FOUND")
                ad = self._ads.get_ad(ad_id)
                if ad is None or ad.business_id != business.id:
                    raise ApiError("AD_NOT_FOUND", status_code=404)
                fields["ad_id"] = ad.id
            elif payload.scope == "business_credit":
                purchase_id = _require_uuid(payload.credit_purchase_id, "CREDIT_PURCHASE_NOT_FOUND")
                purchase = self._credits.get_purchase(purchase_id)
                if purchase is None or purchase.business_id != business.id:
                    raise ApiError("CREDIT_PURCHASE_NOT_FOUND", status_code=404)
                fields["credit_purchase_id"] = purchase.id
        else:
            raise ApiError("SUPPORT_SCOPE_INVALID", status_code=400)
        fields["requester_surface"] = surface or ("business_mini_app" if user.role == "business_owner" else "client_mini_app")
        return fields

    def _notify_admin_support_ticket_created(self, *, ticket: SupportTicketRecord, request_id: str) -> None:
        if self._admin_notifications is None:
            return
        try:
            if ticket.requester_role == "business_owner":
                self._admin_notifications.business_support_ticket_created(ticket=ticket, request_id=request_id)
            elif ticket.requester_role == "remitter":
                self._admin_notifications.client_support_ticket_created(ticket=ticket, request_id=request_id)
        except Exception as exc:
            logger.warning(
                "support_ticket_admin_notification_failed",
                extra={
                    "event": "support_ticket_admin_notification_failed",
                    "ticket_id": ticket.id,
                    "requester_role": ticket.requester_role,
                    "requester_surface": ticket.requester_surface,
                    "scope": ticket.scope,
                    "error_code": type(exc).__name__,
                    "request_id": request_id,
                },
            )

    def _notify_admin_support_message_created(self, *, ticket: SupportTicketRecord, message, request_id: str) -> None:  # type: ignore[no-untyped-def]
        if self._admin_notifications is None:
            return
        try:
            if message.sender_role == "business_owner":
                self._admin_notifications.business_support_message_created(ticket=ticket, message=message, request_id=request_id)
            elif message.sender_role == "remitter":
                self._admin_notifications.client_support_message_created(ticket=ticket, message=message, request_id=request_id)
        except Exception as exc:
            logger.warning(
                "support_message_admin_notification_failed",
                extra={
                    "event": "support_message_admin_notification_failed",
                    "ticket_id": ticket.id,
                    "message_id": message.id,
                    "sender_role": message.sender_role,
                    "scope": ticket.scope,
                    "error_code": type(exc).__name__,
                    "request_id": request_id,
                },
            )

    def _invalidate_marketplace(self) -> None:
        if self._marketplace_cache is not None:
            self._marketplace_cache.clear_prefix(MARKETPLACE_CACHE_PREFIX)

    def _detail_payload(
        self,
        *,
        ticket: SupportTicketRecord,
        user: UserRecord,
        admin: bool = False,
        messages_cursor: str | None = None,
        messages_limit: int = 25,
        events_cursor: str | None = None,
        events_limit: int = 25,
    ) -> dict[str, Any]:
        messages, messages_next_cursor = self._repository.list_messages_page(
            ticket_id=ticket.id,
            cursor=messages_cursor,
            limit=messages_limit,
            include_internal=admin,
            viewer_user_id=user.id,
        )
        resources = [("support_ticket", ticket.id)] + [("support_message", message.id) for message in messages]
        attachments = self._repository.list_files_for_resources(resources=resources)
        events, events_next_cursor = (
            self._repository.list_events_page(ticket_id=ticket.id, cursor=events_cursor, limit=events_limit)
            if admin
            else ([], None)
        )
        payload = {
            **self._ticket_summary_payload(ticket),
            "attachments": [_attachment_payload(file) for file in attachments.get(("support_ticket", ticket.id), [])],
            "messages": [
                message_public(message, attachments.get(("support_message", message.id), []))
                for message in messages
            ],
            "messages_next_cursor": messages_next_cursor,
            "events": [event_public(event) for event in events],
            "events_next_cursor": events_next_cursor,
            "disclaimer": SUPPORT_DISCLAIMER,
        }
        if admin and ticket.report_kind == STRUCTURED_OPERATION_REPORT:
            hold = self._repository.get_publication_hold_for_ticket(ticket.id)
            payload["publication_hold"] = publication_hold_admin(hold) if hold else None
        return payload

    def _operation_report_client_payload(
        self,
        *,
        ticket: SupportTicketRecord,
        user: UserRecord,
    ) -> dict[str, Any]:
        payload = self._detail_payload(ticket=ticket, user=user)
        payload.pop("business_id", None)
        payload.pop("business_name", None)
        return payload

    def create_ticket(self, *, user: UserRecord, payload: SupportTicketCreateRequest, surface: str | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        self._rate_limit("create", user)
        fields = self._validate_ticket_payload(user=user, payload=payload, surface=surface)
        subject = _sanitize_text(payload.subject, 140)
        message_body = _sanitize_text(payload.message, 2000)
        if not subject or not message_body:
            raise ApiError("SUPPORT_MESSAGE_REQUIRED", status_code=400)
        request_payload = {
            "scope": payload.scope,
            "category": payload.category,
            "subject": subject,
            "message": message_body,
            **fields,
        }

        def compute() -> dict[str, Any]:
            ticket_fields = dict(
                requester_user_id=user.id,
                requester_role=user.role,
                requester_surface=fields["requester_surface"],
                scope=payload.scope,
                category=payload.category,
                status="open",
                priority="normal",
                subject=subject,
                report_kind=None,
                business_id=fields["business_id"],
                order_id=fields["order_id"],
                ad_id=fields["ad_id"],
                credit_purchase_id=fields["credit_purchase_id"],
                dispute_id=None,
                assigned_support_user_id=None,
                last_message_at=None,
                escalated_at=None,
                resolved_at=None,
                closed_at=None,
            )
            ticket = self._repository.create_ticket(**ticket_fields)
            self._repository.create_message(ticket_id=ticket.id, sender_user_id=user.id, sender_role=user.role, body=message_body, visibility="participants")
            self._repository.create_event(ticket_id=ticket.id, actor_user_id=user.id, actor_role=user.role, event_type="support_ticket_created", to_status="open", metadata_json={"scope": payload.scope, "category": payload.category})
            self._audit.write(event_type="support_ticket_created", actor_user_id=user.id, actor_role=user.role, resource_type="support_ticket", resource_id=ticket.id, request_id=request_id, metadata_json={"scope": payload.scope, "category": payload.category})
            self._notify_admin_support_ticket_created(ticket=ticket, request_id=request_id)
            return self._detail_payload(ticket=ticket, user=user)

        return self._idempotency.replay_or_store(f"support:ticket:{user.id}:{idempotency_key}", payload=request_payload, compute=compute)

    def create_operation_report(
        self,
        *,
        user: UserRecord,
        order_id: str,
        payload: OperationReportCreateRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        if user.role != "remitter" or user.status != "active":
            raise ApiError("FORBIDDEN", status_code=403)
        clean_order_id = _require_uuid(order_id, "ORDER_NOT_FOUND")
        order = self._orders.get_by_id(clean_order_id)
        if order is None or order.remitter_user_id != user.id:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        if order.status not in REPORTABLE_OPERATION_STATUSES:
            raise ApiError("OPERATION_REPORT_NOT_ALLOWED", status_code=409)
        if payload.category not in OPERATION_REPORT_CATEGORIES:
            raise ApiError("SUPPORT_CATEGORY_INVALID", status_code=400)
        message_body = _sanitize_text(payload.message, 1000)
        if len(message_body) < 3:
            raise ApiError("SUPPORT_MESSAGE_REQUIRED", status_code=400)
        self._rate_limit("operation_report", user, order.id)
        request_payload = {
            "order_id": order.id,
            "category": payload.category,
            "message": message_body,
        }

        def compute() -> dict[str, Any]:
            current_order = self._orders.get_by_id(order.id)
            if current_order is None or current_order.remitter_user_id != user.id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if current_order.status not in REPORTABLE_OPERATION_STATUSES:
                raise ApiError("OPERATION_REPORT_NOT_ALLOWED", status_code=409)
            if self._repository.get_active_operation_report_for_order(current_order.id) is not None:
                raise ApiError("OPERATION_REPORT_DUPLICATE", status_code=409)
            ticket_fields = dict(
                requester_user_id=user.id,
                requester_role=user.role,
                requester_surface="client_mini_app",
                scope="client_order",
                category=payload.category,
                status="open",
                priority="normal",
                subject=f"Reporte de operacion {current_order.public_order_code}",
                report_kind=STRUCTURED_OPERATION_REPORT,
                business_id=current_order.business_id,
                order_id=current_order.id,
                ad_id=None,
                credit_purchase_id=None,
                dispute_id=None,
                assigned_support_user_id=None,
                last_message_at=None,
                escalated_at=None,
                resolved_at=None,
                closed_at=None,
            )
            event_metadata = {
                "scope": "client_order",
                "category": payload.category,
                "report_kind": STRUCTURED_OPERATION_REPORT,
            }
            business = self._businesses.get_business(current_order.business_id)
            if business is None:
                raise ApiError("BUSINESS_NOT_FOUND", status_code=404)
            ticket, hold = self._repository.create_operation_report(
                ticket_fields=ticket_fields,
                message_body=message_body,
                event_metadata=event_metadata,
                publication_paused_until=business.ad_publication_paused_until,
            )
            self._audit.write(
                event_type="structured_operation_report_created",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="support_ticket",
                resource_id=ticket.id,
                request_id=request_id,
                metadata_json={
                    "order_id": current_order.id,
                    "business_id": current_order.business_id,
                    "category": payload.category,
                },
            )
            if hold is not None:
                self._audit.write(
                    event_type="business_publication_hold_started",
                    actor_user_id=user.id,
                    actor_role=user.role,
                    resource_type="business_publication_hold",
                    resource_id=hold.id,
                    request_id=request_id,
                    metadata_json={
                        "business_id": hold.business_id,
                        "order_id": hold.order_id,
                        "support_ticket_id": hold.support_ticket_id,
                    },
                )
                self._invalidate_marketplace()
            self._notify_admin_support_ticket_created(ticket=ticket, request_id=request_id)
            return {
                "ticket": self._operation_report_client_payload(
                    ticket=ticket,
                    user=user,
                )
            }

        return self._idempotency.replay_or_store(
            f"support:operation_report:{user.id}:{order.id}:{idempotency_key}",
            payload=request_payload,
            compute=compute,
        )

    def release_publication_hold(
        self,
        *,
        user: UserRecord,
        hold_id: str,
        payload: SupportReasonRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        if user.role not in {"admin", "super_admin"} or user.status != "active":
            raise ApiError("FORBIDDEN", status_code=403)
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        clean_hold_id = _require_uuid(
            hold_id,
            "BUSINESS_PUBLICATION_HOLD_NOT_FOUND",
        )
        reason = _sanitize_text(payload.reason, 500)
        if not reason:
            raise ApiError("REASON_REQUIRED", status_code=400)
        request_payload = {"hold_id": clean_hold_id, "reason": reason}

        def compute() -> dict[str, Any]:
            hold = self._repository.release_publication_hold(
                hold_id=clean_hold_id,
                released_by=user.id,
                release_reason=reason,
            )
            self._audit.write(
                event_type="business_publication_hold_released",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="business_publication_hold",
                resource_id=hold.id,
                request_id=request_id,
                metadata_json={
                    "business_id": hold.business_id,
                    "order_id": hold.order_id,
                    "support_ticket_id": hold.support_ticket_id,
                    "reason": reason,
                },
            )
            self._invalidate_marketplace()
            return {"hold": publication_hold_admin(hold)}

        return self._idempotency.replay_or_store(
            f"admin:business_publication_hold:release:{user.id}:{clean_hold_id}:{idempotency_key}",
            payload=request_payload,
            compute=compute,
        )

    def list_user_tickets(self, *, user: UserRecord, status: str | None, status_group: str | None, scope: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        self._rate_limit("list", user)
        statuses = _support_statuses(status=status, status_group=status_group)
        if scope and scope not in SUPPORT_SCOPES:
            raise ApiError("SUPPORT_SCOPE_INVALID", status_code=400)
        business_id = None
        requester_user_id = user.id
        if user.role == "business_owner":
            business = self._active_business_for_user(user)
            business_id = business.id
            requester_user_id = None
        items, next_cursor = self._repository.list_tickets(
            requester_user_id=requester_user_id,
            business_id=business_id,
            statuses=statuses,
            scope=scope,
            category=None,
            priority=None,
            assigned_support_user_id=None,
            cursor=cursor,
            limit=limit,
        )
        visible = [ticket for ticket in items if self._ticket_visible_to_user(ticket=ticket, user=user)]
        business_names = self._support_business_names(visible)
        return {"items": [self._ticket_summary_payload(ticket, business_names=business_names) for ticket in visible], "next_cursor": next_cursor}

    def user_ticket_detail(
        self,
        *,
        user: UserRecord,
        ticket_id: str,
        messages_cursor: str | None,
        messages_limit: int,
        request_id: str,
    ) -> dict[str, Any]:
        ticket = self._require_ticket(ticket_id)
        self._rate_limit("detail", user, ticket.id)
        if not self._ticket_visible_to_user(ticket=ticket, user=user) or user.role in ADMIN_ROLES:
            raise ApiError("SUPPORT_TICKET_NOT_FOUND", status_code=404)
        return self._detail_payload(
            ticket=ticket,
            user=user,
            messages_cursor=messages_cursor,
            messages_limit=messages_limit,
        )

    def create_user_message(self, *, user: UserRecord, ticket_id: str, payload: SupportMessageCreateRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        if payload.attachment_ids:
            raise ApiError("SUPPORT_ATTACHMENT_INVALID", status_code=400)
        ticket = self._require_ticket(ticket_id)
        if not self._ticket_visible_to_user(ticket=ticket, user=user) or user.role in ADMIN_ROLES:
            raise ApiError("SUPPORT_TICKET_NOT_FOUND", status_code=404)
        return self._create_message(user=user, ticket=ticket, body=payload.body, visibility="participants", request_id=request_id, idempotency_key=idempotency_key, admin=False)

    def close_user_ticket(self, *, user: UserRecord, ticket_id: str, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        ticket = self._require_ticket(ticket_id)
        if (
            ticket.requester_user_id != user.id
            or not self._ticket_visible_to_user(ticket=ticket, user=user)
            or user.role in ADMIN_ROLES
        ):
            raise ApiError("SUPPORT_TICKET_NOT_FOUND", status_code=404)
        self._rate_limit("close", user, ticket.id)

        def compute() -> dict[str, Any]:
            current = self._require_ticket(ticket.id)
            if current.status not in ACTIVE_SUPPORT_STATUSES:
                raise ApiError("SUPPORT_TICKET_STATUS_INVALID", status_code=400)
            updated = self._repository.update_ticket(current, status="closed", closed_at=utc_now())
            reason = "requester_closed_by_mistake"
            self._repository.create_event(
                ticket_id=current.id,
                actor_user_id=user.id,
                actor_role=user.role,
                event_type="support_ticket_closed",
                from_status=current.status,
                to_status="closed",
                reason=reason,
                metadata_json={"closed_by": "requester"},
            )
            self._audit.write(
                event_type="support_ticket_closed",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="support_ticket",
                resource_id=current.id,
                request_id=request_id,
                metadata_json={"from_status": current.status, "to_status": "closed", "closed_by": "requester"},
            )
            return self._detail_payload(ticket=updated, user=user)

        return self._idempotency.replay_or_store(
            f"support:close-requester:{user.id}:{ticket.id}:{idempotency_key}",
            payload={"ticket_id": ticket.id, "action": "close_by_requester"},
            compute=compute,
        )

    def list_admin_tickets(self, *, user: UserRecord, status: str | None, status_group: str | None, scope: str | None, category: str | None, priority: str | None, assigned_support_user_id: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        self._require_support_permission(user, "view_support_queue")
        self._rate_limit("admin_list", user)
        statuses = _support_statuses(status=status, status_group=status_group)
        items, next_cursor = self._repository.list_tickets(
            requester_user_id=None,
            business_id=None,
            statuses=statuses,
            scope=scope,
            category=category,
            priority=priority,
            assigned_support_user_id=assigned_support_user_id,
            cursor=cursor,
            limit=limit,
        )
        business_names = self._support_business_names(items)
        return {"items": [self._ticket_summary_payload(ticket, business_names=business_names) for ticket in items], "next_cursor": next_cursor}

    def admin_ticket_detail(
        self,
        *,
        user: UserRecord,
        ticket_id: str,
        messages_cursor: str | None,
        messages_limit: int,
        events_cursor: str | None,
        events_limit: int,
        request_id: str,
    ) -> dict[str, Any]:
        ticket = self._require_ticket(ticket_id)
        if user.role == "support" and ticket.assigned_support_user_id == user.id:
            self._require_support_permission(user, "view_assigned_support_tickets", ticket)
        else:
            self._require_support_permission(user, "view_support_queue", ticket)
        self._rate_limit("admin_detail", user, ticket.id)
        return self._detail_payload(
            ticket=ticket,
            user=user,
            admin=True,
            messages_cursor=messages_cursor,
            messages_limit=messages_limit,
            events_cursor=events_cursor,
            events_limit=events_limit,
        )

    def create_admin_message(self, *, user: UserRecord, ticket_id: str, payload: AdminSupportMessageCreateRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        if payload.attachment_ids:
            raise ApiError("SUPPORT_ATTACHMENT_INVALID", status_code=400)
        if payload.visibility not in SUPPORT_MESSAGE_VISIBILITIES:
            raise ApiError("VALIDATION_ERROR", status_code=422)
        ticket = self._require_ticket(ticket_id)
        self._require_support_permission(user, "reply_support_ticket", ticket)
        return self._create_message(user=user, ticket=ticket, body=payload.body, visibility=payload.visibility, request_id=request_id, idempotency_key=idempotency_key, admin=True)

    def assign_ticket(self, *, user: UserRecord, ticket_id: str, assigned_support_user_id: str, reason: str, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        ticket = self._require_ticket(ticket_id)
        self._require_support_permission(user, "assign_support_ticket", ticket)
        assignee = self._users.get_user_by_id(_require_uuid(assigned_support_user_id, "USER_NOT_FOUND"))
        if assignee is None or assignee.role not in ADMIN_ROLES or assignee.status != "active":
            raise ApiError("SUPPORT_ASSIGNEE_INVALID", status_code=400)
        if assignee.role == "support" and (self._staff is None or self._staff.get_active_profile_for_user(assignee.id) is None):
            raise ApiError("SUPPORT_ASSIGNEE_INVALID", status_code=400)
        reason = _sanitize_text(reason, 500)
        if not reason:
            raise ApiError("ADMIN_REASON_REQUIRED", status_code=400)

        def compute() -> dict[str, Any]:
            current = self._require_ticket(ticket.id)
            if current.status not in ACTIVE_SUPPORT_STATUSES:
                raise ApiError("SUPPORT_TICKET_STATUS_INVALID", status_code=400)
            updated = self._repository.update_ticket(current, assigned_support_user_id=assignee.id)
            self._repository.create_event(ticket_id=current.id, actor_user_id=user.id, actor_role=user.role, event_type="support_ticket_assigned", reason=reason, metadata_json={"assigned_support_user_id": assignee.id})
            self._audit.write(event_type="support_ticket_assigned", actor_user_id=user.id, actor_role=user.role, resource_type="support_ticket", resource_id=current.id, request_id=request_id, metadata_json={"assigned_support_user_id": assignee.id})
            return self._detail_payload(ticket=updated, user=user, admin=True)

        return self._idempotency.replay_or_store(f"support:assign:{user.id}:{ticket.id}:{idempotency_key}", payload={"assigned_support_user_id": assignee.id, "reason": reason}, compute=compute)

    def escalate_ticket(self, *, user: UserRecord, ticket_id: str, payload: SupportEscalateRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._status_action(user=user, ticket_id=ticket_id, action="escalate", target_status="escalated", reason=payload.reason, request_id=request_id, idempotency_key=idempotency_key, extra={"existing_dispute_id": payload.existing_dispute_id})

    def resolve_ticket(self, *, user: UserRecord, ticket_id: str, reason: str, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._status_action(user=user, ticket_id=ticket_id, action="resolve", target_status="resolved", reason=reason, request_id=request_id, idempotency_key=idempotency_key, extra={})

    def close_ticket(self, *, user: UserRecord, ticket_id: str, reason: str, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._status_action(user=user, ticket_id=ticket_id, action="close", target_status="closed", reason=reason, request_id=request_id, idempotency_key=idempotency_key, extra={})

    def upload_attachment(self, *, user: UserRecord, ticket_id: str, file_name: str, mime_type: str, content: bytes, request_id: str, idempotency_key: str | None, admin: bool = False) -> dict[str, Any]:
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        if self._storage is None:
            raise ApiError("STORAGE_UNAVAILABLE", status_code=503)
        ticket = self._require_ticket(ticket_id)
        if admin:
            self._require_admin_actor(user)
        elif not self._ticket_visible_to_user(ticket=ticket, user=user) or user.role in ADMIN_ROLES:
            raise ApiError("SUPPORT_TICKET_NOT_FOUND", status_code=404)
        photo = self._validate_upload(user=user, ticket=ticket, mime_type=mime_type, content=content)
        file_name = photo.storage_file_name
        mime_type = photo.mime_type
        payload = {"ticket_id": ticket.id, "file_name": file_name, "mime_type": mime_type, "size_bytes": len(content), "content_sha256": hashlib.sha256(content).hexdigest()}

        def compute() -> dict[str, Any]:
            current = self._require_ticket(ticket.id)
            if current.status not in ACTIVE_SUPPORT_STATUSES:
                raise ApiError("SUPPORT_TICKET_STATUS_INVALID", status_code=400)
            file_id = new_id()
            stored = self._storage.store_support_attachment(ticket_id=current.id, file_id=file_id, file_name=file_name, content=content)
            message = self._repository.create_message(ticket_id=current.id, sender_user_id=user.id, sender_role=user.role, body="Adjunto enviado.", visibility="participants")
            file = self._repository.create_file_asset(file_id=file_id, owner_user_id=user.id, resource_type="support_message", resource_id=message.id, storage_path=stored.storage_path, mime_type=mime_type, size_bytes=stored.size_bytes)
            target_status = current.status
            if current.status != "escalated":
                target_status = "waiting_user" if admin else "waiting_support"
            if target_status != current.status:
                self._repository.update_ticket(current, status=target_status)
            self._repository.create_event(ticket_id=current.id, actor_user_id=user.id, actor_role=user.role, event_type="support_attachment_uploaded", metadata_json={"file_asset_id": file.id, "message_id": message.id, "mime_type": mime_type, "size_bytes": stored.size_bytes})
            self._repository.create_event(ticket_id=current.id, actor_user_id=user.id, actor_role=user.role, event_type="support_message_created", metadata_json={"visibility": "participants", "has_attachment": True})
            self._audit.write(event_type="support_attachment_uploaded", actor_user_id=user.id, actor_role=user.role, resource_type="support_ticket", resource_id=current.id, request_id=request_id, metadata_json={"file_asset_id": file.id, "message_id": message.id, "mime_type": mime_type, "size_bytes": stored.size_bytes})
            self._audit.write(event_type="support_message_created", actor_user_id=user.id, actor_role=user.role, resource_type="support_ticket", resource_id=current.id, request_id=request_id, metadata_json={"visibility": "participants", "has_attachment": True})
            current_ticket = self._repository.get_ticket(current.id) or current
            if not admin:
                self._notify_admin_support_message_created(ticket=current_ticket, message=message, request_id=request_id)
            else:
                self._notifications.message_created_participant(
                    ticket=current_ticket,
                    message=message,
                    request_id=request_id,
                )
            return {
                "attachment": file_asset_public(file),
                "message": message_public(message, [file]),
                "ticket": self._ticket_summary_payload(current_ticket),
                "disclaimer": SUPPORT_DISCLAIMER,
            }

        return self._idempotency.replay_or_store(f"support:attachment:{user.id}:{ticket.id}:{idempotency_key}", payload=payload, compute=compute)

    def attachment_view_url(self, *, user: UserRecord, ticket_id: str, file_id: str, reason: str, request_id: str) -> dict[str, Any]:
        if self._storage is None:
            raise ApiError("STORAGE_UNAVAILABLE", status_code=503)
        ticket = self._require_ticket(ticket_id)
        self._require_support_permission(user, "view_support_attachment", ticket)
        reason = _sanitize_text(reason, 500)
        if not reason:
            raise ApiError("ADMIN_REASON_REQUIRED", status_code=400)
        file = self._repository.get_ticket_file_asset(
            ticket_id=ticket.id,
            file_id=_require_uuid(file_id, "SUPPORT_ATTACHMENT_NOT_FOUND"),
        )
        if file is None:
            raise ApiError("SUPPORT_ATTACHMENT_ACCESS_DENIED", status_code=403)
        url = self._storage.signed_view_url(storage_path=file.storage_path, expires_in=min(self._settings.storage_signed_url_ttl_seconds, 300))
        self._repository.create_event(ticket_id=ticket.id, actor_user_id=user.id, actor_role=user.role, event_type="support_attachment_viewed", reason=reason, metadata_json={"file_asset_id": file.id})
        self._audit.write(event_type="support_attachment_viewed", actor_user_id=user.id, actor_role=user.role, resource_type="support_ticket", resource_id=ticket.id, request_id=request_id, metadata_json={"file_asset_id": file.id})
        return {
            "url": url,
            "expires_in_seconds": min(self._settings.storage_signed_url_ttl_seconds, 300),
            "download_filename": _attachment_download_filename(ticket=ticket, file=file),
        }

    def _require_ticket(self, ticket_id: str) -> SupportTicketRecord:
        ticket = self._repository.get_ticket(_require_uuid(ticket_id, "SUPPORT_TICKET_NOT_FOUND"))
        if ticket is None:
            raise ApiError("SUPPORT_TICKET_NOT_FOUND", status_code=404)
        return ticket

    def _create_message(self, *, user: UserRecord, ticket: SupportTicketRecord, body: str, visibility: str, request_id: str, idempotency_key: str | None, admin: bool) -> dict[str, Any]:
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        if ticket.status not in ACTIVE_SUPPORT_STATUSES:
            raise ApiError("SUPPORT_TICKET_STATUS_INVALID", status_code=400)
        self._rate_limit("message", user, ticket.id)
        body = _sanitize_text(body, 2000)
        if not body:
            raise ApiError("SUPPORT_MESSAGE_REQUIRED", status_code=400)

        def compute() -> dict[str, Any]:
            current = self._require_ticket(ticket.id)
            if current.status not in ACTIVE_SUPPORT_STATUSES:
                raise ApiError("SUPPORT_TICKET_STATUS_INVALID", status_code=400)
            message = self._repository.create_message(ticket_id=current.id, sender_user_id=user.id, sender_role=user.role, body=body, visibility=visibility)
            target_status = current.status
            if visibility == "participants" and current.status != "escalated":
                target_status = "waiting_user" if admin else "waiting_support"
            if target_status != current.status:
                self._repository.update_ticket(current, status=target_status)
            self._repository.create_event(ticket_id=current.id, actor_user_id=user.id, actor_role=user.role, event_type="support_message_created", metadata_json={"visibility": visibility})
            self._audit.write(event_type="support_message_created", actor_user_id=user.id, actor_role=user.role, resource_type="support_ticket", resource_id=current.id, request_id=request_id, metadata_json={"visibility": visibility})
            current_ticket = self._repository.get_ticket(current.id) or current
            if not admin and visibility == "participants":
                self._notify_admin_support_message_created(ticket=current_ticket, message=message, request_id=request_id)
            elif admin and visibility == "participants":
                self._notifications.message_created_participant(
                    ticket=current_ticket,
                    message=message,
                    request_id=request_id,
                )
            return {"message": message_public(message), "ticket": self._ticket_summary_payload(current_ticket), "disclaimer": SUPPORT_DISCLAIMER}

        return self._idempotency.replay_or_store(f"support:message:{user.id}:{ticket.id}:{idempotency_key}", payload={"body": body, "visibility": visibility}, compute=compute)

    def _status_action(self, *, user: UserRecord, ticket_id: str, action: str, target_status: str, reason: str, request_id: str, idempotency_key: str | None, extra: dict[str, Any]) -> dict[str, Any]:
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        ticket = self._require_ticket(ticket_id)
        permission = {
            "escalate": "escalate_support_ticket",
            "resolve": "resolve_support_ticket",
            "close": "close_support_ticket",
        }[action]
        if action == "close":
            if user.role not in {"admin", "super_admin"}:
                raise ApiError("FORBIDDEN", status_code=403)
            self._require_admin_actor(user)
        else:
            self._require_support_permission(user, permission, ticket)
        self._rate_limit(action, user, ticket.id)
        reason = _sanitize_text(reason, 500)
        if not reason:
            raise ApiError("ADMIN_REASON_REQUIRED", status_code=400)
        def compute() -> dict[str, Any]:
            current = self._require_ticket(ticket.id)
            if target_status == "closed":
                if current.status != "resolved":
                    raise ApiError("SUPPORT_TICKET_STATUS_INVALID", status_code=400)
            elif current.status not in ACTIVE_SUPPORT_STATUSES:
                raise ApiError("SUPPORT_TICKET_STATUS_INVALID", status_code=400)
            from_status = current.status
            fields: dict[str, Any] = {"status": target_status}
            if target_status == "escalated":
                fields["escalated_at"] = utc_now()
                if extra.get("existing_dispute_id"):
                    fields["dispute_id"] = self._validate_existing_dispute_link(ticket=ticket, dispute_id=extra["existing_dispute_id"])
            if target_status == "resolved":
                fields["resolved_at"] = utc_now()
            if target_status == "closed":
                fields["closed_at"] = utc_now()
            updated = self._repository.update_ticket(current, **fields)
            event_type = {
                "escalate": "support_ticket_escalated",
                "resolve": "support_ticket_resolved",
                "close": "support_ticket_closed",
            }[action]
            self._repository.create_event(ticket_id=current.id, actor_user_id=user.id, actor_role=user.role, event_type=event_type, from_status=from_status, to_status=target_status, reason=reason, metadata_json={"existing_dispute_id": extra.get("existing_dispute_id")} if extra else {})
            self._audit.write(event_type=event_type, actor_user_id=user.id, actor_role=user.role, resource_type="support_ticket", resource_id=current.id, request_id=request_id, metadata_json={"from_status": from_status, "to_status": target_status})
            if target_status == "escalated" and extra.get("existing_dispute_id"):
                self._repository.create_event(ticket_id=current.id, actor_user_id=user.id, actor_role=user.role, event_type="support_ticket_linked_to_dispute", reason=reason, metadata_json={"existing_dispute_id": extra["existing_dispute_id"]})
            if target_status in {"resolved", "closed"}:
                self._notifications.ticket_status_changed(
                    ticket=updated,
                    notification_type=f"support_ticket_{target_status}_participant",
                    request_id=request_id,
                )
            return self._detail_payload(ticket=updated, user=user, admin=True)

        return self._idempotency.replay_or_store(f"support:{action}:{user.id}:{ticket.id}:{idempotency_key}", payload={"reason": reason, **extra}, compute=compute)

    def _validate_existing_dispute_link(self, *, ticket: SupportTicketRecord, dispute_id: str) -> str:
        dispute_id = _require_uuid(dispute_id, "DISPUTE_NOT_FOUND")
        dispute = self._disputes.get_dispute(dispute_id)
        if dispute is None:
            raise ApiError("DISPUTE_NOT_FOUND", status_code=404)
        order = self._orders.get_by_id(dispute.order_id)
        if order is None:
            raise ApiError("DISPUTE_NOT_FOUND", status_code=404)
        if ticket.order_id and dispute.order_id != ticket.order_id:
            raise ApiError("DISPUTE_NOT_FOUND", status_code=404)
        if ticket.business_id and order.business_id != ticket.business_id:
            raise ApiError("DISPUTE_NOT_FOUND", status_code=404)
        if ticket.requester_role == "remitter" and order.remitter_user_id != ticket.requester_user_id:
            raise ApiError("DISPUTE_NOT_FOUND", status_code=404)
        return dispute.id

    def _validate_upload(self, *, user: UserRecord, ticket: SupportTicketRecord, mime_type: str, content: bytes) -> ValidatedPhoto:
        self._rate_limit("upload", user, ticket.id)
        if ticket.status not in ACTIVE_SUPPORT_STATUSES:
            raise ApiError("SUPPORT_TICKET_STATUS_INVALID", status_code=400)
        if not content:
            raise ApiError("SUPPORT_ATTACHMENT_INVALID", message=PHOTO_UPLOAD_ERROR_MESSAGE, status_code=400)
        if len(content) > MAX_SUPPORT_ATTACHMENT_SIZE_BYTES:
            raise ApiError("SUPPORT_ATTACHMENT_TOO_LARGE", status_code=400)
        return validate_photo_upload(
            content=content,
            declared_mime_type=mime_type,
            invalid_error_code="SUPPORT_ATTACHMENT_INVALID",
            type_error_code="SUPPORT_ATTACHMENT_TYPE_NOT_ALLOWED",
        )
