from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.business_intake.models import BusinessIntakeRequestRecord


class BusinessIntakeConversationContextMixin:
    def _rate_limit(self, action: str, key: str) -> None:
        if not self._rate_limiter.allow(  # type: ignore[attr-defined]
            f"business_intake:{action}:{key}",
            max_attempts=self._settings.business_rate_limit_max_attempts,  # type: ignore[attr-defined]
            window_seconds=self._settings.business_rate_limit_window_seconds,  # type: ignore[attr-defined]
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def _ensure_applicant_user(self, telegram_user_id: int):
        user = self._users.get_user_by_telegram_id(telegram_user_id)  # type: ignore[attr-defined]
        if user is not None:
            return user
        user, _ = self._users.upsert_telegram_user(  # type: ignore[attr-defined]
            telegram_id=telegram_user_id,
            username=None,
            first_name=None,
            last_name=None,
        )
        return user

    def _validate_intake_context(
        self,
        *,
        intake: BusinessIntakeRequestRecord,
        telegram_user_id: int,
        telegram_chat_id: int,
    ) -> None:
        if intake.telegram_user_id != telegram_user_id or intake.telegram_chat_id != telegram_chat_id:
            raise ApiError("BUSINESS_INTAKE_NOT_FOUND", status_code=404)

    def _write_audit(
        self,
        *,
        event_type: str,
        intake: BusinessIntakeRequestRecord,
        request_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._audit.write(  # type: ignore[attr-defined]
            event_type=event_type,
            actor_user_id=None,
            actor_role="business_intake_bot",
            resource_type="business_intake",
            resource_id=intake.id,
            request_id=request_id,
            metadata_json=metadata or {},
        )

    def _telegram_response(
        self,
        intake: BusinessIntakeRequestRecord,
        *,
        duplicate_update: bool = False,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "intake_id": intake.id,
            "status": intake.status,
            "last_step": intake.last_step,
            "duplicate_update": duplicate_update,
        }
