from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.business_intake.conversation_validation import (
    clean_text,
    normalize_methods,
    normalize_operation,
    split_clean_list,
    validated_amount_range,
)
from app.modules.business_intake.models import BusinessIntakeRequestRecord


def conversation_fields_for_step(
    *,
    intake: BusinessIntakeRequestRecord,
    current_step: str,
    cleaned: str,
    raw_text: str,
) -> tuple[dict[str, Any], str]:
    fields: dict[str, Any]
    next_step: str
    if current_step == "awaiting_referral_code":
        fields = {"referral_code": cleaned}
        next_step = "awaiting_whatsapp_phone"
    elif current_step == "awaiting_whatsapp_phone":
        fields = {"contact_phone": clean_text(raw_text, min_length=6, max_length=32)}
        next_step = "awaiting_business_name"
    elif current_step == "awaiting_business_name":
        fields = {"business_name": cleaned}
        next_step = "awaiting_responsible_name"
    elif current_step == "awaiting_responsible_name":
        fields = {"responsible_name": cleaned}
        next_step = "awaiting_city"
    elif current_step == "awaiting_city":
        fields = {"city": cleaned}
        next_step = "awaiting_business_phone"
    elif current_step == "awaiting_business_phone":
        fields = {"business_phone": clean_text(raw_text, min_length=6, max_length=32)}
        next_step = "awaiting_operation"
    elif current_step == "awaiting_operation":
        fields = {"operation": normalize_operation(cleaned)}
        next_step = "awaiting_banks"
    elif current_step == "awaiting_banks":
        fields = {"banks_json": split_clean_list(cleaned)}
        next_step = "awaiting_methods"
    elif current_step == "awaiting_methods":
        fields = {"methods_json": normalize_methods(cleaned)}
        next_step = "awaiting_min_amount"
    elif current_step == "awaiting_min_amount":
        min_amount, _ = validated_amount_range(cleaned, cleaned)
        fields = {"min_amount_usd": min_amount}
        next_step = "awaiting_max_amount"
    elif current_step == "awaiting_max_amount":
        if intake.min_amount_usd is None:
            raise ApiError("BOT_INPUT_INVALID", status_code=400)
        min_amount, max_amount = validated_amount_range(intake.min_amount_usd, cleaned)
        fields = {"min_amount_usd": min_amount, "max_amount_usd": max_amount}
        next_step = "awaiting_schedule"
    elif current_step == "awaiting_schedule":
        fields = {"schedule_text": cleaned}
        next_step = "awaiting_references"
    elif current_step == "awaiting_references":
        fields = {"references_json": split_clean_list(cleaned)}
        next_step = "awaiting_documents"
    else:
        raise ApiError("BOT_INPUT_INVALID", status_code=400)
    return fields, next_step
