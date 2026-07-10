from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.core.errors import ApiError
from app.modules.business_intake.models import BusinessIntakeRequestRecord
from app.modules.business_intake.telegram_file_info import message_has_allowed_file, message_has_forbidden_media
from app.modules.business_intake.telegram_documents import (
    TelegramDownload,
    handle_telegram_document,
)

ContactHandler = Callable[..., Awaitable[dict[str, Any]]]
TextHandler = Callable[..., Awaitable[dict[str, Any]]]


async def route_active_intake_message(
    *,
    intake: BusinessIntakeRequestRecord,
    message: dict[str, Any],
    update_id: int,
    chat_id: int,
    telegram_user_id: int,
    text: str | None,
    bot_token: str,
    request_id: str,
    repository,
    user_repository,
    audit_writer,
    storage,
    telegram_download_file: TelegramDownload,
    handle_contact_step: ContactHandler,
    handle_text_step: TextHandler,
) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    if message_has_forbidden_media(message):
        raise ApiError("BOT_UPLOAD_INVALID", status_code=400)

    if message_has_allowed_file(message):
        return await handle_telegram_document(
            intake=intake,
            update_id=update_id,
            message=message,
            bot_token=bot_token,
            request_id=request_id,
            repository=repository,
            user_repository=user_repository,
            audit_writer=audit_writer,
            storage=storage,
            telegram_download_file=telegram_download_file,
        )

    if intake.last_step == "awaiting_contact":
        return await handle_contact_step(
            intake=intake,
            update_id=update_id,
            message=message,
            telegram_user_id=telegram_user_id,
            bot_token=bot_token,
            chat_id=chat_id,
            request_id=request_id,
        )

    if not isinstance(text, str):
        raise ApiError("BOT_INPUT_INVALID", status_code=400)
    return await handle_text_step(
        intake=intake,
        update_id=update_id,
        text=text,
        bot_token=bot_token,
        chat_id=chat_id,
        request_id=request_id,
    )
