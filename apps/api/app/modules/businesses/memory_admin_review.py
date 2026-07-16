from __future__ import annotations

from decimal import Decimal

from app.modules.businesses.models import BusinessRecord, BusinessVerificationSubmissionRecord, utc_now


class InMemoryBusinessAdminReviewMixin:
    def update_business_capacity(
        self,
        *,
        business: BusinessRecord,
        trust_level: str,
        min_order_amount_usd: Decimal,
        max_order_amount_usd: Decimal,
        daily_limit_usd: Decimal,
        active_order_limit: int,
    ) -> BusinessRecord:
        with self._lock:  # type: ignore[attr-defined]
            business.trust_level = trust_level
            business.min_order_amount_usd = min_order_amount_usd
            business.max_order_amount_usd = max_order_amount_usd
            business.daily_limit_usd = daily_limit_usd
            business.active_order_limit = active_order_limit
            business.updated_at = utc_now()
            return business

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

    def approve_business_from_intake(self, *, business: BusinessRecord) -> BusinessRecord:
        with self._lock:  # type: ignore[attr-defined]
            now = utc_now()
            business.verification_status = "approved"
            business.approved_at = business.approved_at or now
            business.updated_at = now
            return business

    def set_business_verification_status(self, *, business: BusinessRecord, status: str) -> BusinessRecord:
        with self._lock:  # type: ignore[attr-defined]
            now = utc_now()
            business.verification_status = status
            if status == "approved":
                business.approved_at = business.approved_at or now
            business.updated_at = now
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
