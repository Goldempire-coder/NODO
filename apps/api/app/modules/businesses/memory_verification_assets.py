from __future__ import annotations

from app.modules.business_intake.models import BusinessIntakeDocumentRecord
from app.core.errors import ApiError
from app.modules.businesses.models import BusinessVerificationSubmissionRecord, FileAssetRecord, new_id, utc_now


class InMemoryBusinessVerificationAssetsMixin:
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
        with self._lock:  # type: ignore[attr-defined]
            file_asset = FileAssetRecord(
                id=file_id,
                owner_user_id=owner_user_id,
                resource_type="business",
                resource_id=business_id,
                file_type=file_type,
                storage_path=storage_path,
                mime_type=mime_type,
                size_bytes=size_bytes,
            )
            self.files[file_asset.id] = file_asset  # type: ignore[attr-defined]
            return file_asset

    def list_files_for_business(self, business_id: str) -> list[FileAssetRecord]:
        return [
            file
            for file in self.files.values()  # type: ignore[attr-defined]
            if file.resource_type == "business" and file.resource_id == business_id and file.deleted_at is None
        ]

    def get_file_for_business(self, business_id: str, file_id: str) -> FileAssetRecord | None:
        file = self.files.get(file_id)  # type: ignore[attr-defined]
        if file and file.resource_type == "business" and file.resource_id == business_id and file.deleted_at is None:
            return file
        return None

    def link_intake_document_to_business(self, *, business_id: str, document: BusinessIntakeDocumentRecord) -> bool:
        with self._lock:  # type: ignore[attr-defined]
            for file in self.files.values():  # type: ignore[attr-defined]
                if (
                    file.resource_type == "business"
                    and file.resource_id == business_id
                    and file.storage_path == document.storage_path
                    and file.deleted_at is None
                ):
                    return False
            file_asset = FileAssetRecord(
                id=new_id(),
                owner_user_id=document.owner_user_id,
                resource_type="business",
                resource_id=business_id,
                file_type=document.file_type,
                storage_path=document.storage_path,
                mime_type=document.mime_type,
                size_bytes=document.size_bytes,
                created_at=document.created_at,
            )
            self.files[file_asset.id] = file_asset  # type: ignore[attr-defined]
            return True

    def get_latest_submission(self, business_id: str) -> BusinessVerificationSubmissionRecord | None:
        submissions = [submission for submission in self.submissions.values() if submission.business_id == business_id]  # type: ignore[attr-defined]
        return max(submissions, key=lambda submission: submission.created_at, default=None)

    def get_pending_submission(self, business_id: str) -> BusinessVerificationSubmissionRecord | None:
        for submission in self.submissions.values():  # type: ignore[attr-defined]
            if submission.business_id == business_id and submission.status == "pending":
                return submission
        return None

    def create_submission(
        self,
        *,
        business_id: str,
        submitted_by_user_id: str,
        submitted_data_json: dict,
    ) -> BusinessVerificationSubmissionRecord:
        with self._lock:  # type: ignore[attr-defined]
            if self.get_pending_submission(business_id) is not None:
                raise ApiError("BUSINESS_ALREADY_SUBMITTED", status_code=409)
            now = utc_now()
            submission = BusinessVerificationSubmissionRecord(
                id=new_id(),
                business_id=business_id,
                submitted_by_user_id=submitted_by_user_id,
                status="pending",
                submitted_data_json=submitted_data_json,
                submitted_at=now,
                created_at=now,
                updated_at=now,
            )
            self.submissions[submission.id] = submission  # type: ignore[attr-defined]
            return submission
