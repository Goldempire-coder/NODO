from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.business_intake.models import INTAKE_STEPS, BusinessIntakeRequestRecord
from app.modules.business_intake.repository_common import decimal_text, intake_from_row, jsonb


class PostgresBusinessIntakeConversationMixin:
    def update_conversation(
        self,
        *,
        intake: BusinessIntakeRequestRecord,
        update_id: int,
        last_step: str,
        fields: dict[str, Any],
    ) -> BusinessIntakeRequestRecord:
        self._validate_conversation_update(last_step=last_step, fields=fields)
        assignments, params = self._conversation_update_assignments(update_id=update_id, last_step=last_step, fields=fields)
        params.append(intake.id)
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                f"""
                update business_intake_requests
                set {', '.join(assignments)}
                where id = %s
                returning *
                """,
                params,
            ).fetchone()
            conn.commit()
        return intake_from_row(row)

    def _validate_conversation_update(self, *, last_step: str, fields: dict[str, Any]) -> None:
        if last_step not in INTAKE_STEPS:
            raise ApiError("BOT_INPUT_INVALID", status_code=400)
        invalid = set(fields) - self._conversation_update_allowed_fields()
        if invalid:
            raise ApiError("BOT_INPUT_INVALID", status_code=400)

    def _conversation_update_allowed_fields(self) -> set[str]:
        return {
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
            "status",
            "submitted_at",
        }

    def _conversation_update_assignments(self, *, update_id: int, last_step: str, fields: dict[str, Any]) -> tuple[list[str], list[Any]]:
        assignments = ["last_update_id = %s", "last_step = %s", "updated_at = now()"]
        params: list[Any] = [update_id, last_step]
        for key, value in fields.items():
            self._append_conversation_assignment(assignments, params, key=key, value=value)
        return assignments, params

    def _append_conversation_assignment(self, assignments: list[str], params: list[Any], *, key: str, value: Any) -> None:
        if key in {"banks_json", "methods_json", "references_json"}:
            assignments.append(f"{key} = %s")
            params.append(jsonb(value))
        elif key in {"min_amount_usd", "max_amount_usd", "daily_limit_usd"}:
            assignments.append(f"{key} = %s")
            params.append(decimal_text(value))
        elif key == "submitted_at":
            assignments.append("submitted_at = coalesce(submitted_at, now())")
        else:
            assignments.append(f"{key} = %s")
            params.append(value)

    def mark_update_processed(self, *, intake: BusinessIntakeRequestRecord, update_id: int, last_step: str) -> BusinessIntakeRequestRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                update business_intake_requests
                set last_update_id = %s, last_step = %s, updated_at = now()
                where id = %s
                returning *
                """,
                (update_id, last_step, intake.id),
            ).fetchone()
            conn.commit()
        return intake_from_row(row)
