from __future__ import annotations

import warnings
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.core.errors import ApiError

PHOTO_UPLOAD_ERROR_MESSAGE = "No pudimos aceptar ese archivo. Usa una imagen valida."

_PHOTO_FORMATS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
}
ALLOWED_PHOTO_MIME_TYPES = frozenset(mime_type for mime_type, _ in _PHOTO_FORMATS.values())


@dataclass(frozen=True)
class ValidatedPhoto:
    mime_type: str
    storage_file_name: str


def validate_photo_upload(
    *,
    content: bytes,
    declared_mime_type: str,
    invalid_error_code: str,
    type_error_code: str | None = None,
) -> ValidatedPhoto:
    normalized_mime = declared_mime_type.strip().lower()
    if normalized_mime not in ALLOWED_PHOTO_MIME_TYPES:
        raise ApiError(
            type_error_code or invalid_error_code,
            message=PHOTO_UPLOAD_ERROR_MESSAGE,
            status_code=400,
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                detected_format = image.format
                image.verify()
            with Image.open(BytesIO(content)) as decoded_image:
                decoded_image.load()
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
        ValueError,
        UnidentifiedImageError,
    ) as exc:
        raise ApiError(
            invalid_error_code,
            message=PHOTO_UPLOAD_ERROR_MESSAGE,
            status_code=400,
        ) from exc

    detected = _PHOTO_FORMATS.get(detected_format or "")
    if detected is None or detected[0] != normalized_mime:
        raise ApiError(
            invalid_error_code,
            message=PHOTO_UPLOAD_ERROR_MESSAGE,
            status_code=400,
        )
    mime_type, extension = detected
    return ValidatedPhoto(mime_type=mime_type, storage_file_name=f"photo{extension}")
