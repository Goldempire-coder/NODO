from __future__ import annotations

from app.modules.business_intake.models import BusinessIntakeDocumentRecord
from app.modules.businesses.models import BusinessVerificationSubmissionRecord, FileAssetRecord, new_id
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
                """
                with direct as (
                    select *
                    from file_assets
                    where resource_type = 'business'
                      and resource_id = %s
                      and deleted_at is null
                ),
                linked_intake as (
                    select file_assets.*
                    from file_assets
                    join business_intake_requests
                      on business_intake_requests.id = file_assets.resource_id
                    where file_assets.resource_type = 'business_intake'
                      and business_intake_requests.created_business_id = %s
                      and file_assets.deleted_at is null
                      and not exists (
                          select 1
                          from direct
                          where direct.storage_path = file_assets.storage_path
                      )
                )
                select * from direct
                union all
                select * from linked_intake
                order by created_at desc
                """,
                (business_id, business_id),
            ).fetchall()
        return [file_from_row(row) for row in rows]

    def get_file_for_business(self, business_id: str, file_id: str) -> FileAssetRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                select *
                from file_assets
                where id = %s
                  and deleted_at is null
                  and (
                    (resource_type = 'business' and resource_id = %s)
                    or (
                        resource_type = 'business_intake'
                        and exists (
                            select 1
                            from business_intake_requests
                            where business_intake_requests.id = file_assets.resource_id
                              and business_intake_requests.created_business_id = %s
                        )
                    )
                  )
                """,
                (file_id, business_id, business_id),
            ).fetchone()
        return file_from_row(row) if row else None

    def link_intake_document_to_business(self, *, business_id: str, document: BusinessIntakeDocumentRecord) -> bool:
        with self._connect() as conn:  # type: ignore[attr-defined]
            existing = conn.execute(
                """
                select *
                from file_assets
                where resource_type = 'business'
                  and resource_id = %s
                  and storage_path = %s
                  and deleted_at is null
                limit 1
                """,
                (business_id, document.storage_path),
            ).fetchone()
            if existing:
                return False
            conn.execute(
                """
                insert into file_assets (
                    id, owner_user_id, resource_type, resource_id, file_type,
                    storage_path, mime_type, size_bytes, created_at
                )
                values (%s, %s, 'business', %s, %s, %s, %s, %s, %s)
                """,
                (
                    new_id(),
                    document.owner_user_id,
                    business_id,
                    document.file_type,
                    document.storage_path,
                    document.mime_type,
                    document.size_bytes,
                    document.created_at,
                ),
            )
            conn.commit()
        return True

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
