from __future__ import annotations

from app.modules.businesses.models import BusinessVerificationSubmissionRecord, FileAssetRecord
from app.modules.businesses.row_mappers import file_from_row, jsonb, submission_from_row


class PostgresBusinessVerificationAssetsMixin:
    def create_file_asset(
        self,
        *,
        file_id: str,
        owner_user_id: str,
        business_id: str,
        file_type: str,
        storage_path: str,
        mime_type: str,
        size_bytes: int,
    ) -> FileAssetRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                insert into file_assets (id, owner_user_id, resource_type, resource_id, file_type, storage_path, mime_type, size_bytes, created_at)
                values (%s, %s, 'business', %s, %s, %s, %s, %s, now())
                returning *
                """,
                (file_id, owner_user_id, business_id, file_type, storage_path, mime_type, size_bytes),
            ).fetchone()
            conn.commit()
        return file_from_row(row)

    def list_files_for_business(self, business_id: str) -> list[FileAssetRecord]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(
                "select * from file_assets where resource_type = 'business' and resource_id = %s and deleted_at is null order by created_at desc",
                (business_id,),
            ).fetchall()
        return [file_from_row(row) for row in rows]

    def get_file_for_business(self, business_id: str, file_id: str) -> FileAssetRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                "select * from file_assets where id = %s and resource_type = 'business' and resource_id = %s and deleted_at is null",
                (file_id, business_id),
            ).fetchone()
        return file_from_row(row) if row else None

    def get_latest_submission(self, business_id: str) -> BusinessVerificationSubmissionRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                "select * from business_verification_submissions where business_id = %s order by created_at desc limit 1",
                (business_id,),
            ).fetchone()
        return submission_from_row(row) if row else None

    def get_pending_submission(self, business_id: str) -> BusinessVerificationSubmissionRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                "select * from business_verification_submissions where business_id = %s and status = 'pending' order by created_at desc limit 1",
                (business_id,),
            ).fetchone()
        return submission_from_row(row) if row else None

    def create_submission(self, *, business_id: str, submitted_by_user_id: str, submitted_data_json: dict) -> BusinessVerificationSubmissionRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                insert into business_verification_submissions (
                    business_id, submitted_by_user_id, status, submitted_data_json,
                    submitted_at, created_at, updated_at
                )
                values (%s, %s, 'pending', %s, now(), now(), now())
                returning *
                """,
                (business_id, submitted_by_user_id, jsonb(submitted_data_json)),
            ).fetchone()
            conn.commit()
        return submission_from_row(row)
