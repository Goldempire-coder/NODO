from __future__ import annotations

from fastapi import APIRouter, Header, Request

from app.core.errors import ApiError
from app.modules.business_intake.policy import require_bot_secret
from app.modules.business_intake.route_helpers import request_id, service

telegram_router = APIRouter(tags=["business-intake"])

RECOVERABLE_TELEGRAM_ERRORS = {"BOT_INPUT_INVALID", "BOT_CONTACT_REQUIRED", "BOT_UPLOAD_INVALID", "RATE_LIMITED"}


async def _send_telegram_message(bot_token: str, chat_id: int, text: str) -> None:
    from app.modules.business_intake import routes as routes_module

    await routes_module.telegram_send_message(bot_token, chat_id, text)


def _telegram_message_context(update: dict) -> tuple[int | None, int | None]:
    message = update.get("message") or update.get("edited_message") or {}
    if not isinstance(message, dict):
        return None, None
    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    chat_id = chat.get("id")
    telegram_user_id = sender.get("id")
    try:
        return int(chat_id), int(telegram_user_id)
    except (TypeError, ValueError):
        return None, None


def _recoverable_message_for_step(*, code: str, last_step: str | None) -> str:
    if code == "BOT_UPLOAD_INVALID":
        return "Ese archivo no se puede usar. Envia una imagen o PDF de hasta 5 MB."
    if code == "RATE_LIMITED":
        return "Recibimos muchos intentos seguidos. Espera un momento y vuelve a intentar."
    if last_step == "awaiting_whatsapp_phone":
        return "Ese numero no parece valido. Escribe tu numero de WhatsApp con codigo de pais."
    if last_step == "awaiting_documents":
        return "Adjunta una imagen o PDF. Cuando termines, escribe finalizar."
    if last_step == "awaiting_referral_code":
        return "Escribe tu codigo de referencia para comenzar."
    return "No pude usar esa respuesta. Revisa la instruccion anterior o escribe /start para comenzar de nuevo."


async def _handle_business_intake_telegram_webhook(*, provided_secret: str | None, request: Request) -> dict:
    require_bot_secret(
        provided_secret=provided_secret,
        bot_token=request.app.state.settings.business_intake_bot_token,
    )
    try:
        update = await request.json()
    except ValueError as exc:
        raise ApiError("BOT_INPUT_INVALID", status_code=400) from exc
    if not isinstance(update, dict):
        raise ApiError("BOT_INPUT_INVALID", status_code=400)

    intake_service = service(request)
    try:
        result = await intake_service.process_telegram_update(
            update=update,
            bot_token=request.app.state.settings.business_intake_bot_token,
            request_id=request_id(request),
        )
    except ApiError as exc:
        if exc.code not in RECOVERABLE_TELEGRAM_ERRORS:
            raise
        chat_id, telegram_user_id = _telegram_message_context(update)
        last_step = None
        if chat_id is not None:
            intake = request.app.state.business_intake_repository.get_active_for_chat(telegram_chat_id=chat_id)
            if intake is not None:
                last_step = intake.last_step
        if chat_id is not None:
            await _send_telegram_message(
                request.app.state.settings.business_intake_bot_token,
                chat_id,
                _recoverable_message_for_step(code=exc.code, last_step=last_step),
            )
        result = {
            "ok": True,
            "handled": True,
            "recoverable_error": exc.code,
            "telegram_user_id": telegram_user_id,
            "last_step": last_step,
        }
    return {"data": result, "request_id": request_id(request)}


@telegram_router.post("/business-intake/telegram/webhook")
async def business_intake_telegram_webhook(
    request: Request,
    telegram_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
    nodo_secret: str | None = Header(default=None, alias="X-NODO-Bot-Webhook-Secret"),
) -> dict:
    return await _handle_business_intake_telegram_webhook(provided_secret=telegram_secret or nodo_secret, request=request)


@telegram_router.post("/business-intake/telegram/webhook/{legacy_secret}", deprecated=True)
async def legacy_business_intake_telegram_webhook(legacy_secret: str, request: Request) -> dict:
    return await _handle_business_intake_telegram_webhook(provided_secret=legacy_secret, request=request)
