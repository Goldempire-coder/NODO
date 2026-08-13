from __future__ import annotations

from app.core.errors import ApiError
from app.modules.business_intake.models import (
    INTAKE_DOCUMENT_KINDS,
    INTAKE_MAX_FILE_SIZE_BYTES,
    new_id,
)
from app.shared.document_uploads import validate_document_upload


class BusinessIntakePublicDocumentsMixin:
    def upload_document(
        self,
        *,
        intake_id: str,
        telegram_update_id: int,
        document_kind: str,
        file_name: str,
        mime_type: str,
        content: bytes,
        request_id: str,
    ) -> dict[str, object]:
        if document_kind not in INTAKE_DOCUMENT_KINDS:
            raise ApiError("BOT_UPLOAD_INVALID", status_code=400)
        intake = self._get_intake(intake_id)  # type: ignore[attr-defined]
        self._rate_limit("document", str(intake.telegram_user_id))  # type: ignore[attr-defined]
        if not content or len(content) > INTAKE_MAX_FILE_SIZE_BYTES:
            raise ApiError("BOT_UPLOAD_INVALID", status_code=400)
        validated_file = validate_document_upload(
            content=content,
            declared_mime_type=mime_type,
            invalid_error_code="BOT_UPLOAD_INVALID",
        )
        if intake.last_update_id == telegram_update_id:
            documents = self._repository.list_documents(intake.id)  # type: ignore[attr-defined]
            if documents:
                return {"file": self._public_document(documents[0]), "pending": True}  # type: ignore[attr-defined]
        if intake.status not in {"draft", "submitted"}:
            raise ApiError("BUSINESS_INTAKE_STATUS_INVALID", status_code=409)
        applicant = self._ensure_applicant_user(intake.telegram_user_id)  # type: ignore[attr-defined]
        file_id = new_id()
        stored = self._storage.store_business_intake_document(  # type: ignore[attr-defined]
            intake_id=intake.id,
            file_id=file_id,
            file_name=validated_file.storage_file_name,
            content=content,
        )
        document = self._repository.create_document(  # type: ignore[attr-defined]
            file_id=file_id,
            owner_user_id=applicant.id,
            intake_id=intake.id,
            document_kind=document_kind,
            storage_path=stored.storage_path,
            mime_type=validated_file.mime_type,
            size_bytes=stored.size_bytes,
        )
        updated = self._repository.mark_update_processed(  # type: ignore[attr-defined]
            intake=intake,
            update_id=telegram_update_id,
            last_step="awaiting_documents",
        )
        self._write_audit(  # type: ignore[attr-defined]
            event_type="business_intake_document_uploaded",
            intake=updated,
            request_id=request_id,
            metadata={
                "file_id": document.id,
                "document_kind": document_kind,
                "mime_type": validated_file.mime_type,
                "size_bytes": stored.size_bytes,
            },
        )
        if getattr(self, "_admin_notifications", None) is not None:
            self._admin_notifications.business_document_uploaded(intake=updated, document=document, request_id=request_id)  # type: ignore[attr-defined]
        return {"file": self._public_document(document), "pending": True}  # type: ignore[attr-defined]
