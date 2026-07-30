from __future__ import annotations

from app.modules.businesses.models import FileAssetRecord
from app.modules.orders.row_mappers import file_from_row, jsonb


class PostgresPaymentEvidenceFilesMixin:
    def list_payment_evidence_for_report(self, payment_report_id: str) -> list[FileAssetRecord]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(
                """
                select * from file_assets
                where resource_type = 'payment_report'
                  and resource_id = %s
                  and file_type = 'payment_evidence'
                  and deleted_at is null
                order by created_at desc
                """,
                (payment_report_id,),
            ).fetchall()
        return [file_from_row(row) for row in rows]

    def create_payment_evidence_file(
        self,
        *,
        file_id: str,
        owner_user_id: str,
        payment_report_id: str,
        storage_path: str,
        mime_type: str,
        size_bytes: int,
        content_sha256: str,
        order_id: str,
    ) -> FileAssetRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                insert into file_assets (
                    id, owner_user_id, resource_type, resource_id, file_type,
                    storage_path, mime_type, size_bytes, metadata_json, created_at
                )
                values (%s, %s, 'payment_report', %s, 'payment_evidence', %s, %s, %s, %s, now())
                returning *
                """,
                (
                    file_id,
                    owner_user_id,
                    payment_report_id,
                    storage_path,
                    mime_type,
                    size_bytes,
                    jsonb(
                        {
                            "content_sha256": content_sha256,
                            "order_id": order_id,
                        }
                    ),
                ),
            ).fetchone()
            conn.commit()
        return file_from_row(row)

    def get_payment_evidence_file(self, file_id: str) -> FileAssetRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                select * from file_assets
                where id = %s
                  and resource_type = 'payment_report'
                  and file_type = 'payment_evidence'
                  and deleted_at is null
                """,
                (file_id,),
            ).fetchone()
        return file_from_row(row) if row else None
