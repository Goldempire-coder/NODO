from __future__ import annotations

from app.modules.businesses.models import BusinessAccessLinkRecord, BusinessRecord


class InMemoryBusinessSurfaceAccessMixin:
    def get_business_with_latest_access_link_for_owner(self, owner_user_id: str) -> tuple[BusinessRecord | None, BusinessAccessLinkRecord | None]:
        candidates: list[tuple[BusinessRecord, BusinessAccessLinkRecord]] = []
        for link in getattr(self, "access_links", {}).values():
            if link.user_id != owner_user_id or link.status != "active":
                continue
            business = getattr(self, "businesses", {}).get(link.business_id)
            if business is None:
                continue
            if business.owner_user_id == owner_user_id and business.verification_status == "approved":
                candidates.append((business, link))
        if candidates:
            candidates.sort(key=lambda item: (item[1].updated_at, item[0].created_at), reverse=True)
            return candidates[0]

        business = self.get_active_business_for_owner(owner_user_id)  # type: ignore[attr-defined]
        if business is None:
            return None, None
        return business, self.get_access_link_for_business_user(business_id=business.id, user_id=owner_user_id)  # type: ignore[attr-defined]
