from __future__ import annotations

from app.core.errors import ApiError
from app.modules.business_intake.admin_list_priority import (
    decode_intake_list_cursor,
    encode_intake_list_cursor,
    normalize_readiness_filter,
    priority_for_ready,
)
from app.modules.business_intake.intake_requirements import intake_review_metadata
from app.modules.business_intake.models import BusinessIntakeRequestRecord
from app.modules.business_intake.repository_common import intake_from_row, jsonb


class PostgresBusinessIntakeAdminMixin:
    def _intake_from_admin_list_row(self, row) -> BusinessIntakeRequestRecord:  # type: ignore[no-untyped-def]
        intake = intake_from_row(row)
        ready, missing_count = intake_review_metadata(intake, document_count=int(row["document_count"] or 0))
        intake.ready_for_review = ready
        intake.review_missing_count = missing_count
        return intake

    def list_intakes(self, *, status: str | None, cursor: str | None, limit: int, readiness: str | None = None) -> tuple[list[BusinessIntakeRequestRecord], str | None]:
        readiness_filter = normalize_readiness_filter(readiness)
        ready_case = """
            case when coalesce(referral_code, '') <> ''
                  and coalesce(contact_phone, '') <> ''
                  and coalesce(business_name, '') <> ''
                  and coalesce(business_tax_id, '') <> ''
                  and coalesce(responsible_name, '') <> ''
                  and coalesce(responsible_id_number, '') <> ''
                  and coalesce(business_phone, '') <> ''
                  and min_amount_usd is not null
                  and max_amount_usd is not null
                  and daily_limit_usd is not null
                  and jsonb_array_length(coalesce(references_json, '[]'::jsonb)) > 0
                  and document_count > 0
                 then 0 else 1 end
        """
        sql = f"""
            with ranked as (
                select business_intake_requests.*,
                       (
                           select count(*)
                             from file_assets
                            where file_assets.resource_type = 'business_intake'
                              and file_assets.resource_id = business_intake_requests.id
                              and file_assets.deleted_at is null
                       ) as document_count
                  from business_intake_requests
                 where true
            ),
            prioritized as (
                select ranked.*, {ready_case} as review_priority
                  from ranked
            )
            select *
              from prioritized
             where true
        """
        params: list[object] = []
        if status:
            sql += " and status = %s"
            params.append(status)
        if readiness_filter == "ready":
            sql += " and review_priority = 0"
        elif readiness_filter == "needs_info":
            sql += " and review_priority = 1"
        if cursor:
            position = decode_intake_list_cursor(cursor)
            sql += """
                and (
                    review_priority > %s
                    or (review_priority = %s and created_at < %s)
                    or (review_priority = %s and created_at = %s and id < %s)
                )
            """
            params.extend([position.priority, position.priority, position.created_at, position.priority, position.created_at, position.item_id])
        sql += " order by review_priority asc, created_at desc, id desc limit %s"
        params.append(limit + 1)
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(sql, params).fetchall()
        items = [self._intake_from_admin_list_row(row) for row in rows]
        page = items[:limit]
        next_cursor = (
            encode_intake_list_cursor(
                priority=priority_for_ready(page[-1].ready_for_review is True),
                created_at=page[-1].created_at,
                item_id=page[-1].id,
            )
            if len(items) > limit
            else None
        )
        return page, next_cursor

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
            "business_tax_id",
            "responsible_name",
            "responsible_id_number",
            "city",
            "business_phone",
            "operation",
            "banks_json",
            "methods_json",
            "min_amount_usd",
            "max_amount_usd",
            "daily_limit_usd",
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
