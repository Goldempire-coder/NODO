from __future__ import annotations

from typing import Any

from app.modules.admin.user_presenters import mask_telegram_id
from app.modules.staff.models import StaffInviteRecord, StaffPermissionRecord, StaffProfileRecord


def iso(value) -> str | None:  # type: ignore[no-untyped-def]
    return value.isoformat() if value else None


def staff_profile_summary(profile: StaffProfileRecord, *, user: dict[str, Any] | None = None, permission_count: int = 0, last_activity_at=None) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "display_name": profile.display_name or (user or {}).get("first_name") or (user or {}).get("username"),
        "username": (user or {}).get("username"),
        "telegram_id_masked": mask_telegram_id((user or {}).get("telegram_id")),
        "staff_role": profile.staff_role,
        "status": profile.status,
        "permission_count": permission_count,
        "last_activity_at": iso(last_activity_at),
        "created_at": iso(profile.created_at),
        "updated_at": iso(profile.updated_at),
    }


def staff_permission_payload(permission: StaffPermissionRecord) -> dict[str, Any]:
    return {
        "id": permission.id,
        "permission": permission.permission,
        "scope": permission.scope,
        "scope_value": permission.scope_value,
        "status": permission.status,
        "created_at": iso(permission.created_at),
        "revoked_at": iso(permission.revoked_at),
    }


def staff_profile_detail(profile: StaffProfileRecord, *, user: dict[str, Any] | None, permissions: list[StaffPermissionRecord]) -> dict[str, Any]:
    return {
        **staff_profile_summary(profile, user=user, permission_count=sum(1 for item in permissions if item.status == "active")),
        "user_status": (user or {}).get("status"),
        "base_role": (user or {}).get("role"),
        "permissions": [staff_permission_payload(item) for item in permissions],
        "reason": profile.reason,
        "activated_at": iso(profile.activated_at),
        "suspended_at": iso(profile.suspended_at),
        "revoked_at": iso(profile.revoked_at),
    }


def staff_invite_payload(invite: StaffInviteRecord, *, staff_profile_id: str | None = None) -> dict[str, Any]:
    return {
        "invite_id": invite.id,
        "staff_profile_id": staff_profile_id,
        "status": invite.status,
        "staff_role": invite.staff_role,
        "target_user_id": invite.target_user_id,
        "target_telegram_id_masked": mask_telegram_id(invite.target_telegram_id),
        "target_username": invite.target_username,
        "expires_at": iso(invite.expires_at),
        "created_at": iso(invite.created_at),
    }
