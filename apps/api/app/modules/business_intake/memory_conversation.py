from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.business_intake.models import INTAKE_STEPS, BusinessIntakeRequestRecord, new_id, utc_now
from app.modules.business_intake.repository_common import decimal_text


class InMemoryBusinessIntakeConversationMixin:
    def get_by_update(self, *, telegram_chat_id: int, update_id: int) -> BusinessIntakeRequestRecord | None:
        for intake in self.intakes.values():  # type: ignore[attr-defined]
            if intake.telegram_chat_id == telegram_chat_id and intake.last_update_id == update_id:
                return intake
        return None

    def get_active_for_chat(self, *, telegram_chat_id: int) -> BusinessIntakeRequestRecord | None:
        candidates = [
            intake
            for intake in self.intakes.values()  # type: ignore[attr-defined]
            if intake.telegram_chat_id == telegram_chat_id and intake.status == "draft"
        ]
        return max(candidates, key=lambda item: item.updated_at, default=None)

    def get_latest_for_chat(self, *, telegram_chat_id: int) -> BusinessIntakeRequestRecord | None:
        candidates = [
            intake
            for intake in self.intakes.values()  # type: ignore[attr-defined]
            if intake.telegram_chat_id == telegram_chat_id
        ]
        return max(candidates, key=lambda item: item.updated_at, default=None)

    def create_or_get_draft(
        self,
        *,
        telegram_user_id: int,
        telegram_chat_id: int,
        update_id: int,
        referral_code: str | None,
    ) -> BusinessIntakeRequestRecord:
        with self._lock:  # type: ignore[attr-defined]
            existing_update = self.get_by_update(telegram_chat_id=telegram_chat_id, update_id=update_id)
            if existing_update is not None:
                return existing_update
            existing = self.get_active_for_chat(telegram_chat_id=telegram_chat_id)
            if existing is not None:
                existing.last_update_id = update_id
                existing.last_step = "awaiting_referral_code"
                existing.updated_at = utc_now()
                return existing
            now = utc_now()
            intake = BusinessIntakeRequestRecord(
                id=new_id(),
                telegram_user_id=telegram_user_id,
                telegram_chat_id=telegram_chat_id,
                referral_code=referral_code,
                last_step="awaiting_referral_code",
                last_update_id=update_id,
                created_at=now,
                updated_at=now,
            )
            self.intakes[intake.id] = intake  # type: ignore[attr-defined]
            return intake

    def save_contact(
        self,
        *,
        intake: BusinessIntakeRequestRecord,
        update_id: int,
        contact_phone: str,
    ) -> BusinessIntakeRequestRecord:
        with self._lock:  # type: ignore[attr-defined]
            intake.contact_phone = contact_phone
            intake.last_update_id = update_id
            intake.last_step = "awaiting_business_name"
            intake.updated_at = utc_now()
            return intake

    def update_conversation(
        self,
        *,
        intake: BusinessIntakeRequestRecord,
        update_id: int,
        last_step: str,
        fields: dict[str, Any],
    ) -> BusinessIntakeRequestRecord:
        if last_step not in INTAKE_STEPS:
            raise ApiError("BOT_INPUT_INVALID", status_code=400)
        with self._lock:  # type: ignore[attr-defined]
            for key, value in fields.items():
                if not hasattr(intake, key):
                    raise ApiError("BOT_INPUT_INVALID", status_code=400)
                if key == "submitted_at" and value is True:
                    setattr(intake, key, utc_now())
                elif key in {"min_amount_usd", "max_amount_usd", "daily_limit_usd"}:
                    setattr(intake, key, decimal_text(value))
                else:
                    setattr(intake, key, value)
            intake.last_update_id = update_id
            intake.last_step = last_step
            intake.updated_at = utc_now()
            return intake

    def mark_update_processed(
        self,
        *,
        intake: BusinessIntakeRequestRecord,
        update_id: int,
        last_step: str,
    ) -> BusinessIntakeRequestRecord:
        with self._lock:  # type: ignore[attr-defined]
            intake.last_update_id = update_id
            intake.last_step = last_step
            intake.updated_at = utc_now()
            return intake
