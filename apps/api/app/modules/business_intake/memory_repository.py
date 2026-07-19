from __future__ import annotations

from threading import RLock

from app.core.errors import ApiError
from app.modules.business_intake.memory_conversation import InMemoryBusinessIntakeConversationMixin
from app.modules.business_intake.memory_documents import InMemoryBusinessIntakeDocumentsMixin
from app.modules.business_intake.models import (
    INTAKE_STATUSES,
    BusinessIntakeDocumentRecord,
    BusinessIntakeRequestRecord,
    utc_now,
)
from app.modules.business_intake.repository_common import decimal_text


class InMemoryBusinessIntakeRepository(InMemoryBusinessIntakeConversationMixin, InMemoryBusinessIntakeDocumentsMixin):
    def __init__(self) -> None:
        self._lock = RLock()
        self.intakes: dict[str, BusinessIntakeRequestRecord] = {}
        self.documents: dict[str, BusinessIntakeDocumentRecord] = {}

    def get(self, intake_id: str) -> BusinessIntakeRequestRecord | None:
        return self.intakes.get(intake_id)

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
        with self._lock:
            now = utc_now()
            intake.status = "submitted"
            intake.last_update_id = update_id
            intake.last_step = "submitted"
            intake.business_name = business_name
            intake.business_tax_id = business_tax_id
            intake.responsible_name = responsible_name
            intake.responsible_id_number = responsible_id_number
            intake.city = city
            intake.business_phone = business_phone
            intake.operation = operation
            intake.banks_json = banks
            intake.methods_json = methods
            intake.min_amount_usd = decimal_text(min_amount_usd)
            intake.max_amount_usd = decimal_text(max_amount_usd)
            intake.daily_limit_usd = decimal_text(daily_limit_usd)
            intake.schedule_text = schedule
            intake.references_json = references
            intake.submitted_at = intake.submitted_at or now
            intake.updated_at = now
            return intake

    def list_intakes(self, *, status: str | None, cursor: str | None, limit: int) -> tuple[list[BusinessIntakeRequestRecord], str | None]:
        items = [intake for intake in self.intakes.values() if status is None or intake.status == status]
        items.sort(key=lambda item: item.created_at, reverse=True)
        if cursor:
            items = [item for item in items if item.created_at.isoformat() < cursor]
        page = items[:limit]
        next_cursor = page[-1].created_at.isoformat() if len(page) == limit else None
        return page, next_cursor

    def review(self, *, intake: BusinessIntakeRequestRecord, status: str, admin_user_id: str, reason: str) -> BusinessIntakeRequestRecord:
        if status not in INTAKE_STATUSES or status not in {"accepted", "rejected"}:
            raise ApiError("BUSINESS_INTAKE_STATUS_INVALID", status_code=409)
        with self._lock:
            now = utc_now()
            intake.status = status
            intake.reviewed_by_admin_id = admin_user_id
            intake.reviewed_at = now
            intake.admin_reason = reason
            intake.updated_at = now
            return intake

    def admin_update(
        self,
        *,
        intake: BusinessIntakeRequestRecord,
        updates: dict[str, object],
        submit_for_review: bool,
    ) -> BusinessIntakeRequestRecord:
        with self._lock:
            now = utc_now()
            for field, value in updates.items():
                setattr(intake, field, value)
            if submit_for_review:
                intake.status = "submitted"
                intake.last_step = "submitted"
                intake.submitted_at = intake.submitted_at or now
            intake.updated_at = now
            return intake

    def attach_created_business(
        self,
        *,
        intake: BusinessIntakeRequestRecord,
        business_id: str,
        linked_telegram_user_id: int | None = None,
    ) -> BusinessIntakeRequestRecord:
        with self._lock:
            intake.created_business_id = business_id
            intake.linked_telegram_user_id = linked_telegram_user_id
            intake.updated_at = utc_now()
            return intake

    def delete_intake(self, *, intake_id: str) -> dict[str, int]:
        with self._lock:
            documents_deleted = 0
            for document in self.documents.values():
                if document.resource_type == "business_intake" and document.resource_id == intake_id and document.deleted_at is None:
                    document.deleted_at = utc_now()
                    documents_deleted += 1
            intakes_deleted = 1 if self.intakes.pop(intake_id, None) is not None else 0
            return {"intakes_deleted": intakes_deleted, "documents_deleted": documents_deleted}
