from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.businesses.models import ALLOWED_MIME_TYPES, DOCUMENT_TYPES, MAX_DOCUMENT_SIZE_BYTES, new_id
from app.modules.businesses.policy import require_business_owner
from app.modules.businesses.presenters import file_payload
from app.modules.businesses.state_machine import require_owner_upload_allowed
from app.modules.users.models import UserRecord
from app.shared.document_uploads import ValidatedDocumentUpload, validate_document_upload


class LegacyBusinessDocumentMixin:
    def upload_document(
        self,
        *,
        user: UserRecord,
        business_id: str,
        file_type: str,
        file_name: str,
        mime_type: str,
        content: bytes,
        request_id: str,
    ) -> dict[str, Any]:
        self._rate_limit("upload", user)  # type: ignore[attr-defined]
        business = self._business_or_404(business_id)  # type: ignore[attr-defined]
        require_business_owner(user, business)
        require_owner_upload_allowed(business)
        validated_file = self._validate_legacy_document(file_type=file_type, mime_type=mime_type, content=content)
        file_id = new_id()
        stored = self._storage.store(  # type: ignore[attr-defined]
            business_id=business.id,
            file_id=file_id,
            file_name=validated_file.storage_file_name,
            content=content,
        )
        file = self._repository.create_file_asset(  # type: ignore[attr-defined]
            file_id=file_id,
            owner_user_id=user.id,
            business_id=business.id,
            file_type=file_type,
            storage_path=stored.storage_path,
            mime_type=validated_file.mime_type,
            size_bytes=stored.size_bytes,
        )
        self._audit.write(  # type: ignore[attr-defined]
            event_type="verification_document_uploaded",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="business",
            resource_id=business.id,
            request_id=request_id,
            metadata_json={
                "file_id": file.id,
                "file_type": file.file_type,
                "mime_type": file.mime_type,
                "size_bytes": file.size_bytes,
            },
        )
        return {"file": file_payload(file)}

    def _validate_legacy_document(
        self,
        *,
        file_type: str,
        mime_type: str,
        content: bytes,
    ) -> ValidatedDocumentUpload:
        if file_type not in DOCUMENT_TYPES or mime_type not in ALLOWED_MIME_TYPES or not content or len(content) > MAX_DOCUMENT_SIZE_BYTES:
            raise ApiError("BUSINESS_DOCUMENT_INVALID", status_code=400)
        return validate_document_upload(
            content=content,
            declared_mime_type=mime_type,
            invalid_error_code="BUSINESS_DOCUMENT_INVALID",
        )
