from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app.core.errors import ApiError
from app.shared.storage.models import StoredPrivateFile


class InMemoryPrivateStorage:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def _store_private_object(self, storage_path: str, content: bytes) -> StoredPrivateFile:
        self._objects[storage_path] = content
        return StoredPrivateFile(
            storage_path=storage_path,
            size_bytes=len(content),
            checksum_sha256=hashlib.sha256(content).hexdigest(),
        )

    def store(self, *, business_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        suffix = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "bin"
        return self._store_private_object(f"private/business_verification/{business_id}/{file_id}.{suffix}", content)

    def store_payment_evidence(self, *, order_id: str, payment_report_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        suffix = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "bin"
        return self._store_private_object(f"private/payment_evidence/{order_id}/{payment_report_id}/{file_id}.{suffix}", content)

    def store_message_attachment(self, *, order_id: str, attachment_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        suffix = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "bin"
        return self._store_private_object(f"private/message_attachments/{order_id}/{attachment_id}/{file_id}.{suffix}", content)

    def store_credit_purchase_proof(self, *, business_id: str, purchase_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        suffix = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "bin"
        return self._store_private_object(f"private/credit_purchase_proofs/{business_id}/{purchase_id}/{file_id}.{suffix}", content)

    def store_business_intake_document(self, *, intake_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        suffix = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "bin"
        return self._store_private_object(f"private/business_intake/{intake_id}/{file_id}.{suffix}", content)

    def signed_view_url(self, *, storage_path: str, expires_in: int) -> str:
        if storage_path not in self._objects:
            raise ApiError("BUSINESS_DOCUMENT_NOT_FOUND", status_code=404)
        issued_at = int(datetime.now(timezone.utc).timestamp())
        return f"test://private-document/{hashlib.sha256(storage_path.encode()).hexdigest()}?iat={issued_at}&ttl={expires_in}"
