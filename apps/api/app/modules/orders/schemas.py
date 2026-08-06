from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field, StrictBool, StrictInt, field_validator, model_validator

from app.modules.orders.integrity import canonical_network, canonical_transaction_hash
from app.modules.orders.receiver_details import (
    normalize_bank,
    normalize_document,
    normalize_holder,
    normalize_phone,
)
from app.shared.validation import ResourceId, StrictRequestModel


class ReceiverData(StrictRequestModel):
    bank: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=7, max_length=32)
    document: str = Field(min_length=4, max_length=32)
    holder: str = Field(min_length=2, max_length=120)


class ReceiverDetailsRequest(StrictRequestModel):
    bank: str = Field(min_length=4, max_length=4)
    phone: str = Field(min_length=7, max_length=32)
    document: str = Field(min_length=6, max_length=16)
    holder: str = Field(min_length=2, max_length=120)

    @field_validator("bank")
    @classmethod
    def validate_bank(cls, value: str) -> str:
        return normalize_bank(value)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("document")
    @classmethod
    def validate_document(cls, value: str) -> str:
        return normalize_document(value)

    @field_validator("holder")
    @classmethod
    def validate_holder(cls, value: str) -> str:
        return normalize_holder(value)


class OrderCreateRequest(StrictRequestModel):
    ad_id: ResourceId
    amount_usd: Decimal = Field(ge=20, max_digits=12, decimal_places=2)
    expected_rate_bs_per_usd: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=18,
        decimal_places=6,
    )
    receiver_data: ReceiverData | None = None


class OrderActionRequest(StrictRequestModel):
    reason: str | None = Field(default=None, max_length=500)


class OrderCancelRequest(StrictRequestModel):
    reason: Literal[
        "business_not_responding",
        "business_unavailable",
        "customer_mistake",
        "choose_another_business",
    ] = "choose_another_business"
    payment_not_sent_confirmed: StrictBool = False


class OrderRatingRequest(StrictRequestModel):
    stars: StrictInt = Field(ge=1, le=5)


class PaymentReportRequest(StrictRequestModel):
    payment_type: str = Field(pattern="^(zelle|usdt_trc20)$")
    payment_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_reference: str | None = Field(default=None, max_length=120)
    payment_sender_name: str | None = Field(default=None, max_length=120)
    payment_sender_account_masked: str | None = Field(default=None, max_length=80)
    tx_hash: str | None = Field(default=None, min_length=8, max_length=160)
    network: str | None = Field(default=None, max_length=20)
    proof_file_id: ResourceId | None = None
    pending_payment_report_id: ResourceId | None = None

    @model_validator(mode="after")
    def validate_by_method(self) -> "PaymentReportRequest":
        if self.network is not None:
            object.__setattr__(self, "network", canonical_network(self.network))
        if self.tx_hash is not None:
            object.__setattr__(
                self,
                "tx_hash",
                canonical_transaction_hash(self.tx_hash),
            )
        if self.payment_type == "usdt_trc20":
            if self.tx_hash and self.network != "TRC20":
                raise ValueError("usdt_trc20 tx_hash requires TRC20 network")
            if not self.tx_hash:
                object.__setattr__(self, "network", None)
        return self
