from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.errors import ApiError
from app.modules.businesses.access_link_service import BusinessAccessLinkServiceMixin
from app.modules.businesses.access_control import require_active_business_access
from app.modules.businesses.admin_review_service import BusinessAdminReviewServiceMixin
from app.modules.businesses.models import BusinessRecord
from app.modules.businesses.presenters import business_payload, payment_method_display
from app.modules.users.models import UserRecord


class BusinessService(BusinessAccessLinkServiceMixin, BusinessAdminReviewServiceMixin):
    def __init__(self, *, settings: Settings, repository, user_repository, audit_writer, rate_limiter, idempotency_store, storage) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._users = user_repository
        self._audit = audit_writer
        self._rate_limiter = rate_limiter
        self._idempotency = idempotency_store
        self._storage = storage

    def _rate_limit(self, action: str, user: UserRecord) -> None:
        key = f"business:{action}:{user.id}"
        if not self._rate_limiter.allow(
            key,
            max_attempts=self._settings.business_rate_limit_max_attempts,
            window_seconds=self._settings.business_rate_limit_window_seconds,
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def _business_or_404(self, business_id: str) -> BusinessRecord:
        business = self._repository.get_business(business_id)
        if business is None:
            raise ApiError("BUSINESS_NOT_FOUND", status_code=404)
        return business

    def my_business(self, *, user: UserRecord) -> dict[str, Any]:
        business = self._repository.get_active_business_for_owner(user.id)
        return {"business": business_payload(business) if business else None}

    def own_payment_methods(self, *, user: UserRecord) -> list[dict[str, Any]]:
        self._rate_limit("payment_methods", user)
        business, _ = require_active_business_access(user=user, business_repository=self._repository)
        methods = [
            method
            for method in self._repository.list_payment_methods_for_business(business.id)
            if method.verified_status == "approved" and method.active
        ]
        return [payment_method_display(method, business=business) for method in methods]

