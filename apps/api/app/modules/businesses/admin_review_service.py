from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.businesses.policy import require_admin_mutation, require_admin_view
from app.modules.businesses.presenters import business_payload, file_payload, mask_phone, mask_rif
from app.modules.businesses.state_machine import require_admin_review_allowed
from app.modules.users.models import UserRecord


class BusinessAdminReviewServiceMixin:
    def admin_pending(self, *, user: UserRecord, cursor: str | None, limit: int) -> dict[str, Any]:
        require_admin_view(user)
        self._rate_limit("admin_pending", user)  # type: ignore[attr-defined]
        items, next_cursor = self._repository.list_pending_businesses(cursor=cursor, limit=limit)  # type: ignore[attr-defined]
        return {
            "items": [self._admin_pending_item_payload(business) for business in items],
            "next_cursor": next_cursor,
        }

    def _admin_pending_item_payload(self, business) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        latest = self._repository.get_latest_submission(business.id)  # type: ignore[attr-defined]
        return {
            "id": business.id,
            "business_name": business.business_name,
            "rif_masked": mask_rif(business.rif),
            "phone_masked": mask_phone(business.phone),
            "verification_status": business.verification_status,
            "risk_level": business.risk_level,
            "submitted_at": latest.submitted_at.isoformat() if latest else None,
            "created_at": business.created_at.isoformat(),
        }

    def admin_detail(self, *, user: UserRecord, business_id: str) -> dict[str, Any]:
        require_admin_view(user)
        business = self._business_or_404(business_id)  # type: ignore[attr-defined]
        latest = self._repository.get_latest_submission(business.id)  # type: ignore[attr-defined]
        return {
            "business": business_payload(business, admin=user.role in {"admin", "super_admin"}),
            "latest_submission": self._latest_submission_payload(latest=latest, user=user),
            "documents": [file_payload(file) for file in self._repository.list_files_for_business(business.id)],  # type: ignore[attr-defined]
        }

    def _latest_submission_payload(self, *, latest, user: UserRecord) -> dict[str, Any] | None:  # type: ignore[no-untyped-def]
        if latest is None:
            return None
        return {
            "id": latest.id,
            "status": latest.status,
            "submitted_data": latest.submitted_data_json if user.role in {"admin", "super_admin"} else {},
            "submitted_at": latest.submitted_at.isoformat(),
            "reviewed_at": latest.reviewed_at.isoformat() if latest.reviewed_at else None,
        }

    def signed_document_url(
        self,
        *,
        user: UserRecord,
        business_id: str,
        file_id: str,
        reason: str,
        request_id: str,
    ) -> dict[str, Any]:
        require_admin_mutation(user)
        self._rate_limit("view_url", user)  # type: ignore[attr-defined]
        reason = self._admin_reason_or_error(reason)
        business = self._business_or_404(business_id)  # type: ignore[attr-defined]
        file = self._repository.get_file_for_business(business.id, file_id)  # type: ignore[attr-defined]
        if file is None:
            raise ApiError("BUSINESS_DOCUMENT_NOT_FOUND", status_code=404)
        expires_in = min(self._settings.storage_signed_url_ttl_seconds, 300)  # type: ignore[attr-defined]
        url = self._storage.signed_view_url(storage_path=file.storage_path, expires_in=expires_in)  # type: ignore[attr-defined]
        self._audit.write(  # type: ignore[attr-defined]
            event_type="verification_document_viewed",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="business",
            resource_id=business.id,
            request_id=request_id,
            metadata_json={"file_id": file.id, "reason": reason},
        )
        return {"url": url, "expires_in": expires_in}

    def approve(
        self,
        *,
        user: UserRecord,
        business_id: str,
        reason: str,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        return self._review_business(
            user=user,
            business_id=business_id,
            reason=reason,
            request_id=request_id,
            idempotency_key=idempotency_key,
            decision="approved",
        )

    def reject(
        self,
        *,
        user: UserRecord,
        business_id: str,
        reason: str,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        return self._review_business(
            user=user,
            business_id=business_id,
            reason=reason,
            request_id=request_id,
            idempotency_key=idempotency_key,
            decision="rejected",
        )

    def _review_business(
        self,
        *,
        user: UserRecord,
        business_id: str,
        reason: str,
        request_id: str,
        idempotency_key: str | None,
        decision: str,
    ) -> dict[str, Any]:
        require_admin_mutation(user)
        self._rate_limit("approve" if decision == "approved" else "reject", user)  # type: ignore[attr-defined]
        reason = self._admin_reason_or_error(reason)
        business = self._business_or_404(business_id)  # type: ignore[attr-defined]

        def compute() -> dict[str, Any]:
            return self._compute_review_business(
                user=user,
                business=business,
                decision=decision,
                reason=reason,
                request_id=request_id,
            )

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            idempotency_key,
            payload={"id": business_id, "reason": reason},
            compute=compute,
        )

    def _compute_review_business(
        self,
        *,
        user: UserRecord,
        business,
        decision: str,
        reason: str,
        request_id: str,
    ) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        submission = require_admin_review_allowed(
            business,
            self._repository.get_latest_submission(business.id),  # type: ignore[attr-defined]
        )
        if decision == "approved":
            updated = self._repository.approve_business(  # type: ignore[attr-defined]
                business=business,
                submission=submission,
                admin_user_id=user.id,
                reason=reason,
            )
            payload = {
                "id": updated.id,
                "verification_status": updated.verification_status,
                "approved_at": updated.approved_at.isoformat() if updated.approved_at else None,
            }
        else:
            updated = self._repository.reject_business(  # type: ignore[attr-defined]
                business=business,
                submission=submission,
                admin_user_id=user.id,
                reason=reason,
            )
            payload = {"id": updated.id, "verification_status": updated.verification_status}

        self._audit.write(  # type: ignore[attr-defined]
            event_type=f"business_{decision}",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="business",
            resource_id=business.id,
            request_id=request_id,
            metadata_json={"reason": reason},
        )
        return {"business": payload}

    def _admin_reason_or_error(self, reason: str) -> str:
        reason = reason.strip()
        if not reason:
            raise ApiError("ADMIN_REASON_REQUIRED", status_code=400)
        return reason
