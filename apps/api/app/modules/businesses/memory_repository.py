from __future__ import annotations

from datetime import datetime, timedelta
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
        self._publication_hold_repository = None
        self.businesses: dict[str, BusinessRecord] = {}
        self.submissions: dict[str, BusinessVerificationSubmissionRecord] = {}
        self.payment_methods: dict[str, BusinessPaymentMethodRecord] = {}
        self.access_links: dict[str, BusinessAccessLinkRecord] = {}
        self.files: dict[str, FileAssetRecord] = {}

    def bind_publication_hold_repository(self, publication_hold_repository) -> None:  # type: ignore[no-untyped-def]
        self._publication_hold_repository = publication_hold_repository

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

    def update_business_accepting_orders(self, business_id: str, accepting_orders: bool) -> BusinessRecord | None:
        with self._lock:
            business = self.businesses.get(business_id)
            if business is None:
                return None
            business.is_accepting_orders = accepting_orders
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

    def publish_due_public_reputation_snapshots(
        self,
        *,
        current_time: datetime,
        limit: int,
        minimum_ratings: int = 5,
        publication_interval: timedelta = timedelta(hours=24),
        dry_run: bool = False,
    ) -> list[str]:
        with self._lock:
            candidates = []
            for business in self.businesses.values():
                if (
                    business.ratings_count < minimum_ratings
                    or business.rating_avg is None
                    or business.reputation_calculated_at is None
                ):
                    continue
                unpublished = business.public_reputation_published_at is None
                due = unpublished or business.public_reputation_published_at <= current_time - publication_interval
                source_is_old_enough = business.reputation_calculated_at <= current_time - publication_interval
                changed = (
                    business.public_reputation_source_calculated_at is None
                    or business.reputation_calculated_at > business.public_reputation_source_calculated_at
                )
                if due and source_is_old_enough and changed:
                    candidates.append(business)
            candidates.sort(
                key=lambda item: item.public_reputation_published_at or item.created_at
            )
            selected = candidates[:limit]
            if not dry_run:
                for business in selected:
                    business.public_reputation_rating_avg = business.rating_avg
                    business.public_reputation_ratings_count = business.ratings_count
                    business.public_reputation_tier = business.reputation_tier
                    business.public_reputation_published_at = current_time
                    business.public_reputation_source_calculated_at = business.reputation_calculated_at
            return [business.id for business in selected]

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


