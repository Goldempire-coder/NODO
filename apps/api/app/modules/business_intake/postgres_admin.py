from __future__ import annotations

from app.core.errors import ApiError
from app.modules.business_intake.models import BusinessIntakeRequestRecord
from app.modules.business_intake.repository_common import intake_from_row, jsonb


class PostgresBusinessIntakeAdminMixin:
    def list_intakes(self, *, status: str | None, cursor: str | None, limit: int) -> tuple[list[BusinessIntakeRequestRecord], str | None]:
        sql = "select * from business_intake_requests where true"
        params: list[object] = []
        if status:
            sql += " and status = %s"
            params.append(status)
        if cursor:
            sql += " and created_at < %s"
            params.append(cursor)
        sql += " order by created_at desc limit %s"
        params.append(limit)
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(sql, params).fetchall()
        items = [intake_from_row(row) for row in rows]
        next_cursor = items[-1].created_at.isoformat() if len(items) == limit else None
        return items, next_cursor

    def review(self, *, intake: BusinessIntakeRequestRecord, status: str, admin_user_id: str, reason: str) -> BusinessIntakeRequestRecord:
        if status not in {"accepted", "rejected"}:
            raise ApiError("BUSINESS_INTAKE_STATUS_INVALID", status_code=409)
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                update business_intake_requests
                set status = %s,
                    reviewed_by_admin_id = %s,
                    reviewed_at = now(),
                    admin_reason = %s,
                    updated_at = now()
                where id = %s
                returning *
                """,
                (status, admin_user_id, reason, intake.id),
            ).fetchone()
            conn.commit()
        return intake_from_row(row)

    def admin_update(
        self,
        *,
        intake: BusinessIntakeRequestRecord,
        updates: dict[str, object],
        submit_for_review: bool,
    ) -> BusinessIntakeRequestRecord:
        allowed_columns = {
            "referral_code",
            "contact_phone",
            "business_name",
            "responsible_name",
            "city",
            "business_phone",
            "operation",
            "banks_json",
            "methods_json",
            "min_amount_usd",
            "max_amount_usd",
            "schedule_text",
            "references_json",
        }
        assignments: list[str] = []
        params: list[object] = []
        for column, value in updates.items():
            if column not in allowed_columns:
                raise ApiError("VALIDATION_ERROR", status_code=422)
            assignments.append(f"{column} = %s")
            params.append(jsonb(value) if column in {"banks_json", "methods_json", "references_json"} else value)
        if submit_for_review:
            assignments.extend(["status = 'submitted'", "last_step = 'submitted'", "submitted_at = coalesce(submitted_at, now())"])
        assignments.append("updated_at = now()")
        sql = f"""
            update business_intake_requests
               set {", ".join(assignments)}
             where id = %s
             returning *
        """
        params.append(intake.id)
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(sql, params).fetchone()
            conn.commit()
        return intake_from_row(row)

    def attach_created_business(
        self,
        *,
        intake: BusinessIntakeRequestRecord,
        business_id: str,
        linked_telegram_user_id: int | None = None,
    ) -> BusinessIntakeRequestRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                update business_intake_requests
                set created_business_id = %s,
                    linked_telegram_user_id = %s,
                    updated_at = now()
                where id = %s
                returning *
                """,
                (business_id, linked_telegram_user_id, intake.id),
            ).fetchone()
            conn.commit()
        return intake_from_row(row)

    def delete_intake(self, *, intake_id: str) -> dict[str, int]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            documents_deleted = conn.execute(
                """
                update file_assets
                   set deleted_at = now()
                 where resource_type = 'business_intake'
                   and resource_id = %s
                   and deleted_at is null
                """,
                (intake_id,),
            ).rowcount
            intakes_deleted = conn.execute(
                "delete from business_intake_requests where id = %s",
                (intake_id,),
            ).rowcount
            conn.commit()
        return {"intakes_deleted": intakes_deleted, "documents_deleted": documents_deleted}
