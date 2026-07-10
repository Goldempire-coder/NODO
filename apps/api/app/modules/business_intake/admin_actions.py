from __future__ import annotations

from typing import Any, Callable

from app.core.errors import ApiError
from app.modules.business_intake.admin_delete import BusinessIntakeAdminDeleteMixin
from app.modules.business_intake.admin_review import BusinessIntakeAdminReviewMixin
from app.modules.business_intake.business_creation import BusinessIntakeBusinessCreationMixin
from app.modules.business_intake.models import BusinessIntakeRequestRecord
from app.modules.business_intake.policy import require_admin_read
from app.modules.users.models import UserRecord


class BusinessIntakeAdminActions(
    BusinessIntakeAdminReviewMixin,
    BusinessIntakeAdminDeleteMixin,
    BusinessIntakeBusinessCreationMixin,
):
    def __init__(
        self,
        *,
        settings,
        repository,
        business_repository,
        user_repository,
        audit_writer,
        rate_limiter,
        idempotency_store,
        public_intake: Callable[[BusinessIntakeRequestRecord], dict[str, Any]],
        public_document: Callable[[Any], dict[str, Any]],
    ) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._businesses = business_repository
        self._users = user_repository
        self._audit = audit_writer
        self._rate_limiter = rate_limiter
        self._idempotency = idempotency_store
        self._public_intake = public_intake
        self._public_document = public_document

    def _rate_limit(self, action: str, key: str) -> None:
        if not self._rate_limiter.allow(
            f"business_intake:{action}:{key}",
            max_attempts=self._settings.business_rate_limit_max_attempts,
            window_seconds=self._settings.business_rate_limit_window_seconds,
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def _get_intake(self, intake_id: str) -> BusinessIntakeRequestRecord:
        intake = self._repository.get(intake_id)
        if intake is None:
            raise ApiError("BUSINESS_INTAKE_NOT_FOUND", status_code=404)
        return intake

    def _ensure_applicant_user(self, telegram_user_id: int) -> UserRecord:
        user = self._users.get_user_by_telegram_id(telegram_user_id)
        if user is not None:
            return user
        user, _ = self._users.upsert_telegram_user(
            telegram_id=telegram_user_id,
            username=None,
            first_name=None,
            last_name=None,
        )
        return user

    def _write_admin_audit(
        self,
        *,
        event_type: str,
        user: UserRecord,
        intake: BusinessIntakeRequestRecord,
        request_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._audit.write(
            event_type=event_type,
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="business_intake",
            resource_id=intake.id,
            request_id=request_id,
            metadata_json=metadata or {},
        )

    def list(self, *, user: UserRecord, status: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("admin_list", user.id)
        items, next_cursor = self._repository.list_intakes(status=status, cursor=cursor, limit=limit)
        return {"items": [self._public_intake(item) for item in items], "next_cursor": next_cursor}

    def detail(self, *, user: UserRecord, intake_id: str, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("admin_detail", user.id)
        intake = self._get_intake(intake_id)
        documents = self._repository.list_documents(intake.id)
        self._write_admin_audit(event_type="business_intake_viewed_by_admin", user=user, intake=intake, request_id=request_id)
        return {"intake": self._public_intake(intake), "documents": [self._public_document(doc) for doc in documents]}
