from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.business_intake.models import INTAKE_MAX_FILE_SIZE_BYTES, BusinessIntakeRequestRecord, new_id
from app.modules.business_intake.presenters import public_business_intake_document
from app.shared.document_uploads import validate_document_upload


def store_intake_document(
    *,
    intake: BusinessIntakeRequestRecord,
    update_id: int,
    document_kind: str,
    file_name: str,
    mime_type: str,
    content: bytes,
    telegram_file_id: str | None,
    telegram_file_unique_id: str | None,
    request_id: str,
    repository,
    user_repository,
    audit_writer,
    storage,
    admin_notifications=None,
) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    if not content or len(content) > INTAKE_MAX_FILE_SIZE_BYTES:
        raise ApiError("BOT_UPLOAD_INVALID", status_code=400)
    validated_file = validate_document_upload(
        content=content,
        declared_mime_type=mime_type,
        invalid_error_code="BOT_UPLOAD_INVALID",
    )
    if intake.status != "draft" or intake.last_step != "awaiting_documents":
        raise ApiError("BOT_INPUT_INVALID", status_code=400)

    applicant = _applicant_user_for_document(intake=intake, user_repository=user_repository)
    document, stored_size = _store_and_record_intake_document(
        storage=storage,
        repository=repository,
        intake=intake,
        owner_user_id=applicant.id,
        document_kind=document_kind,
        file_name=validated_file.storage_file_name,
        mime_type=validated_file.mime_type,
        content=content,
        update_id=update_id,
        telegram_file_id=telegram_file_id,
        telegram_file_unique_id=telegram_file_unique_id,
    )
    repository.mark_update_processed(intake=intake, update_id=update_id, last_step="awaiting_documents")
    _audit_intake_document_upload(
        audit_writer=audit_writer,
        intake=intake,
        document=document,
        document_kind=document_kind,
        mime_type=validated_file.mime_type,
        size_bytes=stored_size,
        request_id=request_id,
    )
    if admin_notifications is not None:
        admin_notifications.business_document_uploaded(intake=intake, document=document, request_id=request_id)
    return {"file": public_business_intake_document(document)}


def _applicant_user_for_document(*, intake: BusinessIntakeRequestRecord, user_repository):  # type: ignore[no-untyped-def]
    applicant = user_repository.get_user_by_telegram_id(intake.telegram_user_id)
    if applicant is not None:
        return applicant
    applicant, _ = user_repository.upsert_telegram_user(
        telegram_id=intake.telegram_user_id,
        username=None,
        first_name=None,
        last_name=None,
    )
    return applicant


def _store_and_record_intake_document(
    *,
    storage,
    repository,
    intake: BusinessIntakeRequestRecord,
    owner_user_id: str,
    document_kind: str,
    file_name: str,
    mime_type: str,
    content: bytes,
    update_id: int,
    telegram_file_id: str | None,
    telegram_file_unique_id: str | None,
) -> tuple[Any, int]:  # type: ignore[no-untyped-def]
    file_id = new_id()
    stored = storage.store_business_intake_document(
        intake_id=intake.id,
        file_id=file_id,
        file_name=file_name,
        content=content,
    )
    document = repository.create_document(
        file_id=file_id,
        owner_user_id=owner_user_id,
        intake_id=intake.id,
        document_kind=document_kind,
        storage_path=stored.storage_path,
        mime_type=mime_type,
        size_bytes=stored.size_bytes,
        telegram_update_id=update_id,
        telegram_file_id=telegram_file_id,
        telegram_file_unique_id=telegram_file_unique_id,
    )
    return document, stored.size_bytes


def _audit_intake_document_upload(
    *,
    audit_writer,
    intake: BusinessIntakeRequestRecord,
    document,
    document_kind: str,
    mime_type: str,
    size_bytes: int,
    request_id: str,
) -> None:  # type: ignore[no-untyped-def]
    audit_writer.write(
        event_type="business_intake_document_uploaded",
        actor_user_id=None,
        actor_role="business_intake_bot",
        resource_type="business_intake",
        resource_id=intake.id,
        request_id=request_id,
        metadata_json={"file_id": document.id, "document_kind": document_kind, "mime_type": mime_type, "size_bytes": size_bytes},
    )
