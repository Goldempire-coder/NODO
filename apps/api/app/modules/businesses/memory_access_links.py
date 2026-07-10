from __future__ import annotations

from app.core.errors import ApiError
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
            existing = self.get_active_access_link_for_business_user(business_id=business_id, user_id=user_id)
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
        links.sort(key=lambda item: item.updated_at, reverse=True)
        return links[0]

    def get_active_access_link_for_business_user(
        self,
        *,
        business_id: str,
        user_id: str,
    ) -> BusinessAccessLinkRecord | None:
        link = self.get_access_link_for_business_user(business_id=business_id, user_id=user_id)
        return link if link is not None and link.status == "active" else None

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
            link.status = status
            link.reason = reason
            link.updated_at = now
            if status == "active":
                link.suspended_at = None
                link.blocked_at = None
                link.revoked_at = None
            elif status == "suspended":
                link.suspended_at = now
            elif status == "blocked":
                link.blocked_at = now
            elif status == "revoked":
                link.revoked_at = now
            return link
