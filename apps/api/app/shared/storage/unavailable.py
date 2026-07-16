from __future__ import annotations

from app.core.errors import ApiError
from app.shared.storage.models import StoredPrivateFile


class UnavailablePrivateStorage:
    def store(self, *, business_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        raise ApiError("STORAGE_UNAVAILABLE", status_code=503)

    def store_payment_evidence(self, *, order_id: str, payment_report_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        raise ApiError("STORAGE_UNAVAILABLE", status_code=503)

    def store_message_attachment(self, *, order_id: str, attachment_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        raise ApiError("STORAGE_UNAVAILABLE", status_code=503)

    def store_credit_purchase_proof(self, *, business_id: str, purchase_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        raise ApiError("STORAGE_UNAVAILABLE", status_code=503)

    def store_business_intake_document(self, *, intake_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        raise ApiError("STORAGE_UNAVAILABLE", status_code=503)

    def store_support_attachment(self, *, ticket_id: str, file_id: str, file_name: str, content: bytes) -> StoredPrivateFile:
        raise ApiError("STORAGE_UNAVAILABLE", status_code=503)

    def signed_view_url(self, *, storage_path: str, expires_in: int) -> str:
        raise ApiError("STORAGE_UNAVAILABLE", status_code=503)
