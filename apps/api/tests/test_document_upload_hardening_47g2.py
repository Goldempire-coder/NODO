from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from app.core.errors import ApiError
from app.shared.document_uploads import validate_document_upload


def _image_bytes(image_format: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color=(20, 120, 220)).save(buffer, format=image_format)
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("declared_mime_type", "content", "expected_name"),
    [
        ("image/jpeg", _image_bytes("JPEG"), "photo.jpg"),
        ("image/png", _image_bytes("PNG"), "photo.png"),
        ("image/webp", _image_bytes("WEBP"), "photo.webp"),
        ("application/pdf", b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n", "document.pdf"),
    ],
)
def test_document_upload_accepts_supported_content_with_canonical_metadata(
    declared_mime_type: str,
    content: bytes,
    expected_name: str,
) -> None:
    validated = validate_document_upload(
        content=content,
        declared_mime_type=declared_mime_type,
        invalid_error_code="DOCUMENT_INVALID",
    )

    assert validated.mime_type == declared_mime_type
    assert validated.storage_file_name == expected_name


@pytest.mark.parametrize(
    ("declared_mime_type", "content"),
    [
        ("image/jpeg", b"<html><script>alert(1)</script></html>"),
        ("image/jpeg", b"%PDF-1.7\n%%EOF\n"),
        ("image/png", b"<svg><script/></svg>"),
        ("image/webp", b"RIFFbrokenWEBP"),
        ("application/pdf", b"<html>not a pdf</html>"),
        ("application/pdf", b"PK\x03\x04archive"),
        ("application/pdf", b"%PDF-1.7\nmissing eof"),
        ("application/pdf", b"%PDF-1.7\n<Script>alert(1)</Script>\n%%EOF\n"),
        ("application/pdf", b"%PDF-1.7\n/OpenAction 1 0 R\n%%EOF\n"),
        ("application/pdf", b"%PDF-1.7\n%%EOF\n<script/>"),
        ("image/svg+xml", b"<svg/>"),
    ],
)
def test_document_upload_rejects_disguised_or_corrupt_content(
    declared_mime_type: str,
    content: bytes,
) -> None:
    with pytest.raises(ApiError) as captured:
        validate_document_upload(
            content=content,
            declared_mime_type=declared_mime_type,
            invalid_error_code="DOCUMENT_INVALID",
        )

    assert captured.value.code == "DOCUMENT_INVALID"
    assert captured.value.status_code == 400
    assert "PDF" in captured.value.message
