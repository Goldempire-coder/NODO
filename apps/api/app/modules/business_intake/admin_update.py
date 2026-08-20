from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.business_intake.conversation_validation import (
    clean_text,
    normalize_methods,
    normalize_operation,
    normalize_social_references,
    split_clean_list,
    validated_amount_range,
    validated_positive_amount,
)
from app.modules.business_intake.policy import require_admin_mutation
from app.modules.business_intake.schemas import AdminBusinessIntakeUpdateRequest
from app.modules.credits.referral_codes import normalize_referral_code
from app.modules.users.models import UserRecord


class BusinessIntakeAdminUpdateMixin:
    def update(
        self,
        *,
        user: UserRecord,
        intake_id: str,
        payload: AdminBusinessIntakeUpdateRequest,
        request_id: str,
    ) -> dict[str, Any]:
        require_admin_mutation(user)
        self._rate_limit("admin_update", user.id)  # type: ignore[attr-defined]
        current = self._get_intake(intake_id)  # type: ignore[attr-defined]
        if current.created_business_id or current.status == "accepted":
            raise ApiError("BUSINESS_INTAKE_STATUS_INVALID", status_code=409)
        updates = self._validated_updates(current=current, payload=payload)
        if not updates and not payload.submit_for_review:
            raise ApiError("VALIDATION_ERROR", status_code=422)
        updated = self._repository.admin_update(  # type: ignore[attr-defined]
            intake=current,
            updates=updates,
            submit_for_review=payload.submit_for_review,
        )
        self._write_admin_audit(  # type: ignore[attr-defined]
            event_type="business_intake_admin_updated",
            user=user,
            intake=updated,
            request_id=request_id,
            metadata={
                "updated_fields": sorted(updates.keys()),
                "submit_for_review": payload.submit_for_review,
                "reason": "admin_manual_intake_update",
            },
        )
        return {"intake": self._public_intake(updated)}  # type: ignore[attr-defined]

    def _validated_updates(
        self,
        *,
        current,  # type: ignore[no-untyped-def]
        payload: AdminBusinessIntakeUpdateRequest,
    ) -> dict[str, Any]:
        provided = payload.model_dump(exclude_unset=True)
        updates: dict[str, Any] = {}
        scalar_fields = {
            "referral_code": ("referral_code", 1, 80),
            "contact_phone": ("contact_phone", 6, 32),
            "business_name": ("business_name", 2, 160),
            "business_tax_id": ("business_tax_id", 3, 64),
            "responsible_name": ("responsible_name", 2, 160),
            "responsible_id_number": ("responsible_id_number", 3, 64),
            "city": ("city", 2, 120),
            "business_phone": ("business_phone", 6, 32),
            "schedule": ("schedule_text", 2, 240),
        }
        for request_field, (record_field, min_length, max_length) in scalar_fields.items():
            value = provided.get(request_field)
            if value is not None:
                cleaned = clean_text(value, min_length=min_length, max_length=max_length)
                updates[record_field] = normalize_referral_code(cleaned) if request_field == "referral_code" else cleaned
        if provided.get("operation") is not None:
            updates["operation"] = normalize_operation(str(provided["operation"]))
        if provided.get("methods") is not None:
            updates["methods_json"] = normalize_methods(", ".join(provided["methods"] or []))
        if provided.get("banks") is not None:
            updates["banks_json"] = split_clean_list(", ".join(provided["banks"] or []))
        if provided.get("references") is not None:
            updates["references_json"] = normalize_social_references(", ".join(provided["references"] or []))
        if "min_amount_usd" in provided or "max_amount_usd" in provided:
            min_candidate = provided.get("min_amount_usd") or updates.get("min_amount_usd") or current.min_amount_usd
            max_candidate = provided.get("max_amount_usd") or updates.get("max_amount_usd") or current.max_amount_usd
            if min_candidate is None or max_candidate is None:
                raise ApiError("VALIDATION_ERROR", status_code=422)
            min_amount, max_amount = validated_amount_range(str(min_candidate), str(max_candidate))
            updates["min_amount_usd"] = min_amount
            updates["max_amount_usd"] = max_amount
        if "daily_limit_usd" in provided and provided["daily_limit_usd"] is not None:
            updates["daily_limit_usd"] = validated_positive_amount(str(provided["daily_limit_usd"]))
        return updates
