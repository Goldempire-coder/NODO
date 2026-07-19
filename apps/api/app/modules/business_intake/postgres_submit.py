from __future__ import annotations

from typing import Any

from app.modules.business_intake.models import BusinessIntakeRequestRecord
from app.modules.business_intake.repository_common import decimal_text, intake_from_row, jsonb


class PostgresBusinessIntakeSubmitMixin:
    def submit(
        self,
        *,
        intake: BusinessIntakeRequestRecord,
        update_id: int,
        business_name: str,
        business_tax_id: str | None,
        responsible_name: str,
        responsible_id_number: str | None,
        city: str,
        business_phone: str,
        operation: str,
        banks: list[str],
        methods: list[str],
        min_amount_usd: str,
        max_amount_usd: str,
        daily_limit_usd: str,
        schedule: str,
        references: list[str],
    ) -> BusinessIntakeRequestRecord:
        submit_fields = self._submit_fields(
            update_id=update_id,
            business_name=business_name,
            business_tax_id=business_tax_id,
            responsible_name=responsible_name,
            responsible_id_number=responsible_id_number,
            city=city,
            business_phone=business_phone,
            operation=operation,
            banks=banks,
            methods=methods,
            min_amount_usd=min_amount_usd,
            max_amount_usd=max_amount_usd,
            daily_limit_usd=daily_limit_usd,
            schedule=schedule,
            references=references,
        )
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = self._mark_intake_submitted(conn, intake_id=intake.id, submit_fields=submit_fields)
            conn.commit()
        return intake_from_row(row)

    def _submit_fields(
        self,
        *,
        update_id: int,
        business_name: str,
        business_tax_id: str | None,
        responsible_name: str,
        responsible_id_number: str | None,
        city: str,
        business_phone: str,
        operation: str,
        banks: list[str],
        methods: list[str],
        min_amount_usd: str,
        max_amount_usd: str,
        daily_limit_usd: str,
        schedule: str,
        references: list[str],
    ) -> dict[str, Any]:
        return {
            "update_id": update_id,
            "business_name": business_name,
            "business_tax_id": business_tax_id,
            "responsible_name": responsible_name,
            "responsible_id_number": responsible_id_number,
            "city": city,
            "business_phone": business_phone,
            "operation": operation,
            "banks_json": jsonb(banks),
            "methods_json": jsonb(methods),
            "min_amount_usd": decimal_text(min_amount_usd),
            "max_amount_usd": decimal_text(max_amount_usd),
            "daily_limit_usd": decimal_text(daily_limit_usd),
            "schedule_text": schedule,
            "references_json": jsonb(references),
        }

    def _mark_intake_submitted(self, conn, *, intake_id: str, submit_fields: dict[str, Any]):  # type: ignore[no-untyped-def]
        return conn.execute(
            """
            update business_intake_requests
            set status = 'submitted',
                last_update_id = %s,
                last_step = 'submitted',
                business_name = %s,
                business_tax_id = %s,
                responsible_name = %s,
                responsible_id_number = %s,
                city = %s,
                business_phone = %s,
                operation = %s,
                banks_json = %s,
                methods_json = %s,
                min_amount_usd = %s,
                max_amount_usd = %s,
                daily_limit_usd = %s,
                schedule_text = %s,
                references_json = %s,
                submitted_at = coalesce(submitted_at, now()),
                updated_at = now()
            where id = %s
            returning *
            """,
            (
                submit_fields["update_id"],
                submit_fields["business_name"],
                submit_fields["business_tax_id"],
                submit_fields["responsible_name"],
                submit_fields["responsible_id_number"],
                submit_fields["city"],
                submit_fields["business_phone"],
                submit_fields["operation"],
                submit_fields["banks_json"],
                submit_fields["methods_json"],
                submit_fields["min_amount_usd"],
                submit_fields["max_amount_usd"],
                submit_fields["daily_limit_usd"],
                submit_fields["schedule_text"],
                submit_fields["references_json"],
                intake_id,
            ),
        ).fetchone()
