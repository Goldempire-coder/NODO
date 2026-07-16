from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from app.core.errors import ApiError
from app.shared.storage.models import StoredPrivateFile


class LocalFilePrivateStorage:
    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _safe_suffix(self, file_name: str) -> str:
        suffix = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "bin"
        return "".join(character for character in suffix if character.isalnum())[:12] or "bin"

    def _write(self, relative_path: str, content: bytes) -> StoredPrivateFile:
        path = (self._root / relative_path).resolve()
        if self._root not in path.parents:
            raise ApiError("STORAGE_UPLOAD_FAILED", status_code=500)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return StoredPrivateFile(
            storage_path=relative_path.replace("\\", "/"),
            size_bytes=len(content),
            checksum_sha256=hashlib.sha256(content).hexdigest(),
        )

    def store(self, *, business_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        suffix = self._safe_suffix(file_name)
        return self._write(f"private/business_verification/{business_id}/{file_id}.{suffix}", content)

    def store_payment_evidence(self, *, order_id: str, payment_report_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        suffix = self._safe_suffix(file_name)
        return self._write(f"private/payment_evidence/{order_id}/{payment_report_id}/{file_id}.{suffix}", content)

    def store_message_attachment(self, *, order_id: str, attachment_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        suffix = self._safe_suffix(file_name)
        return self._write(f"private/message_attachments/{order_id}/{attachment_id}/{file_id}.{suffix}", content)

    def store_credit_purchase_proof(self, *, business_id: str, purchase_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        suffix = self._safe_suffix(file_name)
        return self._write(f"private/credit_purchase_proofs/{business_id}/{purchase_id}/{file_id}.{suffix}", content)

    def store_business_intake_document(self, *, intake_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        suffix = self._safe_suffix(file_name)
        return self._write(f"private/business_intake/{intake_id}/{file_id}.{suffix}", content)

    def store_support_attachment(self, *, ticket_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        suffix = self._safe_suffix(file_name)
        return self._write(f"private/support/{ticket_id}/{file_id}.{suffix}", content)

    def signed_view_url(self, *, storage_path: str, expires_in: int) -> str:
        path = (self._root / storage_path).resolve()
        if self._root not in path.parents or not path.exists():
            raise ApiError("BUSINESS_DOCUMENT_NOT_FOUND", status_code=404)
        issued_at = int(datetime.now(timezone.utc).timestamp())
        digest = hashlib.sha256(f"{storage_path}:{issued_at}:{expires_in}".encode()).hexdigest()
        return f"local-private://{digest}?iat={issued_at}&ttl={expires_in}"
