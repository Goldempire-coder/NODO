from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class ReceiverData(BaseModel):
    bank: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=7, max_length=32)
    document: str = Field(min_length=4, max_length=32)
    holder: str = Field(min_length=2, max_length=120)


class OrderCreateRequest(BaseModel):
    ad_id: str = Field(min_length=1)
    amount_usd: Decimal = Field(ge=20, max_digits=12, decimal_places=2)
    receiver_data: ReceiverData


class OrderActionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class PaymentReportRequest(BaseModel):
    payment_type: str = Field(pattern="^(zelle|usdt_trc20)$")
    payment_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_reference: str | None = Field(default=None, max_length=120)
    payment_sender_name: str | None = Field(default=None, max_length=120)
    payment_sender_account_masked: str | None = Field(default=None, max_length=80)
    tx_hash: str | None = Field(default=None, min_length=8, max_length=160)
    network: str | None = Field(default=None, max_length=20)
    proof_file_id: str | None = Field(default=None, min_length=1)
    pending_payment_report_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_by_method(self) -> "PaymentReportRequest":
        if self.payment_type == "zelle":
            if not self.payment_reference or not self.payment_sender_name:
                raise ValueError("zelle report requires reference and sender name")
        if self.payment_type == "usdt_trc20":
            if not self.tx_hash or self.network != "TRC20":
                raise ValueError("usdt_trc20 report requires tx_hash and TRC20 network")
        return self
