from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import ApiError
from app.modules.business_intake.admin_actions import BusinessIntakeAdminActions
from app.modules.business_intake import conversation as conversation_module
from app.modules.business_intake.conversation import (
    BusinessIntakeConversation,
    telegram_download_file,
    telegram_send_message,
    telegram_set_chat_menu_button,
)
from app.modules.business_intake.models import (
    BusinessIntakeRequestRecord,
)
from app.modules.business_intake.presenters import public_business_intake_document, public_intake_payload
from app.modules.business_intake.public_actions import BusinessIntakePublicActionsMixin
from app.modules.business_intake.schemas import (
    AdminBusinessIntakeDeleteRequest,
    AdminBusinessIntakeReviewRequest,
)
from app.modules.users.models import UserRecord


def _require_uuid(value: str, code: str = "BUSINESS_INTAKE_NOT_FOUND") -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError) as exc:
        raise ApiError(code, status_code=404) from exc


class BusinessIntakeService(BusinessIntakePublicActionsMixin):
    def __init__(self, *, settings, repository, business_repository, user_repository, audit_writer, rate_limiter, idempotency_store, storage) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._businesses = business_repository
        self._users = user_repository
        self._audit = audit_writer
        self._rate_limiter = rate_limiter
        self._idempotency = idempotency_store
        self._storage = storage
        self._conversation = BusinessIntakeConversation(
            settings=settings,
            repository=repository,
            business_repository=business_repository,
            user_repository=user_repository,
            audit_writer=audit_writer,
            rate_limiter=rate_limiter,
            storage=storage,
        )
        self._admin_actions = BusinessIntakeAdminActions(
            settings=settings,
            repository=repository,
            business_repository=business_repository,
            user_repository=user_repository,
            audit_writer=audit_writer,
            rate_limiter=rate_limiter,
            idempotency_store=idempotency_store,
            public_intake=lambda intake: self._public_intake(intake, admin=True),
            public_document=self._public_document,
        )

    def _rate_limit(self, action: str, key: str) -> None:
        if not self._rate_limiter.allow(
            f"business_intake:{action}:{key}",
            max_attempts=self._settings.business_rate_limit_max_attempts,
            window_seconds=self._settings.business_rate_limit_window_seconds,
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

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

    def _get_intake(self, intake_id: str) -> BusinessIntakeRequestRecord:
        intake_id = _require_uuid(intake_id)
        intake = self._repository.get(intake_id)
        if intake is None:
            raise ApiError("BUSINESS_INTAKE_NOT_FOUND", status_code=404)
        return intake

    def _validate_intake_context(self, *, intake: BusinessIntakeRequestRecord, telegram_user_id: int, telegram_chat_id: int) -> None:
        if intake.telegram_user_id != telegram_user_id or intake.telegram_chat_id != telegram_chat_id:
            raise ApiError("BUSINESS_INTAKE_NOT_FOUND", status_code=404)

    def _write_audit(self, *, event_type: str, intake: BusinessIntakeRequestRecord, request_id: str, metadata: dict[str, Any] | None = None) -> None:
        self._audit.write(
            event_type=event_type,
            actor_user_id=None,
            actor_role="business_intake_bot",
            resource_type="business_intake",
            resource_id=intake.id,
            request_id=request_id,
            metadata_json=metadata or {},
        )

    async def process_telegram_update(self, *, update: dict[str, Any], bot_token: str | None, request_id: str) -> dict[str, Any]:
        conversation_module.telegram_send_message = telegram_send_message
        conversation_module.telegram_download_file = telegram_download_file
        conversation_module.telegram_set_chat_menu_button = telegram_set_chat_menu_button
        return await self._conversation.process_telegram_update(update=update, bot_token=bot_token, request_id=request_id)

    def _public_intake(self, intake: BusinessIntakeRequestRecord, *, admin: bool = False) -> dict[str, Any]:
        return public_intake_payload(intake, admin=admin)

    def _public_document(self, document) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        return public_business_intake_document(document)

    def admin_list(self, *, user: UserRecord, status: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        return self._admin_actions.list(user=user, status=status, cursor=cursor, limit=limit, request_id=request_id)

    def admin_detail(self, *, user: UserRecord, intake_id: str, request_id: str) -> dict[str, Any]:
        return self._admin_actions.detail(user=user, intake_id=intake_id, request_id=request_id)

    def admin_accept(self, *, user: UserRecord, intake_id: str, payload: AdminBusinessIntakeReviewRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._admin_actions.accept(user=user, intake_id=intake_id, payload=payload, request_id=request_id, idempotency_key=idempotency_key)

    def admin_reject(self, *, user: UserRecord, intake_id: str, payload: AdminBusinessIntakeReviewRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._admin_actions.reject(user=user, intake_id=intake_id, payload=payload, request_id=request_id, idempotency_key=idempotency_key)

    def admin_delete(self, *, user: UserRecord, intake_id: str, payload: AdminBusinessIntakeDeleteRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._admin_actions.delete(user=user, intake_id=intake_id, payload=payload, request_id=request_id, idempotency_key=idempotency_key)
