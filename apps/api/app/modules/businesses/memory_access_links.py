from __future__ import annotations

from datetime import datetime

from app.core.errors import ApiError
from app.modules.businesses.access_link_selection import preferred_access_link
from app.modules.businesses.models import (
    BUSINESS_ACCESS_ROLES,
    BUSINESS_ACCESS_STATUSES,
    BusinessAccessLinkRecord,
    utc_now,
    new_id,
)


class InMemoryBusinessAccessLinksMixin:
    def create_access_link(
        self,
        *,
        business_id: str,
        user_id: str,
        telegram_id_snapshot: int,
        role_in_business: str,
        linked_by_admin_id: str,
        reason: str,
    ) -> BusinessAccessLinkRecord:
        if role_in_business not in BUSINESS_ACCESS_ROLES:
            raise ApiError("VALIDATION_ERROR", status_code=422)
        with self._lock:  # type: ignore[attr-defined]
            existing_links = [
                link
                for link in self.access_links.values()  # type: ignore[attr-defined]
                if link.business_id == business_id
                and link.user_id == user_id
                and link.role_in_business == role_in_business
                and link.status == "active"
            ]
            existing_links.sort(key=lambda link: (link.updated_at, link.id), reverse=True)
            existing = preferred_access_link(existing_links)
            if existing is not None:
                return existing
            if role_in_business == "owner":
                existing_owner = next(
                    (
                        link
                        for link in self.access_links.values()  # type: ignore[attr-defined]
                        if link.business_id == business_id
                        and link.role_in_business == "owner"
                        and link.status == "active"
                    ),
                    None,
                )
                if existing_owner is not None:
                    raise ApiError("CONFLICT", status_code=409)
            same_role_links = [
                link
                for link in self.access_links.values()  # type: ignore[attr-defined]
                if link.business_id == business_id
                and link.user_id == user_id
                and link.role_in_business == role_in_business
            ]
            if same_role_links:
                now = utc_now()
                selected = preferred_access_link(same_role_links)
                if selected is None:
                    raise ApiError("BUSINESS_ACCESS_LINK_REQUIRED", status_code=404)
                for link in same_role_links:
                    link.status = "active" if link.id == selected.id else "revoked"
                    link.telegram_id_snapshot = telegram_id_snapshot
                    link.linked_by_admin_id = linked_by_admin_id
                    link.reason = reason
                    link.suspended_at = None
                    link.blocked_at = None
                    link.revoked_at = None if link.id == selected.id else now
                    link.updated_at = now
                return selected
            now = utc_now()
            link = BusinessAccessLinkRecord(
                id=new_id(),
                business_id=business_id,
                user_id=user_id,
                telegram_id_snapshot=telegram_id_snapshot,
                role_in_business=role_in_business,
                status="active",
                linked_by_admin_id=linked_by_admin_id,
                linked_at=now,
                reason=reason,
                created_at=now,
                updated_at=now,
            )
            self.access_links[link.id] = link  # type: ignore[attr-defined]
            return link

    def get_access_link(self, link_id: str) -> BusinessAccessLinkRecord | None:
        return self.access_links.get(link_id)  # type: ignore[attr-defined]

    def get_access_link_for_business_user(
        self,
        *,
        business_id: str,
        user_id: str,
    ) -> BusinessAccessLinkRecord | None:
        links = [
            link
            for link in self.access_links.values()  # type: ignore[attr-defined]
            if link.business_id == business_id and link.user_id == user_id
        ]
        if not links:
            return None
        links.sort(
            key=lambda item: (item.role_in_business == "owner", item.status == "active", item.updated_at, item.id),
            reverse=True,
        )
        return links[0]

    def get_active_access_link_for_business_user(
        self,
        *,
        business_id: str,
        user_id: str,
    ) -> BusinessAccessLinkRecord | None:
        links = [
            link
            for link in self.access_links.values()  # type: ignore[attr-defined]
            if link.business_id == business_id
            and link.user_id == user_id
            and link.role_in_business == "owner"
            and link.status == "active"
        ]
        links.sort(key=lambda link: (link.updated_at, link.id), reverse=True)
        return links[0] if links else None

    def list_access_links_for_business(self, business_id: str) -> list[BusinessAccessLinkRecord]:
        return sorted(
            [link for link in self.access_links.values() if link.business_id == business_id],  # type: ignore[attr-defined]
            key=lambda link: (link.updated_at, link.id),
            reverse=True,
        )

    def set_access_link_status(
        self,
        *,
        link: BusinessAccessLinkRecord,
        status: str,
        reason: str,
    ) -> BusinessAccessLinkRecord:
        if status not in BUSINESS_ACCESS_STATUSES:
            raise ApiError("VALIDATION_ERROR", status_code=422)
        with self._lock:  # type: ignore[attr-defined]
            now = utc_now()
            linked_group = [
                candidate
                for candidate in self.access_links.values()  # type: ignore[attr-defined]
                if candidate.business_id == link.business_id
                and candidate.user_id == link.user_id
                and candidate.role_in_business == link.role_in_business
            ]
            for candidate in linked_group:
                candidate.status = status if status != "active" or candidate.id == link.id else "revoked"
                candidate.reason = reason
                candidate.updated_at = now
                if candidate.status == "active":
                    candidate.suspended_at = None
                    candidate.blocked_at = None
                    candidate.revoked_at = None
                elif candidate.status == "suspended":
                    candidate.suspended_at = now
                elif candidate.status == "blocked":
                    candidate.blocked_at = now
                elif candidate.status == "revoked":
                    candidate.revoked_at = now
            return next((candidate for candidate in linked_group if candidate.id == link.id), link)

    def set_access_link_pin_hash(self, *, link_id: str, pin_hash: str) -> BusinessAccessLinkRecord:
        with self._lock:  # type: ignore[attr-defined]
            link = self.access_links[link_id]  # type: ignore[attr-defined]
            now = utc_now()
            link.business_pin_hash = pin_hash
            link.business_pin_set_at = now
            link.business_pin_verified_at = None
            link.business_pin_unlocked_until = None
            link.business_pin_failed_attempts = 0
            link.business_pin_locked_until = None
            link.updated_at = now
            return link

    def mark_access_link_pin_verified(self, *, link_id: str, unlocked_until: datetime) -> BusinessAccessLinkRecord:
        with self._lock:  # type: ignore[attr-defined]
            link = self.access_links[link_id]  # type: ignore[attr-defined]
            link.business_pin_verified_at = utc_now()
            link.business_pin_unlocked_until = unlocked_until
            link.business_pin_failed_attempts = 0
            link.business_pin_locked_until = None
            link.updated_at = utc_now()
            return link

    def record_access_link_pin_failure(self, *, link_id: str, failed_attempts: int, locked_until: datetime | None) -> BusinessAccessLinkRecord:
        with self._lock:  # type: ignore[attr-defined]
            link = self.access_links[link_id]  # type: ignore[attr-defined]
            link.business_pin_failed_attempts = failed_attempts
            link.business_pin_locked_until = locked_until
            link.business_pin_unlocked_until = None
            link.updated_at = utc_now()
            return link

    def lock_access_link_pin(self, *, link_id: str) -> BusinessAccessLinkRecord:
        with self._lock:  # type: ignore[attr-defined]
            link = self.access_links[link_id]  # type: ignore[attr-defined]
            link.business_pin_unlocked_until = None
            link.updated_at = utc_now()
            return link
