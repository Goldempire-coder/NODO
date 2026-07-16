from __future__ import annotations

from datetime import datetime
from threading import RLock
from typing import Any

from app.modules.staff.models import StaffInviteRecord, StaffPermissionRecord, StaffProfileRecord, new_id, utc_now


class InMemoryStaffRepository:
    def __init__(self, *, users=None, audit_writer=None) -> None:  # type: ignore[no-untyped-def]
        self._users = users
        self._audit = audit_writer
        self._lock = RLock()
        self.profiles: dict[str, StaffProfileRecord] = {}
        self.permissions: dict[str, StaffPermissionRecord] = {}
        self.invites: dict[str, StaffInviteRecord] = {}

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        user = getattr(self._users, "_users_by_id", {}).get(user_id)
        return user.__dict__.copy() if user else None

    def count_active_super_admin_profiles(self) -> int:
        return sum(1 for item in self.profiles.values() if item.status == "active" and item.staff_role == "super_admin")

    def list_profiles(self, *, status: str | None, staff_role: str | None, q: str | None, cursor: str | None, limit: int) -> tuple[list[StaffProfileRecord], str | None]:
        items = list(self.profiles.values())
        if status:
            items = [item for item in items if item.status == status]
        if staff_role:
            items = [item for item in items if item.staff_role == staff_role]
        if q:
            needle = q.lower()
            items = [
                item
                for item in items
                if needle in (item.display_name or "").lower()
                or needle in ((self.get_user(item.user_id) or {}).get("username") or "").lower()
            ]
        if cursor:
            items = [item for item in items if item.created_at.isoformat() < cursor]
        items.sort(key=lambda item: item.created_at, reverse=True)
        page = items[:limit]
        return page, page[-1].created_at.isoformat() if len(page) == limit else None

    def get_profile(self, profile_id: str) -> StaffProfileRecord | None:
        return self.profiles.get(profile_id)

    def get_active_profile_for_user(self, user_id: str) -> StaffProfileRecord | None:
        for profile in self.profiles.values():
            if profile.user_id == user_id and profile.status == "active":
                return profile
        return None

    def create_invite(self, *, target_user_id: str | None, target_telegram_id: int | None, target_username: str | None, staff_role: str, expires_at: datetime, created_by_super_admin_id: str, reason: str) -> StaffInviteRecord:
        invite = StaffInviteRecord(
            id=new_id(),
            target_user_id=target_user_id,
            target_telegram_id=target_telegram_id,
            target_username=target_username,
            invite_code_hash=None,
            staff_role=staff_role,
            status="pending",
            expires_at=expires_at,
            created_by_super_admin_id=created_by_super_admin_id,
            reason=reason,
        )
        with self._lock:
            self.invites[invite.id] = invite
        return invite

    def create_or_activate_profile(self, *, user_id: str, staff_role: str, display_name: str | None, actor_id: str, reason: str) -> StaffProfileRecord:
        now = utc_now()
        with self._lock:
            existing = self.get_active_profile_for_user(user_id)
            if existing is not None:
                existing.staff_role = staff_role
                existing.display_name = display_name or existing.display_name
                existing.reason = reason
                existing.updated_at = now
                return existing
            profile = StaffProfileRecord(
                id=new_id(),
                user_id=user_id,
                staff_role=staff_role,
                status="active",
                display_name=display_name,
                created_by_super_admin_id=actor_id,
                activated_by_super_admin_id=actor_id,
                activated_at=now,
                reason=reason,
                created_at=now,
                updated_at=now,
            )
            self.profiles[profile.id] = profile
            return profile

    def set_profile_status(self, *, profile_id: str, status: str, actor_id: str, reason: str) -> StaffProfileRecord | None:
        now = utc_now()
        with self._lock:
            profile = self.profiles.get(profile_id)
            if profile is None:
                return None
            profile.status = status
            profile.reason = reason
            profile.updated_at = now
            if status == "active":
                profile.activated_by_super_admin_id = actor_id
                profile.activated_at = now
            elif status == "suspended":
                profile.suspended_by_super_admin_id = actor_id
                profile.suspended_at = now
            elif status == "revoked":
                profile.revoked_by_super_admin_id = actor_id
                profile.revoked_at = now
                for permission in self.permissions.values():
                    if permission.staff_profile_id == profile_id and permission.status == "active":
                        permission.status = "revoked"
                        permission.revoked_by_super_admin_id = actor_id
                        permission.revoked_at = now
                        permission.updated_at = now
            return profile

    def replace_permissions(self, *, profile_id: str, permissions: list[dict[str, str | None]], actor_id: str, reason: str) -> list[StaffPermissionRecord]:
        now = utc_now()
        with self._lock:
            for permission in self.permissions.values():
                if permission.staff_profile_id == profile_id and permission.status == "active":
                    permission.status = "revoked"
                    permission.revoked_by_super_admin_id = actor_id
                    permission.revoked_at = now
                    permission.updated_at = now
            created = []
            for item in permissions:
                record = StaffPermissionRecord(
                    id=new_id(),
                    staff_profile_id=profile_id,
                    permission=str(item["permission"]),
                    scope=str(item["scope"]),
                    scope_value=item.get("scope_value"),
                    status="active",
                    granted_by_super_admin_id=actor_id,
                    reason=reason,
                    created_at=now,
                    updated_at=now,
                )
                self.permissions[record.id] = record
                created.append(record)
            return created

    def list_permissions(self, profile_id: str) -> list[StaffPermissionRecord]:
        return sorted(
            [item for item in self.permissions.values() if item.staff_profile_id == profile_id],
            key=lambda item: item.created_at,
            reverse=True,
        )

    def list_active_permissions_for_user(self, user_id: str) -> list[StaffPermissionRecord]:
        profile = self.get_active_profile_for_user(user_id)
        if profile is None:
            return []
        return [item for item in self.permissions.values() if item.staff_profile_id == profile.id and item.status == "active"]

    def list_activity(self, *, profile_id: str, event_type: str | None, cursor: str | None, limit: int) -> tuple[list[dict[str, Any]], str | None]:
        profile = self.get_profile(profile_id)
        if profile is None:
            return [], None
        events = [event for event in getattr(self._audit, "events", []) if event.actor_user_id == profile.user_id or event.resource_id == profile.id]
        if event_type:
            events = [event for event in events if event.event_type == event_type]
        if cursor:
            events = [event for event in events if event.created_at.isoformat() < cursor]
        events.sort(key=lambda item: item.created_at, reverse=True)
        page = events[:limit]
        return [
            {
                "event_type": event.event_type,
                "actor_user_id": event.actor_user_id,
                "actor_role": event.actor_role,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "metadata_json": event.metadata_json or {},
                "created_at": event.created_at.isoformat(),
            }
            for event in page
        ], page[-1].created_at.isoformat() if len(page) == limit else None
