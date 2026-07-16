from __future__ import annotations

from decimal import Decimal

from app.modules.businesses.models import BusinessRecord, BusinessVerificationSubmissionRecord
from app.modules.businesses.row_mappers import business_from_row


class PostgresBusinessAdminReviewMixin:
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
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                update businesses
                set trust_level = %s,
                    min_order_amount_usd = %s,
                    max_order_amount_usd = %s,
                    daily_limit_usd = %s,
                    active_order_limit = %s,
                    updated_at = now()
                where id = %s
                returning *
                """,
                (
                    trust_level,
                    min_order_amount_usd,
                    max_order_amount_usd,
                    daily_limit_usd,
                    active_order_limit,
                    business.id,
                ),
            ).fetchone()
            conn.commit()
        return business_from_row(row)

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

    def approve_business_from_intake(self, *, business: BusinessRecord) -> BusinessRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                update businesses
                set verification_status = 'approved',
                    approved_at = coalesce(approved_at, now()),
                    updated_at = now()
                where id = %s
                returning *
                """,
                (business.id,),
            ).fetchone()
            conn.commit()
        return business_from_row(row)

    def set_business_verification_status(self, *, business: BusinessRecord, status: str) -> BusinessRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                update businesses
                set verification_status = %s,
                    approved_at = case when %s = 'approved' then coalesce(approved_at, now()) else approved_at end,
                    updated_at = now()
                where id = %s
                returning *
                """,
                (status, status, business.id),
            ).fetchone()
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
