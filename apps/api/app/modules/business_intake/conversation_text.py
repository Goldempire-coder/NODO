from __future__ import annotations

from typing import Any

from app.modules.business_intake.conversation_prompts import START_BUTTON_TEXTS
from app.modules.business_intake.conversation_steps import conversation_fields_for_step
from app.modules.business_intake.conversation_submit import ensure_ready_to_submit, ensure_submit_command
from app.modules.business_intake.conversation_validation import clean_text
from app.modules.business_intake.models import BusinessIntakeRequestRecord


class BusinessIntakeTextStepsMixin:
    async def _handle_text_step(
        self,
        *,
        intake: BusinessIntakeRequestRecord,
        update_id: int,
        text: str,
        bot_token: str,
        chat_id: int,
        request_id: str,
    ) -> dict[str, Any]:
        current_step = intake.last_step
        cleaned = clean_text(text)
        if cleaned.lower() in START_BUTTON_TEXTS:
            await self._send_prompt(bot_token=bot_token, chat_id=chat_id, step="awaiting_referral_code")
            return self._telegram_response(intake, duplicate_update=True)

        if current_step == "awaiting_documents":
            return await self._handle_submit_text(
                intake=intake,
                update_id=update_id,
                cleaned=cleaned,
                bot_token=bot_token,
                chat_id=chat_id,
                request_id=request_id,
            )

        fields, next_step = conversation_fields_for_step(intake=intake, current_step=current_step, cleaned=cleaned, raw_text=text)
        updated = self._repository.update_conversation(  # type: ignore[attr-defined]
            intake=intake,
            update_id=update_id,
            last_step=next_step,
            fields=fields,
        )
        self._write_audit(  # type: ignore[attr-defined]
            event_type="business_intake_step_answered",
            intake=updated,
            request_id=request_id,
            metadata={"step": current_step, "next_step": next_step},
        )
        await self._send_prompt(bot_token=bot_token, chat_id=chat_id, step=next_step)
        return self._telegram_response(updated)

    async def _handle_submit_text(
        self,
        *,
        intake: BusinessIntakeRequestRecord,
        update_id: int,
        cleaned: str,
        bot_token: str,
        chat_id: int,
        request_id: str,
    ) -> dict[str, Any]:
        ensure_submit_command(cleaned)
        ensure_ready_to_submit(intake, list_documents=self._repository.list_documents)  # type: ignore[attr-defined]
        updated = self._repository.update_conversation(  # type: ignore[attr-defined]
            intake=intake,
            update_id=update_id,
            last_step="submitted",
            fields={"status": "submitted", "submitted_at": True},
        )
        self._write_audit(event_type="business_intake_submitted", intake=updated, request_id=request_id)  # type: ignore[attr-defined]
        await self._send_final_confirmation(bot_token=bot_token, chat_id=chat_id)
        return self._telegram_response(updated)
