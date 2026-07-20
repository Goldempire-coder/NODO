from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.business_intake.conversation_context import BusinessIntakeConversationContextMixin
from app.modules.business_intake.conversation_prompts import (
    REMOVE_REPLY_MARKUP,
    START_BUTTON_TEXTS,
    START_REPLY_MARKUP,
    STEP_PROMPTS,
)
from app.modules.business_intake.conversation_active import BusinessIntakeActiveMessageMixin
from app.modules.business_intake.conversation_contact import BusinessIntakeContactStepMixin
from app.modules.business_intake.conversation_router import route_active_intake_message
from app.modules.business_intake.conversation_start import BusinessIntakeStartMixin
from app.modules.business_intake.conversation_text import BusinessIntakeTextStepsMixin
from app.modules.business_intake.business_creation import BUSINESS_APPROVAL_BUTTON_TEXT, BUSINESS_MENU_BUTTON_TEXT
from app.modules.business_intake.models import (
    INTAKE_FINAL_CONFIRMATION,
    BusinessIntakeRequestRecord,
)
from app.modules.business_intake.telegram_client import telegram_download_file, telegram_send_message, telegram_set_chat_menu_button
from app.modules.business_intake.telegram_update_parser import empty_telegram_response, telegram_message_context

INTAKE_CONFIRMATION = INTAKE_FINAL_CONFIRMATION
BUSINESS_OPEN_MESSAGE = "Ya tienes acceso a NODO Negocio.\n\nToca el boton para abrir la Mini App."



class BusinessIntakeConversation(
    BusinessIntakeConversationContextMixin,
    BusinessIntakeStartMixin,
    BusinessIntakeActiveMessageMixin,
    BusinessIntakeContactStepMixin,
    BusinessIntakeTextStepsMixin,
):
    def __init__(self, *, settings, repository, business_repository, user_repository, audit_writer, rate_limiter, storage, admin_notifications=None) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._businesses = business_repository
        self._users = user_repository
        self._audit = audit_writer
        self._rate_limiter = rate_limiter
        self._storage = storage
        self._admin_notifications = admin_notifications

    async def process_telegram_update(self, *, update: dict[str, Any], bot_token: str | None, request_id: str) -> dict[str, Any]:
        if not bot_token:
            raise ApiError("TELEGRAM_BOT_NOT_CONFIGURED", status_code=503)

        context = telegram_message_context(update)
        if context is None:
            return empty_telegram_response()
        return await self._process_message_context(context=context, bot_token=bot_token, request_id=request_id)

    async def _process_message_context(self, *, context: dict[str, Any], bot_token: str, request_id: str) -> dict[str, Any]:
        message = context["message"]
        update_id = context["update_id"]
        chat_id = context["chat_id"]
        telegram_user_id = context["telegram_user_id"]
        text = context["text"]
        normalized_text = context["normalized_text"]

        self._rate_limit("telegram_webhook", str(telegram_user_id))
        existing_update = self._repository.get_by_update(telegram_chat_id=chat_id, update_id=update_id)
        if existing_update is not None:
            return self._telegram_response(existing_update, duplicate_update=True)

        if isinstance(text, str) and (normalized_text.startswith("/start") or normalized_text in START_BUTTON_TEXTS):
            return await self._handle_start_update(
                bot_token=bot_token,
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                update_id=update_id,
                request_id=request_id,
            )

        intake, early_response = await self._get_or_start_active_intake(
            bot_token=bot_token,
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            update_id=update_id,
            request_id=request_id,
        )
        if early_response is not None:
            return early_response

        return await self._handle_active_intake_message(
            intake=intake,
            message=message,
            update_id=update_id,
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            text=text,
            bot_token=bot_token,
            request_id=request_id,
        )

    async def _route_active_intake_message(
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
        return await route_active_intake_message(
            intake=intake,
            message=message,
            update_id=update_id,
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            text=text,
            bot_token=bot_token,
            request_id=request_id,
            repository=self._repository,
            user_repository=self._users,
            audit_writer=self._audit,
            storage=self._storage,
            admin_notifications=self._admin_notifications,
            telegram_download_file=telegram_download_file,
            handle_contact_step=self._handle_contact_step,
            handle_text_step=self._handle_text_step,
        )

    async def _send_prompt(self, *, bot_token: str, chat_id: int, step: str) -> None:
        prompt = STEP_PROMPTS.get(step)
        if prompt is None:
            return
        reply_markup = START_REPLY_MARKUP if step == "awaiting_referral_code" else REMOVE_REPLY_MARKUP
        await telegram_send_message(bot_token, chat_id, prompt, reply_markup=reply_markup)

    async def _send_final_confirmation(self, *, bot_token: str, chat_id: int) -> None:
        await telegram_send_message(bot_token, chat_id, INTAKE_CONFIRMATION)

    async def _send_business_open_message(self, *, bot_token: str, chat_id: int) -> None:
        await self._set_business_open_menu_button(bot_token=bot_token, chat_id=chat_id)
        await telegram_send_message(bot_token, chat_id, BUSINESS_OPEN_MESSAGE, reply_markup=self._business_approval_reply_markup())

    async def _set_business_open_menu_button(self, *, bot_token: str, chat_id: int) -> None:
        try:
            await telegram_set_chat_menu_button(bot_token, chat_id, BUSINESS_MENU_BUTTON_TEXT, self._business_web_app_url())
        except ApiError:
            return

    def _business_approval_reply_markup(self) -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {
                        "text": BUSINESS_APPROVAL_BUTTON_TEXT,
                        "web_app": {"url": self._business_web_app_url()},
                    }
                ]
            ]
        }

    def _business_web_app_url(self) -> str:
        base_url = self._settings.telegram_web_app_url.rstrip("/")
        return f"{base_url}/business/"
