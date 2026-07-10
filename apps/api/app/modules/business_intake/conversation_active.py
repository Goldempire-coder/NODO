from __future__ import annotations

from typing import Any

from app.modules.business_intake.models import BusinessIntakeRequestRecord


class BusinessIntakeActiveMessageMixin:
    async def _handle_active_intake_message(
        self,
        *,
        intake: BusinessIntakeRequestRecord,
        message: dict[str, Any],
        update_id: int,
        chat_id: int,
        telegram_user_id: int,
        text: str | None,
        bot_token: str,
        request_id: str,
    ) -> dict[str, Any]:
        self._validate_intake_context(intake=intake, telegram_user_id=telegram_user_id, telegram_chat_id=chat_id)  # type: ignore[attr-defined]
        early_response = await self._closed_or_duplicate_intake_response(intake=intake, update_id=update_id, bot_token=bot_token, chat_id=chat_id)
        if early_response is not None:
            return early_response
        return await self._route_active_intake_message(
            intake=intake,
            message=message,
            update_id=update_id,
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            text=text,
            bot_token=bot_token,
            request_id=request_id,
        )  # type: ignore[attr-defined]

    async def _closed_or_duplicate_intake_response(self, *, intake: BusinessIntakeRequestRecord, update_id: int, bot_token: str, chat_id: int) -> dict[str, Any] | None:
        if intake.last_update_id is not None and update_id <= intake.last_update_id:
            return self._telegram_response(intake, duplicate_update=True)  # type: ignore[attr-defined]
        if intake.status != "draft":
            await self._send_final_confirmation(bot_token=bot_token, chat_id=chat_id)  # type: ignore[attr-defined]
            return self._telegram_response(intake)  # type: ignore[attr-defined]
        return None
