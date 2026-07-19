from __future__ import annotations

from typing import Any, Callable

from app.core.errors import ApiError
from app.modules.business_intake.admin_delete import BusinessIntakeAdminDeleteMixin
from app.modules.business_intake.admin_review import BusinessIntakeAdminReviewMixin
from app.modules.business_intake.admin_update import BusinessIntakeAdminUpdateMixin
from app.modules.business_intake.business_creation import BusinessIntakeBusinessCreationMixin
from app.modules.business_intake.models import BusinessIntakeRequestRecord
from app.modules.business_intake.policy import require_admin_mutation, require_admin_read
from app.modules.users.models import UserRecord


class BusinessIntakeAdminActions(
    BusinessIntakeAdminReviewMixin,
    BusinessIntakeAdminUpdateMixin,
    BusinessIntakeAdminDeleteMixin,
    BusinessIntakeBusinessCreationMixin,
):
    def __init__(
        self,
        *,
        settings,
        repository,
        business_repository,
        user_repository,
        audit_writer,
        rate_limiter,
        idempotency_store,
        storage,
        public_intake: Callable[[BusinessIntakeRequestRecord], dict[str, Any]],
        public_document: Callable[[Any], dict[str, Any]],
    ) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._businesses = business_repository
        self._users = user_repository
        self._audit = audit_writer
        self._rate_limiter = rate_limiter
        self._idempotency = idempotency_store
        self._storage = storage
        self._public_intake = public_intake
        self._public_document = public_document

    def _rate_limit(self, action: str, key: str) -> None:
        if not self._rate_limiter.allow(
            f"business_intake:{action}:{key}",
            max_attempts=self._settings.business_rate_limit_max_attempts,
            window_seconds=self._settings.business_rate_limit_window_seconds,
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def _get_intake(self, intake_id: str) -> BusinessIntakeRequestRecord:
        intake = self._repository.get(intake_id)
        if intake is None:
            raise ApiError("BUSINESS_INTAKE_NOT_FOUND", status_code=404)
        return intake

    def _ensure_applicant_user(self, telegram_user_id: int) -> UserRecord:
        user = self._users.get_user_by_telegram_id(telegram_user_id)
        if user is not None:
            return user
        user, _ = self._users.upsert_telegram_user(
            telegram_id=telegram_user_id,
            username=None,
            first_name=None,
            last_name=None,
        )
        return user

    def _write_admin_audit(
        self,
        *,
        event_type: str,
        user: UserRecord,
        intake: BusinessIntakeRequestRecord,
        request_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._audit.write(
            event_type=event_type,
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="business_intake",
            resource_id=intake.id,
            request_id=request_id,
            metadata_json=metadata or {},
        )

    def _document_download_filename(self, *, intake: BusinessIntakeRequestRecord, document: Any) -> str:
        extension_by_mime = {
            "application/pdf": "pdf",
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
        }
        extension = extension_by_mime.get(document.mime_type, "bin")
        business_slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in (intake.business_name or "solicitud"))
        business_slug = "-".join(part for part in business_slug.split("-") if part)[:48] or "solicitud"
        return f"nodo-intake-{business_slug}-{document.document_kind}.{extension}"

    def list(self, *, user: UserRecord, status: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("admin_list", user.id)
        items, next_cursor = self._repository.list_intakes(status=status, cursor=cursor, limit=limit)
        return {"items": [self._public_intake(item) for item in items], "next_cursor": next_cursor}

    def detail(self, *, user: UserRecord, intake_id: str, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("admin_detail", user.id)
        intake = self._get_intake(intake_id)
        documents = self._repository.list_documents(intake.id)
        self._write_admin_audit(event_type="business_intake_viewed_by_admin", user=user, intake=intake, request_id=request_id)
        return {"intake": self._public_intake(intake), "documents": [self._public_document(doc) for doc in documents]}

    def document_view_url(
        self,
        *,
        user: UserRecord,
        intake_id: str,
        file_id: str,
        reason: str | None,
        request_id: str,
    ) -> dict[str, Any]:
        require_admin_mutation(user)
        self._rate_limit("admin_document_view_url", user.id)
        clean_reason = (reason or "").strip() or "admin_document_review"
        intake = self._get_intake(intake_id)
        document = self._repository.get_document(intake.id, file_id)
        if document is None:
            raise ApiError("BUSINESS_INTAKE_DOCUMENT_NOT_FOUND", status_code=404)
        expires_in = min(self._settings.storage_signed_url_ttl_seconds, 300)
        url = self._storage.signed_view_url(storage_path=document.storage_path, expires_in=expires_in)
        self._write_admin_audit(
            event_type="business_intake_document_viewed",
            user=user,
            intake=intake,
            request_id=request_id,
            metadata={
                "file_id": document.id,
                "document_kind": document.document_kind,
                "reason": clean_reason,
            },
        )
        return {
            "url": url,
            "expires_in": expires_in,
            "download_filename": self._document_download_filename(intake=intake, document=document),
        }
