from __future__ import annotations

from app.core.errors import ApiError
from app.modules.business_intake.conversation import INTAKE_CONFIRMATION
from app.modules.business_intake.conversation_validation import validated_amount_range
from app.modules.business_intake.models import INTAKE_OPERATIONS
from app.modules.business_intake.public_documents import BusinessIntakePublicDocumentsMixin
from app.modules.business_intake.schemas import (
    BusinessIntakeContactRequest,
    BusinessIntakeStartRequest,
    BusinessIntakeSubmitRequest,
)


class BusinessIntakePublicActionsMixin(BusinessIntakePublicDocumentsMixin):
    def start(self, *, payload: BusinessIntakeStartRequest, request_id: str) -> dict[str, object]:
        self._rate_limit("start", str(payload.telegram_user_id))  # type: ignore[attr-defined]
        self._ensure_applicant_user(payload.telegram_user_id)  # type: ignore[attr-defined]
        existing = self._repository.get_by_update(  # type: ignore[attr-defined]
            telegram_chat_id=payload.telegram_chat_id,
            update_id=payload.telegram_update_id,
        )
        intake = self._repository.create_or_get_draft(  # type: ignore[attr-defined]
            telegram_user_id=payload.telegram_user_id,
            telegram_chat_id=payload.telegram_chat_id,
            update_id=payload.telegram_update_id,
            referral_code=payload.referral_code,
        )
        if existing is None:
            self._write_audit(event_type="business_intake_started", intake=intake, request_id=request_id)  # type: ignore[attr-defined]
        return {"id": intake.id, "status": intake.status, "last_step": intake.last_step}

    def contact(self, *, intake_id: str, payload: BusinessIntakeContactRequest, request_id: str) -> dict[str, object]:
        self._rate_limit("contact", str(payload.telegram_user_id))  # type: ignore[attr-defined]
        if payload.contact_user_id != payload.telegram_user_id:
            raise ApiError("BOT_CONTACT_REQUIRED", status_code=400)
        intake = self._get_intake(intake_id)  # type: ignore[attr-defined]
        self._validate_intake_context(intake=intake, telegram_user_id=payload.telegram_user_id, telegram_chat_id=payload.telegram_chat_id)  # type: ignore[attr-defined]
        if intake.last_update_id == payload.telegram_update_id:
            return {"id": intake.id, "status": intake.status, "last_step": intake.last_step}
        if intake.status != "draft":
            raise ApiError("BUSINESS_INTAKE_STATUS_INVALID", status_code=409)
        updated = self._repository.save_contact(intake=intake, update_id=payload.telegram_update_id, contact_phone=payload.contact_phone)  # type: ignore[attr-defined]
        self._write_audit(event_type="business_intake_contact_shared", intake=updated, request_id=request_id)  # type: ignore[attr-defined]
        return {"id": updated.id, "status": updated.status, "last_step": updated.last_step}

    def submit(self, *, intake_id: str, payload: BusinessIntakeSubmitRequest, request_id: str) -> dict[str, object]:
        self._rate_limit("submit", str(payload.telegram_user_id))  # type: ignore[attr-defined]
        if payload.operation not in INTAKE_OPERATIONS:
            raise ApiError("VALIDATION_ERROR", status_code=422)
        if any(method not in {"zelle", "usdt_trc20"} for method in payload.methods):
            raise ApiError("VALIDATION_ERROR", status_code=422)
        min_amount_usd, max_amount_usd = validated_amount_range(payload.min_amount_usd, payload.max_amount_usd)
        intake = self._get_intake(intake_id)  # type: ignore[attr-defined]
        self._validate_intake_context(intake=intake, telegram_user_id=payload.telegram_user_id, telegram_chat_id=payload.telegram_chat_id)  # type: ignore[attr-defined]
        if intake.last_update_id == payload.telegram_update_id and intake.status == "submitted":
            return {"id": intake.id, "status": intake.status, "message": INTAKE_CONFIRMATION}
        if intake.status != "draft":
            raise ApiError("BUSINESS_INTAKE_STATUS_INVALID", status_code=409)
        if not intake.contact_phone:
            raise ApiError("BOT_CONTACT_REQUIRED", status_code=400)
        updated = self._repository.submit(  # type: ignore[attr-defined]
            intake=intake,
            update_id=payload.telegram_update_id,
            business_name=payload.business_name,
            responsible_name=payload.responsible_name,
            city=payload.city,
            business_phone=payload.business_phone,
            operation=payload.operation,
            banks=payload.banks,
            methods=payload.methods,
            min_amount_usd=min_amount_usd,
            max_amount_usd=max_amount_usd,
            schedule=payload.schedule,
            references=payload.references,
        )
        self._write_audit(event_type="business_intake_submitted", intake=updated, request_id=request_id)  # type: ignore[attr-defined]
        return {"id": updated.id, "status": updated.status, "message": INTAKE_CONFIRMATION}
