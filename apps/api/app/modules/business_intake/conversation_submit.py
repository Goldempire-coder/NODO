from __future__ import annotations

from typing import Callable

from app.core.errors import ApiError
from app.modules.business_intake.intake_requirements import ensure_intake_ready_for_review
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
    ensure_intake_ready_for_review(
        intake,
        documents=list_documents(intake.id),
        error_code="BOT_INPUT_INVALID",
        status_code=400,
    )
