from __future__ import annotations

from threading import RLock

from app.core.errors import ApiError
from app.modules.businesses.memory_access_links import InMemoryBusinessAccessLinksMixin
from app.modules.businesses.memory_admin_review import InMemoryBusinessAdminReviewMixin
from app.modules.businesses.memory_founder import InMemoryBusinessFounderMixin
from app.modules.businesses.memory_marketplace import InMemoryBusinessMarketplaceMixin
from app.modules.businesses.memory_payment_methods import InMemoryBusinessPaymentMethodsMixin
from app.modules.businesses.memory_surface_access import InMemoryBusinessSurfaceAccessMixin
from app.modules.businesses.memory_verification_assets import InMemoryBusinessVerificationAssetsMixin
from app.modules.businesses.models import (
    BusinessAccessLinkRecord,
    BusinessPaymentMethodRecord,
    BusinessRecord,
    BusinessVerificationSubmissionRecord,
    FileAssetRecord,
    utc_now,
    new_id,
)

class InMemoryBusinessRepository(
    InMemoryBusinessAccessLinksMixin,
    InMemoryBusinessAdminReviewMixin,
    InMemoryBusinessFounderMixin,
    InMemoryBusinessMarketplaceMixin,
    InMemoryBusinessPaymentMethodsMixin,
    InMemoryBusinessSurfaceAccessMixin,
    InMemoryBusinessVerificationAssetsMixin,
):
    def __init__(self) -> None:
        self._lock = RLock()
        self.businesses: dict[str, BusinessRecord] = {}
        self.submissions: dict[str, BusinessVerificationSubmissionRecord] = {}
        self.payment_methods: dict[str, BusinessPaymentMethodRecord] = {}
        self.access_links: dict[str, BusinessAccessLinkRecord] = {}
        self.files: dict[str, FileAssetRecord] = {}

    def create_business(self, *, owner_user_id: str, business_name: str, rif: str | None, address: str | None, phone: str | None, country: str) -> BusinessRecord:
        with self._lock:
            if self.get_active_business_for_owner(owner_user_id) is not None:
                raise ApiError("BUSINESS_ALREADY_EXISTS", status_code=409)
            now = utc_now()
            business = BusinessRecord(
                id=new_id(),
                owner_user_id=owner_user_id,
                business_name=business_name,
                rif=rif,
                address=address,
                phone=phone,
                country=country,
                created_at=now,
                updated_at=now,
            )
            self.businesses[business.id] = business
            return business

    def update_business(self, business: BusinessRecord, fields: dict[str, str | None]) -> BusinessRecord:
        with self._lock:
            for key, value in fields.items():
                if value is not None:
                    setattr(business, key, value)
            business.updated_at = utc_now()
            return business

    def get_business(self, business_id: str) -> BusinessRecord | None:
        return self.businesses.get(business_id)

    def get_businesses_by_ids(self, business_ids: set[str]) -> dict[str, BusinessRecord]:
        return {business_id: self.businesses[business_id] for business_id in business_ids if business_id in self.businesses}

    def get_active_business_for_owner(self, owner_user_id: str) -> BusinessRecord | None:
        for business in self.businesses.values():
            if business.owner_user_id == owner_user_id:
                return business
        return None

    def list_pending_businesses(self, *, cursor: str | None, limit: int) -> tuple[list[BusinessRecord], str | None]:
        items = sorted(
            [business for business in self.businesses.values() if business.verification_status == "pending"],
            key=lambda business: business.created_at,
            reverse=True,
        )
        if cursor:
            items = [business for business in items if business.created_at.isoformat() < cursor]
        page = items[:limit]
        next_cursor = page[-1].created_at.isoformat() if len(page) == limit else None
        return page, next_cursor


