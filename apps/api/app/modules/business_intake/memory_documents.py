from __future__ import annotations

from app.modules.business_intake.models import BusinessIntakeDocumentRecord


class InMemoryBusinessIntakeDocumentsMixin:
    def create_document(
        self,
        *,
        file_id: str,
        owner_user_id: str,
        intake_id: str,
        document_kind: str,
        storage_path: str,
        mime_type: str,
        size_bytes: int,
        telegram_update_id: int | None = None,
        telegram_file_id: str | None = None,
        telegram_file_unique_id: str | None = None,
    ) -> BusinessIntakeDocumentRecord:
        with self._lock:  # type: ignore[attr-defined]
            doc = BusinessIntakeDocumentRecord(
                id=file_id,
                owner_user_id=owner_user_id,
                resource_type="business_intake",
                resource_id=intake_id,
                file_type="intake_document",
                storage_path=storage_path,
                mime_type=mime_type,
                size_bytes=size_bytes,
                document_kind=document_kind,
                telegram_update_id=telegram_update_id,
                telegram_file_id=telegram_file_id,
                telegram_file_unique_id=telegram_file_unique_id,
            )
            self.documents[doc.id] = doc  # type: ignore[attr-defined]
            return doc

    def find_document_by_telegram_file(
        self,
        *,
        intake_id: str,
        telegram_update_id: int,
        telegram_file_id: str | None,
        telegram_file_unique_id: str | None,
    ) -> BusinessIntakeDocumentRecord | None:
        for document in self.documents.values():  # type: ignore[attr-defined]
            if document.resource_id != intake_id or document.deleted_at is not None:
                continue
            if document.telegram_update_id != telegram_update_id:
                continue
            if telegram_file_unique_id and document.telegram_file_unique_id == telegram_file_unique_id:
                return document
            if telegram_file_id and document.telegram_file_id == telegram_file_id:
                return document
        return None

    def list_documents(self, intake_id: str) -> list[BusinessIntakeDocumentRecord]:
        return [
            doc
            for doc in self.documents.values()  # type: ignore[attr-defined]
            if doc.resource_type == "business_intake" and doc.resource_id == intake_id and doc.deleted_at is None
        ]
