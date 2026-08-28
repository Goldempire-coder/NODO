from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from app.shared.validation import ResourceId, StrictRequestModel


class StripeCheckoutRequest(StrictRequestModel):
    package_code: str = Field(pattern="^(starter|pro|business|enterprise)$")
    success_url: str | None = Field(default=None, max_length=500)
    cancel_url: str | None = Field(default=None, max_length=500)


class LegacyBaseUsdcPaymentRequest(StrictRequestModel):
    package_code: str = Field(pattern="^(starter|pro|business|enterprise)$")
    token_symbol: str = Field(default="USDC", pattern="^USDC$")


class ContractBaseUsdcPaymentRequest(StrictRequestModel):
    package_code: str = Field(pattern="^(starter|pro|business|enterprise)$")
    payer_wallet_address: str = Field(pattern="^0x[a-fA-F0-9]{40}$")


BaseUsdcPaymentRequest = ContractBaseUsdcPaymentRequest | LegacyBaseUsdcPaymentRequest


class CreditHandoffCreateRequest(StrictRequestModel):
    package_code: str = Field(pattern="^(starter|pro|business|enterprise)$")


class CreditHandoffTokenRequest(StrictRequestModel):
    handoff_token: str = Field(min_length=43, max_length=43, pattern="^[A-Za-z0-9_-]+$")


class CreditHandoffClaimRequest(CreditHandoffTokenRequest):
    wallet_address: str = Field(pattern="^0x[a-fA-F0-9]{40}$")
    chain_id: int
    signature: str = Field(pattern="^0x[a-fA-F0-9]{130}$")


class BaseUsdcTxHashRequest(StrictRequestModel):
    tx_hash: str = Field(pattern="^0x[a-fA-F0-9]{64}$")


class ContractCreditPurchaseDismissRequest(StrictRequestModel):
    confirmation: str = Field(pattern="^NO_PAYMENT_SENT$")


class ReferralApplyRequest(StrictRequestModel):
    referral_code: str = Field(min_length=4, max_length=32)


class AdminReviewCreditPurchaseRequest(StrictRequestModel):
    reason: str = Field(min_length=2, max_length=500)


class AdminCreditAdjustmentRequest(StrictRequestModel):
    business_id: ResourceId
    amount: int = Field(gt=0)
    direction: str = Field(pattern="^(add|remove)$")
    reason: str = Field(min_length=2, max_length=500)
    notes: str | None = Field(default=None, max_length=500)


class CreditLedgerQuery(StrictRequestModel):
    cursor: str | None = Field(default=None, max_length=500)
    limit: int = Field(default=20, ge=1, le=50)
    type: str | None = Field(default=None, max_length=32)


class AdminCreditPurchaseQuery(StrictRequestModel):
    status: str | None = Field(default=None, max_length=32)
    business_id: ResourceId | None = None
    cursor: str | None = Field(default=None, max_length=500)
    limit: int = Field(default=20, ge=1, le=50)


def decimal_text(value: Decimal) -> str:
    return format(value, "f")
