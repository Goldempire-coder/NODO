from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.errors import ApiError
from app.shared.photo_uploads import ALLOWED_PHOTO_MIME_TYPES, validate_photo_upload

DOCUMENT_UPLOAD_ERROR_MESSAGE = "No pudimos aceptar ese archivo. Usa una imagen o PDF valido."
PDF_MIME_TYPE = "application/pdf"
ALLOWED_DOCUMENT_MIME_TYPES = ALLOWED_PHOTO_MIME_TYPES | {PDF_MIME_TYPE}

_PDF_HEADER = re.compile(rb"\A%PDF-(?:1\.[0-9]|2\.0)(?:[\t\r\n ]|%)")
_PDF_ACTIVE_MARKERS = (
    b"<script",
    b"javascript:",
    b"/javascript",
    b"/openaction",
    b"/launch",
    b"/embeddedfile",
    b"/richmedia",
    b"/xfa",
)


@dataclass(frozen=True)
class ValidatedDocumentUpload:
    mime_type: str
    storage_file_name: str


def validate_document_upload(
    *,
    content: bytes,
    declared_mime_type: str,
    invalid_error_code: str,
) -> ValidatedDocumentUpload:
    normalized_mime = declared_mime_type.strip().lower()
    if normalized_mime not in ALLOWED_DOCUMENT_MIME_TYPES:
        raise _invalid_document(invalid_error_code)

    if normalized_mime in ALLOWED_PHOTO_MIME_TYPES:
        try:
            validated_photo = validate_photo_upload(
                content=content,
                declared_mime_type=normalized_mime,
                invalid_error_code=invalid_error_code,
            )
        except ApiError as exc:
            raise _invalid_document(invalid_error_code) from exc
        return ValidatedDocumentUpload(
            mime_type=validated_photo.mime_type,
            storage_file_name=validated_photo.storage_file_name,
        )

    if not _valid_pdf_envelope(content):
        raise _invalid_document(invalid_error_code)
    return ValidatedDocumentUpload(mime_type=PDF_MIME_TYPE, storage_file_name="document.pdf")


def _valid_pdf_envelope(content: bytes) -> bool:
    if not _PDF_HEADER.match(content[:16]):
        return False
    lowered = content.lower()
    if any(marker in lowered for marker in _PDF_ACTIVE_MARKERS):
        return False
    eof_index = content.rfind(b"%%EOF", max(0, len(content) - 1024))
    return eof_index >= 0 and not content[eof_index + len(b"%%EOF") :].strip()


def _invalid_document(error_code: str) -> ApiError:
    return ApiError(
        error_code,
        message=DOCUMENT_UPLOAD_ERROR_MESSAGE,
        status_code=400,
    )
