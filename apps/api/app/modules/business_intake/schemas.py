from __future__ import annotations

from pydantic import BaseModel, Field


class BusinessIntakeStartRequest(BaseModel):
    telegram_user_id: int
    telegram_chat_id: int
    telegram_update_id: int
    referral_code: str | None = Field(default=None, max_length=80)


class BusinessIntakeContactRequest(BaseModel):
    telegram_update_id: int
    telegram_user_id: int
    telegram_chat_id: int
    contact_user_id: int
    contact_phone: str = Field(min_length=6, max_length=32)


class BusinessIntakeSubmitRequest(BaseModel):
    telegram_update_id: int
    telegram_user_id: int
    telegram_chat_id: int
    business_name: str = Field(min_length=2, max_length=160)
    responsible_name: str = Field(min_length=2, max_length=160)
    city: str = Field(min_length=2, max_length=120)
    business_phone: str = Field(min_length=6, max_length=32)
    operation: str
    banks: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    min_amount_usd: str
    max_amount_usd: str
    schedule: str = Field(min_length=2, max_length=240)
    references: list[str] = Field(default_factory=list)


class AdminBusinessIntakeReviewRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    create_business: bool = False
    public_business_name: str | None = Field(default=None, min_length=2, max_length=160)


class AdminBusinessIntakeDeleteRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
