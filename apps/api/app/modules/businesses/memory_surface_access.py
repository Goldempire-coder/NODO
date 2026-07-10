from __future__ import annotations

from app.modules.businesses.models import BusinessAccessLinkRecord, BusinessRecord


class InMemoryBusinessSurfaceAccessMixin:
    def get_business_with_latest_access_link_for_owner(self, owner_user_id: str) -> tuple[BusinessRecord | None, BusinessAccessLinkRecord | None]:
        business = self.get_active_business_for_owner(owner_user_id)  # type: ignore[attr-defined]
        if business is None:
            return None, None
        return business, self.get_access_link_for_business_user(business_id=business.id, user_id=owner_user_id)  # type: ignore[attr-defined]
