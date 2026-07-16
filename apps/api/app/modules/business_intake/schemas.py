from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.shared.validation import StrictRequestModel


IntakeListItem = Annotated[str, Field(min_length=1, max_length=160)]


class BusinessIntakeStartRequest(StrictRequestModel):
    telegram_user_id: int
    telegram_chat_id: int
    telegram_update_id: int
    referral_code: str | None = Field(default=None, max_length=80)


class BusinessIntakeContactRequest(StrictRequestModel):
    telegram_update_id: int
    telegram_user_id: int
    telegram_chat_id: int
    contact_user_id: int
    contact_phone: str = Field(min_length=6, max_length=32)


class BusinessIntakeSubmitRequest(StrictRequestModel):
    telegram_update_id: int
    telegram_user_id: int
    telegram_chat_id: int
    business_name: str = Field(min_length=2, max_length=160)
    responsible_name: str = Field(min_length=2, max_length=160)
    city: str = Field(min_length=2, max_length=120)
    business_phone: str = Field(min_length=6, max_length=32)
    operation: str = Field(min_length=1, max_length=32)
    banks: list[IntakeListItem] = Field(default_factory=list, max_length=20)
    methods: list[IntakeListItem] = Field(default_factory=list, max_length=10)
    min_amount_usd: str = Field(min_length=1, max_length=32)
    max_amount_usd: str = Field(min_length=1, max_length=32)
    schedule: str = Field(min_length=2, max_length=240)
    references: list[IntakeListItem] = Field(default_factory=list, max_length=10)


class AdminBusinessIntakeReviewRequest(StrictRequestModel):
    reason: str = Field(min_length=1, max_length=500)
    create_business: bool = False
    approve_business: bool = False
    public_business_name: str | None = Field(default=None, min_length=2, max_length=160)


class AdminBusinessIntakeDeleteRequest(StrictRequestModel):
    reason: str = Field(min_length=1, max_length=500)
