from __future__ import annotations

from app.modules.business_intake.models import BusinessIntakeDocumentRecord
from app.modules.business_intake.repository_common import document_from_row, jsonb


class PostgresBusinessIntakeDocumentsMixin:
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
        metadata = {
            "document_kind": document_kind,
            "telegram_update_id": telegram_update_id,
            "telegram_file_id": telegram_file_id,
            "telegram_file_unique_id": telegram_file_unique_id,
        }
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                insert into file_assets (
                    id, owner_user_id, resource_type, resource_id, file_type,
                    storage_path, mime_type, size_bytes, metadata_json, created_at
                )
                values (%s, %s, 'business_intake', %s, 'intake_document', %s, %s, %s, %s, now())
                returning *
                """,
                (file_id, owner_user_id, intake_id, storage_path, mime_type, size_bytes, jsonb(metadata)),
            ).fetchone()
            conn.commit()
        return document_from_row(row)

    def find_document_by_telegram_file(
        self,
        *,
        intake_id: str,
        telegram_update_id: int,
        telegram_file_id: str | None,
        telegram_file_unique_id: str | None,
    ) -> BusinessIntakeDocumentRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                select * from file_assets
                where resource_type = 'business_intake'
                  and resource_id = %s
                  and deleted_at is null
                  and metadata_json->>'telegram_update_id' = %s
                  and (
                    (%s::text is not null and metadata_json->>'telegram_file_unique_id' = %s::text)
                    or (%s::text is not null and metadata_json->>'telegram_file_id' = %s::text)
                  )
                order by created_at desc
                limit 1
                """,
                (
                    intake_id,
                    str(telegram_update_id),
                    telegram_file_unique_id,
                    telegram_file_unique_id,
                    telegram_file_id,
                    telegram_file_id,
                ),
            ).fetchone()
        return document_from_row(row) if row else None

    def list_documents(self, intake_id: str) -> list[BusinessIntakeDocumentRecord]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(
                """
                select * from file_assets
                where resource_type = 'business_intake' and resource_id = %s and deleted_at is null
                order by created_at desc
                """,
                (intake_id,),
            ).fetchall()
        return [document_from_row(row) for row in rows]

    def get_document(self, intake_id: str, file_id: str) -> BusinessIntakeDocumentRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                select * from file_assets
                where id = %s
                  and resource_type = 'business_intake'
                  and resource_id = %s
                  and deleted_at is null
                limit 1
                """,
                (file_id, intake_id),
            ).fetchone()
        return document_from_row(row) if row else None
