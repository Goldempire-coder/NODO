from __future__ import annotations

from typing import Any

from app.modules.business_intake.models import BusinessIntakeRequestRecord


class BusinessIntakeStartMixin:
    def _create_started_draft(self, *, telegram_user_id: int, chat_id: int, update_id: int, request_id: str) -> BusinessIntakeRequestRecord:
        intake = self._repository.create_or_get_draft(  # type: ignore[attr-defined]
            telegram_user_id=telegram_user_id,
            telegram_chat_id=chat_id,
            update_id=update_id,
            referral_code=None,
        )
        self._ensure_applicant_user(telegram_user_id)  # type: ignore[attr-defined]
        self._write_audit(event_type="business_intake_started", intake=intake, request_id=request_id)  # type: ignore[attr-defined]
        return intake

    async def _handle_start_update(self, *, bot_token: str, chat_id: int, telegram_user_id: int, update_id: int, request_id: str) -> dict[str, Any]:
        latest = self._repository.get_latest_for_chat(telegram_chat_id=chat_id)  # type: ignore[attr-defined]
        if latest is not None:
            self._validate_intake_context(intake=latest, telegram_user_id=telegram_user_id, telegram_chat_id=chat_id)  # type: ignore[attr-defined]
            if latest.status != "draft":
                await self._send_final_confirmation(bot_token=bot_token, chat_id=chat_id)  # type: ignore[attr-defined]
                return self._telegram_response(latest, duplicate_update=latest.last_update_id == update_id)  # type: ignore[attr-defined]
            if latest.last_update_id is not None and update_id <= latest.last_update_id:
                return self._telegram_response(latest, duplicate_update=True)  # type: ignore[attr-defined]

        intake = self._create_started_draft(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            update_id=update_id,
            request_id=request_id,
        )
        await self._send_prompt(bot_token=bot_token, chat_id=chat_id, step="awaiting_referral_code")  # type: ignore[attr-defined]
        return self._telegram_response(intake)  # type: ignore[attr-defined]

    async def _get_or_start_active_intake(
        self,
        *,
        bot_token: str,
        chat_id: int,
        telegram_user_id: int,
        update_id: int,
        request_id: str,
    ) -> tuple[BusinessIntakeRequestRecord, dict[str, Any] | None]:
        intake = self._repository.get_active_for_chat(telegram_chat_id=chat_id)  # type: ignore[attr-defined]
        if intake is not None:
            return intake, None

        latest = self._repository.get_latest_for_chat(telegram_chat_id=chat_id)  # type: ignore[attr-defined]
        if latest is not None:
            self._validate_intake_context(intake=latest, telegram_user_id=telegram_user_id, telegram_chat_id=chat_id)  # type: ignore[attr-defined]
            await self._send_final_confirmation(bot_token=bot_token, chat_id=chat_id)  # type: ignore[attr-defined]
            return latest, self._telegram_response(latest, duplicate_update=latest.last_update_id == update_id)  # type: ignore[attr-defined]

        started = self._create_started_draft(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            update_id=update_id,
            request_id=request_id,
        )
        await self._send_prompt(bot_token=bot_token, chat_id=chat_id, step="awaiting_referral_code")  # type: ignore[attr-defined]
        return started, self._telegram_response(started)  # type: ignore[attr-defined]
