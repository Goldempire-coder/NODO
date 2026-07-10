from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class StripeCheckoutRequest(BaseModel):
    package_code: str = Field(pattern="^(starter|pro|business|enterprise)$")
    success_url: str | None = Field(default=None, max_length=500)
    cancel_url: str | None = Field(default=None, max_length=500)


class ReferralApplyRequest(BaseModel):
    referral_code: str = Field(min_length=4, max_length=32)


class AdminReviewCreditPurchaseRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=500)


class AdminCreditAdjustmentRequest(BaseModel):
    business_id: str = Field(min_length=1)
    amount: int = Field(gt=0)
    direction: str = Field(pattern="^(add|remove)$")
    reason: str = Field(min_length=2, max_length=500)
    notes: str | None = Field(default=None, max_length=500)


class CreditLedgerQuery(BaseModel):
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=50)
    type: str | None = Field(default=None, max_length=32)


class AdminCreditPurchaseQuery(BaseModel):
    status: str | None = Field(default=None, max_length=32)
    business_id: str | None = Field(default=None, min_length=1)
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=50)


def decimal_text(value: Decimal) -> str:
    return format(value, "f")
