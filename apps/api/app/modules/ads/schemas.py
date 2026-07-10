from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class AdCreateRequest(BaseModel):
    business_id: str | None = Field(default=None, min_length=1)
    payment_method_id: str = Field(min_length=1)
    payment_method: str = Field(min_length=1, max_length=32)
    delivery_method: str = Field(default="pago_movil_ve", max_length=32)
    rate_bs_per_usd: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    amount_min_usd: Decimal = Field(ge=20, max_digits=12, decimal_places=2)
    amount_max_usd: Decimal = Field(ge=20, max_digits=12, decimal_places=2)


class AdUpdateRequest(BaseModel):
    rate_bs_per_usd: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    amount_min_usd: Decimal | None = Field(default=None, ge=20, max_digits=12, decimal_places=2)
    amount_max_usd: Decimal | None = Field(default=None, ge=20, max_digits=12, decimal_places=2)


class AdActionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class AdSearchQuery(BaseModel):
    amount_usd: Decimal = Field(ge=20, max_digits=12, decimal_places=2)
    payment_method: str = Field(min_length=1, max_length=32)
    delivery_method: str = Field(default="pago_movil_ve", max_length=32)
    sort: str | None = Field(default=None, max_length=16)
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=50)
