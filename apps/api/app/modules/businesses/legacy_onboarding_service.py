from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.errors import ApiError
from app.modules.businesses.legacy_documents import LegacyBusinessDocumentMixin
from app.modules.businesses.legacy_submission import LegacyBusinessSubmissionMixin
from app.modules.businesses.policy import require_business_owner, require_owner_or_eligible
from app.modules.businesses.presenters import business_payload
from app.modules.businesses.schemas import BusinessCreateRequest, BusinessUpdateRequest
from app.modules.businesses.state_machine import require_owner_update_allowed
from app.modules.users.models import UserRecord


class LegacyBusinessOnboardingService(LegacyBusinessDocumentMixin, LegacyBusinessSubmissionMixin):
    """Test-fixture only owner onboarding kept outside the production business service."""

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

    def _business_or_404(self, business_id: str):
        business = self._repository.get_business(business_id)
        if business is None:
            raise ApiError("BUSINESS_NOT_FOUND", status_code=404)
        return business

    def create_business(self, *, user: UserRecord, payload: BusinessCreateRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        require_owner_or_eligible(user)
        self._rate_limit("create", user)

        def compute() -> dict[str, Any]:
            business = self._repository.create_business(
                owner_user_id=user.id,
                business_name=payload.business_name,
                rif=payload.rif,
                address=payload.address,
                phone=payload.phone,
                country=payload.country,
            )
            if user.role != "business_owner":
                self._users.set_user_role(user.id, "business_owner")
                user.role = "business_owner"
            self._audit.write(
                event_type="business_created",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="business",
                resource_id=business.id,
                request_id=request_id,
            )
            return {"business": business_payload(business)}

        return self._idempotency.replay_or_store(idempotency_key, payload=payload.model_dump(), compute=compute)

    def update_business(self, *, user: UserRecord, business_id: str, payload: BusinessUpdateRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        self._rate_limit("update", user)
        business = self._business_or_404(business_id)
        require_business_owner(user, business)
        require_owner_update_allowed(business)

        def compute() -> dict[str, Any]:
            updated = self._repository.update_business(
                business,
                {
                    "business_name": payload.business_name,
                    "rif": payload.rif,
                    "address": payload.address,
                    "phone": payload.phone,
                    "country": payload.country,
                },
            )
            self._audit.write(
                event_type="business_updated",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="business",
                resource_id=updated.id,
                request_id=request_id,
            )
            return {"business": business_payload(updated)}

        return self._idempotency.replay_or_store(idempotency_key, payload={"id": business_id, **payload.model_dump()}, compute=compute)
