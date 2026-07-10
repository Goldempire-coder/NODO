from __future__ import annotations

from app.modules.businesses.models import BusinessRecord, BusinessVerificationSubmissionRecord, utc_now


class InMemoryBusinessAdminReviewMixin:
    def approve_business(
        self,
        *,
        business: BusinessRecord,
        submission: BusinessVerificationSubmissionRecord,
        admin_user_id: str,
        reason: str,
    ) -> BusinessRecord:
        with self._lock:  # type: ignore[attr-defined]
            now = utc_now()
            business.verification_status = "approved"
            business.approved_at = now
            business.updated_at = now
            submission.status = "approved"
            submission.admin_reviewed_by_user_id = admin_user_id
            submission.admin_reason = reason
            submission.reviewed_at = now
            submission.updated_at = now
            return business

    def reject_business(
        self,
        *,
        business: BusinessRecord,
        submission: BusinessVerificationSubmissionRecord,
        admin_user_id: str,
        reason: str,
    ) -> BusinessRecord:
        with self._lock:  # type: ignore[attr-defined]
            now = utc_now()
            business.verification_status = "rejected"
            business.updated_at = now
            submission.status = "rejected"
            submission.admin_reviewed_by_user_id = admin_user_id
            submission.admin_reason = reason
            submission.reviewed_at = now
            submission.updated_at = now
            return business
