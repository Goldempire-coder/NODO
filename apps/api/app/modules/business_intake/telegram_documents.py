from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.core.errors import ApiError
from app.modules.business_intake.intake_document_storage import store_intake_document
from app.modules.business_intake.telegram_file_info import extract_telegram_file_info
from app.modules.business_intake.models import (
    INTAKE_MAX_FILE_SIZE_BYTES,
    BusinessIntakeDocumentRecord,
    BusinessIntakeRequestRecord,
)

TelegramDownload = Callable[[str, str], Awaitable[bytes]]


def public_document_payload(document: BusinessIntakeDocumentRecord) -> dict[str, Any]:
    return {
        "id": document.id,
        "file_type": document.file_type,
        "document_kind": document.document_kind,
        "mime_type": document.mime_type,
        "size_bytes": document.size_bytes,
        "created_at": document.created_at.isoformat(),
    }


async def handle_telegram_document(
    *,
    intake: BusinessIntakeRequestRecord,
    update_id: int,
    message: dict[str, Any],
    bot_token: str,
    request_id: str,
    repository,
    user_repository,
    audit_writer,
    storage,
    telegram_download_file: TelegramDownload,
) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    file_info = extract_telegram_file_info(message)
    existing = repository.find_document_by_telegram_file(
        intake_id=intake.id,
        telegram_update_id=update_id,
        telegram_file_id=file_info["file_id"],
        telegram_file_unique_id=file_info["file_unique_id"],
    )
    if existing is not None:
        return {"ok": True, "intake_id": intake.id, "status": intake.status, "last_step": intake.last_step, "duplicate_update": True, "file_id": existing.id}
    if file_info["size_bytes"] is not None and file_info["size_bytes"] > INTAKE_MAX_FILE_SIZE_BYTES:
        raise ApiError("BOT_UPLOAD_INVALID", status_code=400)

    content = await telegram_download_file(bot_token, file_info["file_id"])
    if len(content) > INTAKE_MAX_FILE_SIZE_BYTES:
        raise ApiError("BOT_UPLOAD_INVALID", status_code=400)

    stored = store_intake_document(
        intake=intake,
        update_id=update_id,
        document_kind=file_info["document_kind"],
        file_name=file_info["file_name"],
        mime_type=file_info["mime_type"],
        content=content,
        telegram_file_id=file_info["file_id"],
        telegram_file_unique_id=file_info["file_unique_id"],
        request_id=request_id,
        repository=repository,
        user_repository=user_repository,
        audit_writer=audit_writer,
        storage=storage,
    )
    return {"ok": True, "intake_id": intake.id, "status": intake.status, "last_step": "awaiting_documents", "duplicate_update": False, "file_id": stored["file"]["id"]}
