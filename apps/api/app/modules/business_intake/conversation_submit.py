from __future__ import annotations

from typing import Callable

from app.core.errors import ApiError
from app.modules.business_intake.models import BusinessIntakeDocumentRecord, BusinessIntakeRequestRecord

SUBMIT_WORDS = {"finalizar", "terminar", "enviar", "submit", "done"}


def ensure_submit_command(cleaned: str) -> None:
    if cleaned.lower() not in SUBMIT_WORDS:
        raise ApiError("BOT_INPUT_INVALID", status_code=400)


def ensure_ready_to_submit(
    intake: BusinessIntakeRequestRecord,
    *,
    list_documents: Callable[[str], list[BusinessIntakeDocumentRecord]],
) -> None:
    if not intake.referral_code or not intake.contact_phone:
        raise ApiError("BOT_INPUT_INVALID", status_code=400)
    if not list_documents(intake.id):
        raise ApiError("BOT_INPUT_INVALID", status_code=400)
