from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.shared.validation import ResourceId, StrictRequestModel


class BusinessCreateRequest(StrictRequestModel):
    business_name: str = Field(min_length=2, max_length=160)
    rif: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=240)
    phone: str | None = Field(default=None, max_length=32)
    country: str = Field(default="VE", min_length=2, max_length=2)


class BusinessUpdateRequest(StrictRequestModel):
    business_name: str | None = Field(default=None, min_length=2, max_length=160)
    rif: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=240)
    phone: str | None = Field(default=None, max_length=32)
    country: str | None = Field(default=None, min_length=2, max_length=2)


class BusinessPaymentMethodInput(StrictRequestModel):
    method_type: str = Field(min_length=1, max_length=32)
    network: str | None = Field(default=None, max_length=32)
    account_value: str = Field(min_length=3, max_length=180)
    holder_name: str = Field(min_length=2, max_length=160)


class BusinessOwnPaymentMethodCreateRequest(StrictRequestModel):
    method_type: Literal["zelle", "usdt_trc20"] = "zelle"
    zelle_account: str | None = Field(default=None, min_length=3, max_length=180)
    account_value: str | None = Field(default=None, min_length=3, max_length=180)
    holder_name: str = Field(min_length=2, max_length=160)


class BusinessOwnPaymentMethodUpdateRequest(StrictRequestModel):
    zelle_account: str | None = Field(default=None, min_length=3, max_length=180)
    account_value: str | None = Field(default=None, min_length=3, max_length=180)
    holder_name: str = Field(min_length=2, max_length=160)


class BusinessAvailabilityUpdateRequest(StrictRequestModel):
    accepting_orders: bool


class BusinessPinSetupRequest(StrictRequestModel):
    pin: str = Field(min_length=4, max_length=6, pattern=r"^[0-9]{4,6}$")
    current_pin: str | None = Field(default=None, min_length=4, max_length=6, pattern=r"^[0-9]{4,6}$")


class BusinessPinVerifyRequest(StrictRequestModel):
    pin: str = Field(min_length=4, max_length=6, pattern=r"^[0-9]{4,6}$")


class BusinessVerificationSubmitPayload(StrictRequestModel):
    business_name: str = Field(min_length=2, max_length=160)
    rif: str = Field(min_length=3, max_length=32)
    address: str = Field(min_length=4, max_length=240)
    phone: str = Field(min_length=6, max_length=32)
    country: str = Field(default="VE", min_length=2, max_length=2)
    document_file_ids: list[ResourceId] = Field(min_length=1, max_length=10)
    payment_methods: list[BusinessPaymentMethodInput] = Field(default_factory=list, max_length=8)


class BusinessVerificationSubmitRequest(StrictRequestModel):
    submitted_data: BusinessVerificationSubmitPayload


class AdminReasonRequest(StrictRequestModel):
    reason: str = Field(max_length=500)


class AdminBusinessCapacityUpdateRequest(StrictRequestModel):
    trust_level: str = Field(max_length=32)
    min_order_amount_usd: Decimal = Field(ge=Decimal("20.00"))
    max_order_amount_usd: Decimal = Field(le=Decimal("2000.00"))
    daily_limit_usd: Decimal = Field(le=Decimal("10000.00"))
    active_order_limit: int = Field(ge=1, le=50)
    reason: str = Field(min_length=1, max_length=500)


class AdminBusinessAccessLinkCreateRequest(StrictRequestModel):
    user_id: ResourceId
    role_in_business: str = Field(default="owner", max_length=32)
    reason: str = Field(min_length=1, max_length=500)


class PendingBusinessesQuery(StrictRequestModel):
    cursor: str | None = Field(default=None, max_length=500)
    limit: int = Field(default=20, ge=1, le=50)
