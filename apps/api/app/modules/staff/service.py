from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.config import Settings
from app.core.errors import ApiError
from app.modules.staff.models import (
    FORBIDDEN_STAFF_PERMISSIONS,
    STAFF_PERMISSIONS,
    STAFF_ROLES,
    STAFF_SCOPES,
    StaffProfileRecord,
)
from app.modules.staff.presenters import staff_invite_payload, staff_profile_detail, staff_profile_summary
from app.modules.staff.schemas import StaffInviteCreateRequest, StaffPermissionInput, StaffPermissionsUpdateRequest
from app.modules.users.models import UserRecord


STAFF_DISCLAIMER = "Delegacion interna NODO: permisos granulares, revocables y auditables. Backend RBAC conserva la autoridad."
STAFF_BASE_ROLES = {"support", "admin", "super_admin"}
ROLE_BASE_COMPATIBILITY = {
    "support_agent": {"support"},
    "support_lead": {"support"},
    "operations_readonly": {"support"},
    "admin": {"admin"},
    "super_admin": {"super_admin"},
}
ROLE_ALLOWED_PERMISSIONS = {
    "support_agent": {
        "view_support_queue",
        "view_assigned_support_tickets",
        "reply_support_ticket",
        "view_support_attachment",
    },
    "support_lead": {
        "view_support_queue",
        "view_assigned_support_tickets",
        "reply_support_ticket",
        "assign_support_ticket",
        "escalate_support_ticket",
        "resolve_support_ticket",
        "close_support_ticket",
        "view_support_attachment",
    },
    "operations_readonly": {
        "view_users_masked",
        "view_businesses_masked",
        "view_orders_masked",
        "view_audit_limited",
        "view_metrics_limited",
    },
    "admin": STAFF_PERMISSIONS,
    "super_admin": STAFF_PERMISSIONS,
}


def _require_uuid(value: str, code: str = "STAFF_PROFILE_NOT_FOUND") -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError) as exc:
        raise ApiError(code, status_code=404) from exc


def _reason(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ApiError("ADMIN_REASON_REQUIRED", status_code=400)
    return cleaned[:500]


def _parse_telegram_id(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ApiError("VALIDATION_ERROR", status_code=422) from exc


class StaffService:
    def __init__(self, *, settings: Settings, repository, audit_writer, rate_limiter, idempotency_store) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._audit = audit_writer
        self._rate = rate_limiter
        self._idempotency = idempotency_store

    def _rate_limit(self, action: str, user: UserRecord) -> None:
        if not self._rate.allow(
            f"staff:{action}:{user.id}",
            max_attempts=self._settings.business_rate_limit_max_attempts,
            window_seconds=self._settings.business_rate_limit_window_seconds,
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def _require_read_actor(self, user: UserRecord) -> None:
        if user.status != "active" or user.role not in {"admin", "super_admin"}:
            raise ApiError("FORBIDDEN", status_code=403)

    def _require_super_admin(self, user: UserRecord) -> None:
        if user.status != "active" or user.role != "super_admin":
            raise ApiError("FORBIDDEN", status_code=403)

    def _audit_event(self, *, event_type: str, user: UserRecord, resource_id: str | None, request_id: str, metadata: dict[str, Any] | None = None) -> None:
        self._audit.write(
            event_type=event_type,
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="staff",
            resource_id=resource_id,
            request_id=request_id,
            metadata_json=metadata or {},
        )

    def _validate_staff_role(self, value: str) -> str:
        if value not in STAFF_ROLES:
            raise ApiError("STAFF_ASSIGNMENT_INVALID", status_code=400)
        return value

    def _validate_permissions(self, *, staff_role: str, values: list[StaffPermissionInput]) -> list[dict[str, str | None]]:
        seen: set[tuple[str, str, str | None]] = set()
        parsed = []
        allowed_permissions = ROLE_ALLOWED_PERMISSIONS[staff_role]
        for item in values:
            if item.permission in FORBIDDEN_STAFF_PERMISSIONS or item.permission not in STAFF_PERMISSIONS:
                raise ApiError("STAFF_PERMISSION_CONFLICT", status_code=409)
            if item.permission not in allowed_permissions:
                raise ApiError("STAFF_PERMISSION_CONFLICT", status_code=409)
            if item.scope not in STAFF_SCOPES:
                raise ApiError("STAFF_ASSIGNMENT_INVALID", status_code=400)
            key = (item.permission, item.scope, item.scope_value)
            if key in seen:
                raise ApiError("STAFF_PERMISSION_CONFLICT", status_code=409)
            seen.add(key)
            parsed.append({"permission": item.permission, "scope": item.scope, "scope_value": item.scope_value})
        return parsed

    def _ensure_target_user_compatible(self, user_id: str, *, staff_role: str) -> dict[str, Any]:
        target = self._repository.get_user(user_id)
        if target is None:
            raise ApiError("USER_NOT_FOUND", status_code=404)
        if target.get("status") != "active" or target.get("role") not in STAFF_BASE_ROLES:
            raise ApiError("STAFF_ASSIGNMENT_INVALID", status_code=400)
        if target.get("role") not in ROLE_BASE_COMPATIBILITY[staff_role]:
            raise ApiError("STAFF_ASSIGNMENT_INVALID", status_code=400)
        return target

    def list_staff(self, *, user: UserRecord, status: str | None, staff_role: str | None, q: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        self._require_read_actor(user)
        self._rate_limit("list", user)
        if status and status not in {"active", "suspended", "revoked"}:
            raise ApiError("STAFF_STATUS_INVALID", status_code=400)
        if staff_role:
            self._validate_staff_role(staff_role)
        profiles, next_cursor = self._repository.list_profiles(status=status, staff_role=staff_role, q=q, cursor=cursor, limit=limit)
        items = []
        for profile in profiles:
            permissions = self._repository.list_permissions(profile.id)
            items.append(
                staff_profile_summary(
                    profile,
                    user=self._repository.get_user(profile.user_id),
                    permission_count=sum(1 for item in permissions if item.status == "active"),
                )
            )
        return {"items": items, "next_cursor": next_cursor, "disclaimer": STAFF_DISCLAIMER}

    def detail(self, *, user: UserRecord, profile_id: str, request_id: str) -> dict[str, Any]:
        self._require_read_actor(user)
        self._rate_limit("detail", user)
        profile = self._require_profile(profile_id)
        return {
            "staff": staff_profile_detail(
                profile,
                user=self._repository.get_user(profile.user_id),
                permissions=self._repository.list_permissions(profile.id),
            ),
            "disclaimer": STAFF_DISCLAIMER,
        }

    def create_invite(self, *, user: UserRecord, payload: StaffInviteCreateRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        self._require_super_admin(user)
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        self._rate_limit("invite", user)
        reason = _reason(payload.reason)
        staff_role = self._validate_staff_role(payload.staff_role)
        permissions = self._validate_permissions(staff_role=staff_role, values=payload.permissions)
        target_user_id = _require_uuid(payload.target_user_id, "USER_NOT_FOUND") if payload.target_user_id else None
        target_telegram_id = _parse_telegram_id(payload.target_telegram_id)
        target_username = payload.target_username.strip() if payload.target_username else None
        if not target_user_id and target_telegram_id is None and not target_username:
            raise ApiError("STAFF_INVITE_INVALID", status_code=400)

        def compute() -> dict[str, Any]:
            invite = self._repository.create_invite(
                target_user_id=target_user_id,
                target_telegram_id=target_telegram_id,
                target_username=target_username,
                staff_role=staff_role,
                expires_at=payload.expires_at,
                created_by_super_admin_id=user.id,
                reason=reason,
            )
            profile = None
            if target_user_id:
                target = self._ensure_target_user_compatible(target_user_id, staff_role=staff_role)
                profile = self._repository.create_or_activate_profile(
                    user_id=target_user_id,
                    staff_role=staff_role,
                    display_name=target.get("first_name") or target.get("username"),
                    actor_id=user.id,
                    reason=reason,
                )
                self._repository.replace_permissions(profile_id=profile.id, permissions=permissions, actor_id=user.id, reason=reason)
                self._audit_event(event_type="staff_activated", user=user, resource_id=profile.id, request_id=request_id, metadata={"staff_role": staff_role})
            self._audit_event(event_type="staff_invite_created", user=user, resource_id=invite.id, request_id=request_id, metadata={"staff_role": staff_role})
            return {"invite": staff_invite_payload(invite, staff_profile_id=profile.id if profile else None), "disclaimer": STAFF_DISCLAIMER}

        return self._idempotency.replay_or_store(
            f"staff:invite:{user.id}:{idempotency_key}",
            payload=payload.model_dump(mode="json"),
            compute=compute,
        )

    def activate(self, *, user: UserRecord, profile_id: str, reason: str, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._set_status(user=user, profile_id=profile_id, status="active", reason=reason, request_id=request_id, idempotency_key=idempotency_key, event_type="staff_activated")

    def suspend(self, *, user: UserRecord, profile_id: str, reason: str, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._set_status(user=user, profile_id=profile_id, status="suspended", reason=reason, request_id=request_id, idempotency_key=idempotency_key, event_type="staff_suspended")

    def revoke(self, *, user: UserRecord, profile_id: str, reason: str, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._set_status(user=user, profile_id=profile_id, status="revoked", reason=reason, request_id=request_id, idempotency_key=idempotency_key, event_type="staff_revoked")

    def _set_status(self, *, user: UserRecord, profile_id: str, status: str, reason: str, request_id: str, idempotency_key: str | None, event_type: str) -> dict[str, Any]:
        self._require_super_admin(user)
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        reason = _reason(reason)
        profile_id = _require_uuid(profile_id)
        self._rate_limit(f"status:{status}", user)

        def compute() -> dict[str, Any]:
            profile = self._require_profile(profile_id)
            if profile.status == status:
                raise ApiError("STAFF_STATUS_INVALID", status_code=409)
            if profile.staff_role == "super_admin" and profile.status == "active" and status in {"suspended", "revoked"} and self._repository.count_active_super_admin_profiles() <= 1:
                raise ApiError("STAFF_LAST_SUPER_ADMIN_REQUIRED", status_code=409)
            if status == "active":
                self._ensure_target_user_compatible(profile.user_id, staff_role=profile.staff_role)
            updated = self._repository.set_profile_status(profile_id=profile.id, status=status, actor_id=user.id, reason=reason)
            if updated is None:
                raise ApiError("STAFF_PROFILE_NOT_FOUND", status_code=404)
            self._audit_event(event_type=event_type, user=user, resource_id=profile.id, request_id=request_id, metadata={"reason": reason, "from_status": profile.status, "to_status": status})
            return {"staff": staff_profile_detail(updated, user=self._repository.get_user(updated.user_id), permissions=self._repository.list_permissions(updated.id)), "disclaimer": STAFF_DISCLAIMER}

        return self._idempotency.replay_or_store(
            f"staff:status:{profile_id}:{status}:{idempotency_key}",
            payload={"profile_id": profile_id, "status": status, "reason": reason},
            compute=compute,
        )

    def update_permissions(self, *, user: UserRecord, profile_id: str, payload: StaffPermissionsUpdateRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        self._require_super_admin(user)
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        reason = _reason(payload.reason)
        profile_id = _require_uuid(profile_id)
        self._rate_limit("permissions", user)

        def compute() -> dict[str, Any]:
            profile = self._require_profile(profile_id)
            permissions = self._validate_permissions(staff_role=profile.staff_role, values=payload.permissions)
            self._repository.replace_permissions(profile_id=profile.id, permissions=permissions, actor_id=user.id, reason=reason)
            updated_permissions = self._repository.list_permissions(profile.id)
            self._audit_event(event_type="staff_permissions_updated", user=user, resource_id=profile.id, request_id=request_id, metadata={"permission_count": len(permissions)})
            return {"staff": staff_profile_detail(profile, user=self._repository.get_user(profile.user_id), permissions=updated_permissions), "disclaimer": STAFF_DISCLAIMER}

        return self._idempotency.replay_or_store(
            f"staff:permissions:{profile_id}:{idempotency_key}",
            payload=payload.model_dump(mode="json"),
            compute=compute,
        )

    def activity(self, *, user: UserRecord, profile_id: str, event_type: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        self._require_read_actor(user)
        self._rate_limit("activity", user)
        profile = self._require_profile(profile_id)
        items, next_cursor = self._repository.list_activity(profile_id=profile.id, event_type=event_type, cursor=cursor, limit=limit)
        self._audit_event(event_type="staff_activity_viewed", user=user, resource_id=profile.id, request_id=request_id, metadata={"event_type": event_type})
        return {"items": items, "next_cursor": next_cursor, "disclaimer": STAFF_DISCLAIMER}

    def _require_profile(self, profile_id: str) -> StaffProfileRecord:
        profile = self._repository.get_profile(_require_uuid(profile_id))
        if profile is None:
            raise ApiError("STAFF_PROFILE_NOT_FOUND", status_code=404)
        return profile


def has_staff_permission(repository, *, user: UserRecord, permission: str, ticket=None) -> bool:  # type: ignore[no-untyped-def]
    if user.status != "active":
        return False
    if user.role in {"admin", "super_admin"}:
        return True
    if user.role != "support":
        return False
    profile = repository.get_active_profile_for_user(user.id) if repository is not None else None
    if profile is None or profile.staff_role not in {"support_agent", "support_lead", "operations_readonly"}:
        return False
    for item in repository.list_active_permissions_for_user(user.id):
        if item.permission != permission:
            continue
        if item.scope == "global_readonly":
            return True
        if item.scope == "assigned_only" and ticket is not None and getattr(ticket, "assigned_support_user_id", None) == user.id:
            return True
        if item.scope == "queue_scope" and (item.scope_value is None or ticket is None or item.scope_value == getattr(ticket, "scope", None)):
            return True
        if item.scope == "category_scope" and ticket is not None and item.scope_value == getattr(ticket, "category", None):
            return True
    return False


def require_staff_permission(repository, *, user: UserRecord, permission: str, ticket=None) -> None:  # type: ignore[no-untyped-def]
    if not has_staff_permission(repository, user=user, permission=permission, ticket=ticket):
        raise ApiError("STAFF_PERMISSION_DENIED", status_code=403)
