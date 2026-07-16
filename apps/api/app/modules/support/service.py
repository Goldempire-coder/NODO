from __future__ import annotations

import hashlib
import re
from typing import Any
from uuid import UUID

from app.core.config import Settings
from app.core.errors import ApiError
from app.modules.businesses.access_control import evaluate_business_access
from app.modules.businesses.models import BusinessRecord
from app.modules.support.models import (
    ALLOWED_SUPPORT_ATTACHMENT_MIME_TYPES,
    MAX_SUPPORT_ATTACHMENT_SIZE_BYTES,
    SUPPORT_CATEGORIES,
    SUPPORT_MESSAGE_VISIBILITIES,
    SUPPORT_SCOPES,
    SUPPORT_STATUSES,
    SupportTicketRecord,
    new_id,
    utc_now,
)
from app.modules.support.presenters import event_public, file_asset_public, message_public, ticket_summary
from app.modules.support.schemas import (
    AdminSupportMessageCreateRequest,
    SupportEscalateRequest,
    SupportMessageCreateRequest,
    SupportTicketCreateRequest,
)
from app.modules.staff.service import require_staff_permission
from app.modules.users.models import UserRecord


SUPPORT_DISCLAIMER = "NODO registra evidencia y estado; no recibe, retiene, transfiere ni garantiza fondos."
ADMIN_ROLES = {"admin", "super_admin", "support"}


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

    def _detail_payload(self, *, ticket: SupportTicketRecord, user: UserRecord, admin: bool = False) -> dict[str, Any]:
        messages = self._repository.list_messages(ticket_id=ticket.id)
        resources = [("support_ticket", ticket.id)] + [("support_message", message.id) for message in messages]
        attachments = self._repository.list_files_for_resources(resources=resources)
        visible_messages = [
            message
            for message in messages
            if admin or message.visibility == "participants" or message.sender_user_id == user.id
        ]
        return {
            **ticket_summary(ticket),
            "attachments": [_attachment_payload(file) for file in attachments.get(("support_ticket", ticket.id), [])],
            "messages": [
                message_public(message, attachments.get(("support_message", message.id), []))
                for message in visible_messages
            ],
            "events": [event_public(event) for event in self._repository.list_events(ticket_id=ticket.id)] if admin else [],
            "disclaimer": SUPPORT_DISCLAIMER,
        }

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
            ticket = self._repository.create_ticket(
                requester_user_id=user.id,
                requester_role=user.role,
                requester_surface=fields["requester_surface"],
                scope=payload.scope,
                category=payload.category,
                status="open",
                priority="normal",
                subject=subject,
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
            self._repository.create_message(ticket_id=ticket.id, sender_user_id=user.id, sender_role=user.role, body=message_body, visibility="participants")
            self._repository.create_event(ticket_id=ticket.id, actor_user_id=user.id, actor_role=user.role, event_type="support_ticket_created", to_status="open", metadata_json={"scope": payload.scope, "category": payload.category})
            self._audit.write(event_type="support_ticket_created", actor_user_id=user.id, actor_role=user.role, resource_type="support_ticket", resource_id=ticket.id, request_id=request_id, metadata_json={"scope": payload.scope, "category": payload.category})
            return self._detail_payload(ticket=ticket, user=user)

        return self._idempotency.replay_or_store(f"support:ticket:{user.id}:{idempotency_key}", payload=request_payload, compute=compute)

    def list_user_tickets(self, *, user: UserRecord, status: str | None, scope: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        self._rate_limit("list", user)
        if status and status not in SUPPORT_STATUSES:
            raise ApiError("SUPPORT_TICKET_STATUS_INVALID", status_code=400)
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
            status=status,
            scope=scope,
            category=None,
            priority=None,
            assigned_support_user_id=None,
            cursor=cursor,
            limit=limit,
        )
        visible = [ticket for ticket in items if self._ticket_visible_to_user(ticket=ticket, user=user)]
        return {"items": [ticket_summary(ticket) for ticket in visible], "next_cursor": next_cursor}

    def user_ticket_detail(self, *, user: UserRecord, ticket_id: str, request_id: str) -> dict[str, Any]:
        ticket = self._require_ticket(ticket_id)
        self._rate_limit("detail", user, ticket.id)
        if not self._ticket_visible_to_user(ticket=ticket, user=user) or user.role in ADMIN_ROLES:
            raise ApiError("SUPPORT_TICKET_NOT_FOUND", status_code=404)
        return self._detail_payload(ticket=ticket, user=user)

    def create_user_message(self, *, user: UserRecord, ticket_id: str, payload: SupportMessageCreateRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        if payload.attachment_ids:
            raise ApiError("SUPPORT_ATTACHMENT_INVALID", status_code=400)
        ticket = self._require_ticket(ticket_id)
        if not self._ticket_visible_to_user(ticket=ticket, user=user) or user.role in ADMIN_ROLES:
            raise ApiError("SUPPORT_TICKET_NOT_FOUND", status_code=404)
        return self._create_message(user=user, ticket=ticket, body=payload.body, visibility="participants", request_id=request_id, idempotency_key=idempotency_key, admin=False)

    def list_admin_tickets(self, *, user: UserRecord, status: str | None, scope: str | None, category: str | None, priority: str | None, assigned_support_user_id: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        self._require_support_permission(user, "view_support_queue")
        self._rate_limit("admin_list", user)
        items, next_cursor = self._repository.list_tickets(
            requester_user_id=None,
            business_id=None,
            status=status,
            scope=scope,
            category=category,
            priority=priority,
            assigned_support_user_id=assigned_support_user_id,
            cursor=cursor,
            limit=limit,
        )
        return {"items": [ticket_summary(ticket) for ticket in items], "next_cursor": next_cursor}

    def admin_ticket_detail(self, *, user: UserRecord, ticket_id: str, request_id: str) -> dict[str, Any]:
        ticket = self._require_ticket(ticket_id)
        if user.role == "support" and ticket.assigned_support_user_id == user.id:
            self._require_support_permission(user, "view_assigned_support_tickets", ticket)
        else:
            self._require_support_permission(user, "view_support_queue", ticket)
        self._rate_limit("admin_detail", user, ticket.id)
        return self._detail_payload(ticket=ticket, user=user, admin=True)

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
            updated = self._repository.update_ticket(ticket, assigned_support_user_id=assignee.id)
            self._repository.create_event(ticket_id=ticket.id, actor_user_id=user.id, actor_role=user.role, event_type="support_ticket_assigned", reason=reason, metadata_json={"assigned_support_user_id": assignee.id})
            self._audit.write(event_type="support_ticket_assigned", actor_user_id=user.id, actor_role=user.role, resource_type="support_ticket", resource_id=ticket.id, request_id=request_id, metadata_json={"assigned_support_user_id": assignee.id})
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
        self._validate_upload(user=user, ticket=ticket, mime_type=mime_type, content=content)
        payload = {"ticket_id": ticket.id, "file_name": file_name, "mime_type": mime_type, "size_bytes": len(content), "content_sha256": hashlib.sha256(content).hexdigest()}

        def compute() -> dict[str, Any]:
            file_id = new_id()
            stored = self._storage.store_support_attachment(ticket_id=ticket.id, file_id=file_id, file_name=file_name, content=content)
            file = self._repository.create_file_asset(file_id=file_id, owner_user_id=user.id, resource_type="support_ticket", resource_id=ticket.id, storage_path=stored.storage_path, mime_type=mime_type, size_bytes=stored.size_bytes)
            self._repository.create_event(ticket_id=ticket.id, actor_user_id=user.id, actor_role=user.role, event_type="support_attachment_uploaded", metadata_json={"file_asset_id": file.id, "mime_type": mime_type, "size_bytes": stored.size_bytes})
            self._audit.write(event_type="support_attachment_uploaded", actor_user_id=user.id, actor_role=user.role, resource_type="support_ticket", resource_id=ticket.id, request_id=request_id, metadata_json={"file_asset_id": file.id, "mime_type": mime_type, "size_bytes": stored.size_bytes})
            return {"attachment": file_asset_public(file), "disclaimer": SUPPORT_DISCLAIMER}

        return self._idempotency.replay_or_store(f"support:attachment:{user.id}:{ticket.id}:{idempotency_key}", payload=payload, compute=compute)

    def attachment_view_url(self, *, user: UserRecord, ticket_id: str, file_id: str, reason: str, request_id: str) -> dict[str, Any]:
        if self._storage is None:
            raise ApiError("STORAGE_UNAVAILABLE", status_code=503)
        ticket = self._require_ticket(ticket_id)
        self._require_support_permission(user, "view_support_attachment", ticket)
        reason = _sanitize_text(reason, 500)
        if not reason:
            raise ApiError("ADMIN_REASON_REQUIRED", status_code=400)
        file = self._repository.get_file_asset(_require_uuid(file_id, "SUPPORT_ATTACHMENT_NOT_FOUND"))
        allowed_resource_ids = {ticket.id, *[message.id for message in self._repository.list_messages(ticket_id=ticket.id)]}
        if file is None or file.file_type != "support_attachment" or file.resource_type not in {"support_ticket", "support_message"} or file.resource_id not in allowed_resource_ids:
            raise ApiError("SUPPORT_ATTACHMENT_ACCESS_DENIED", status_code=403)
        url = self._storage.signed_view_url(storage_path=file.storage_path, expires_in=min(self._settings.storage_signed_url_ttl_seconds, 300))
        self._repository.create_event(ticket_id=ticket.id, actor_user_id=user.id, actor_role=user.role, event_type="support_attachment_viewed", reason=reason, metadata_json={"file_asset_id": file.id})
        self._audit.write(event_type="support_attachment_viewed", actor_user_id=user.id, actor_role=user.role, resource_type="support_ticket", resource_id=ticket.id, request_id=request_id, metadata_json={"file_asset_id": file.id})
        return {"url": url, "expires_in_seconds": min(self._settings.storage_signed_url_ttl_seconds, 300)}

    def _require_ticket(self, ticket_id: str) -> SupportTicketRecord:
        ticket = self._repository.get_ticket(_require_uuid(ticket_id, "SUPPORT_TICKET_NOT_FOUND"))
        if ticket is None:
            raise ApiError("SUPPORT_TICKET_NOT_FOUND", status_code=404)
        return ticket

    def _create_message(self, *, user: UserRecord, ticket: SupportTicketRecord, body: str, visibility: str, request_id: str, idempotency_key: str | None, admin: bool) -> dict[str, Any]:
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        if ticket.status == "closed":
            raise ApiError("SUPPORT_TICKET_STATUS_INVALID", status_code=400)
        self._rate_limit("message", user, ticket.id)
        body = _sanitize_text(body, 2000)
        if not body:
            raise ApiError("SUPPORT_MESSAGE_REQUIRED", status_code=400)

        def compute() -> dict[str, Any]:
            message = self._repository.create_message(ticket_id=ticket.id, sender_user_id=user.id, sender_role=user.role, body=body, visibility=visibility)
            target_status = ticket.status
            if visibility == "participants" and ticket.status != "escalated":
                target_status = "waiting_user" if admin else "waiting_support"
            if target_status != ticket.status:
                self._repository.update_ticket(ticket, status=target_status)
            self._repository.create_event(ticket_id=ticket.id, actor_user_id=user.id, actor_role=user.role, event_type="support_message_created", metadata_json={"visibility": visibility})
            self._audit.write(event_type="support_message_created", actor_user_id=user.id, actor_role=user.role, resource_type="support_ticket", resource_id=ticket.id, request_id=request_id, metadata_json={"visibility": visibility})
            current_ticket = self._repository.get_ticket(ticket.id) or ticket
            return {"message": message_public(message), "ticket": ticket_summary(current_ticket), "disclaimer": SUPPORT_DISCLAIMER}

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
        self._require_support_permission(user, permission, ticket)
        self._rate_limit(action, user, ticket.id)
        reason = _sanitize_text(reason, 500)
        if not reason:
            raise ApiError("ADMIN_REASON_REQUIRED", status_code=400)
        if target_status == "closed" and ticket.status != "resolved":
            raise ApiError("SUPPORT_TICKET_STATUS_INVALID", status_code=400)
        if ticket.status == "closed":
            raise ApiError("SUPPORT_TICKET_STATUS_INVALID", status_code=400)

        def compute() -> dict[str, Any]:
            from_status = ticket.status
            fields: dict[str, Any] = {"status": target_status}
            if target_status == "escalated":
                fields["escalated_at"] = utc_now()
                if extra.get("existing_dispute_id"):
                    fields["dispute_id"] = self._validate_existing_dispute_link(ticket=ticket, dispute_id=extra["existing_dispute_id"])
            if target_status == "resolved":
                fields["resolved_at"] = utc_now()
            if target_status == "closed":
                fields["closed_at"] = utc_now()
            updated = self._repository.update_ticket(ticket, **fields)
            event_type = {
                "escalate": "support_ticket_escalated",
                "resolve": "support_ticket_resolved",
                "close": "support_ticket_closed",
            }[action]
            self._repository.create_event(ticket_id=ticket.id, actor_user_id=user.id, actor_role=user.role, event_type=event_type, from_status=from_status, to_status=target_status, reason=reason, metadata_json={"existing_dispute_id": extra.get("existing_dispute_id")} if extra else {})
            self._audit.write(event_type=event_type, actor_user_id=user.id, actor_role=user.role, resource_type="support_ticket", resource_id=ticket.id, request_id=request_id, metadata_json={"from_status": from_status, "to_status": target_status})
            if target_status == "escalated" and extra.get("existing_dispute_id"):
                self._repository.create_event(ticket_id=ticket.id, actor_user_id=user.id, actor_role=user.role, event_type="support_ticket_linked_to_dispute", reason=reason, metadata_json={"existing_dispute_id": extra["existing_dispute_id"]})
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

    def _validate_upload(self, *, user: UserRecord, ticket: SupportTicketRecord, mime_type: str, content: bytes) -> None:
        self._rate_limit("upload", user, ticket.id)
        if ticket.status == "closed":
            raise ApiError("SUPPORT_TICKET_STATUS_INVALID", status_code=400)
        if mime_type not in ALLOWED_SUPPORT_ATTACHMENT_MIME_TYPES:
            raise ApiError("SUPPORT_ATTACHMENT_TYPE_NOT_ALLOWED", status_code=400)
        if not content:
            raise ApiError("SUPPORT_ATTACHMENT_INVALID", status_code=400)
        if len(content) > MAX_SUPPORT_ATTACHMENT_SIZE_BYTES:
            raise ApiError("SUPPORT_ATTACHMENT_TOO_LARGE", status_code=400)
