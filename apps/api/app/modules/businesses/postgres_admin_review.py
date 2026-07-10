from __future__ import annotations

from app.modules.businesses.models import BusinessRecord, BusinessVerificationSubmissionRecord
from app.modules.businesses.row_mappers import business_from_row


class PostgresBusinessAdminReviewMixin:
    def approve_business(
        self,
        *,
        business: BusinessRecord,
        submission: BusinessVerificationSubmissionRecord,
        admin_user_id: str,
        reason: str,
    ) -> BusinessRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                update businesses set verification_status = 'approved', approved_at = now(), updated_at = now()
                where id = %s returning *
                """,
                (business.id,),
            ).fetchone()
            conn.execute(
                """
                update business_verification_submissions
                set status = 'approved', admin_reviewed_by_user_id = %s, admin_reason = %s, reviewed_at = now(), updated_at = now()
                where id = %s
                """,
                (admin_user_id, reason, submission.id),
            )
            conn.commit()
        return business_from_row(row)

    def reject_business(
        self,
        *,
        business: BusinessRecord,
        submission: BusinessVerificationSubmissionRecord,
        admin_user_id: str,
        reason: str,
    ) -> BusinessRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                "update businesses set verification_status = 'rejected', updated_at = now() where id = %s returning *",
                (business.id,),
            ).fetchone()
            conn.execute(
                """
                update business_verification_submissions
                set status = 'rejected', admin_reviewed_by_user_id = %s, admin_reason = %s, reviewed_at = now(), updated_at = now()
                where id = %s
                """,
                (admin_user_id, reason, submission.id),
            )
            conn.commit()
        return business_from_row(row)
