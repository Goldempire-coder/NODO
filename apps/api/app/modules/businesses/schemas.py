from __future__ import annotations

from pydantic import BaseModel, Field


class BusinessCreateRequest(BaseModel):
    business_name: str = Field(min_length=2, max_length=160)
    rif: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=240)
    phone: str | None = Field(default=None, max_length=32)
    country: str = Field(default="VE", min_length=2, max_length=2)


class BusinessUpdateRequest(BaseModel):
    business_name: str | None = Field(default=None, min_length=2, max_length=160)
    rif: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=240)
    phone: str | None = Field(default=None, max_length=32)
    country: str | None = Field(default=None, min_length=2, max_length=2)


class BusinessPaymentMethodInput(BaseModel):
    method_type: str
    network: str | None = None
    account_value: str = Field(min_length=3, max_length=180)
    holder_name: str = Field(min_length=2, max_length=160)


class BusinessVerificationSubmitPayload(BaseModel):
    business_name: str = Field(min_length=2, max_length=160)
    rif: str = Field(min_length=3, max_length=32)
    address: str = Field(min_length=4, max_length=240)
    phone: str = Field(min_length=6, max_length=32)
    country: str = Field(default="VE", min_length=2, max_length=2)
    document_file_ids: list[str] = Field(min_length=1)
    payment_methods: list[BusinessPaymentMethodInput] = Field(default_factory=list)


class BusinessVerificationSubmitRequest(BaseModel):
    submitted_data: BusinessVerificationSubmitPayload


class AdminReasonRequest(BaseModel):
    reason: str = Field(max_length=500)


class AdminBusinessAccessLinkCreateRequest(BaseModel):
    user_id: str = Field(min_length=1)
    role_in_business: str = Field(default="owner", max_length=32)
    reason: str = Field(min_length=1, max_length=500)


class PendingBusinessesQuery(BaseModel):
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=50)
