from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.business_intake.conversation_validation import clean_text
from app.modules.business_intake.models import BusinessIntakeRequestRecord


class BusinessIntakeContactStepMixin:
    async def _handle_contact_step(
        self,
        *,
        intake: BusinessIntakeRequestRecord,
        update_id: int,
        message: dict[str, Any],
        telegram_user_id: int,
        bot_token: str,
        chat_id: int,
        request_id: str,
    ) -> dict[str, Any]:
        contact = message.get("contact")
        if not isinstance(contact, dict):
            raise ApiError("BOT_CONTACT_REQUIRED", status_code=400)
        contact_user_id = contact.get("user_id")
        try:
            contact_user_id_int = int(contact_user_id)
        except (TypeError, ValueError) as exc:
            raise ApiError("BOT_CONTACT_REQUIRED", status_code=400) from exc
        if contact_user_id_int != telegram_user_id:
            raise ApiError("BOT_CONTACT_REQUIRED", status_code=400)
        contact_phone = clean_text(contact.get("phone_number"), min_length=6, max_length=32)
        updated = self._repository.save_contact(intake=intake, update_id=update_id, contact_phone=contact_phone)  # type: ignore[attr-defined]
        self._write_audit(event_type="business_intake_contact_shared", intake=updated, request_id=request_id)  # type: ignore[attr-defined]
        await self._send_prompt(bot_token=bot_token, chat_id=chat_id, step=updated.last_step)  # type: ignore[attr-defined]
        return self._telegram_response(updated)  # type: ignore[attr-defined]
