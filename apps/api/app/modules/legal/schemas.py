from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.modules.legal.models import (
    BUSINESS_CREDIT_TERMS_DOCUMENT_SET,
    BUSINESS_LEGAL_CONFIRMATION,
    BUSINESS_TERMS_DOCUMENT_SET,
)
from app.shared.validation import StrictRequestModel

BusinessLegalDocumentSet = Literal["business_terms", "business_credit_terms"]


class BusinessLegalAcceptanceRequest(StrictRequestModel):
    document_set: BusinessLegalDocumentSet
    document_version: str = Field(min_length=1, max_length=32)
    confirmation: Literal["ACCEPTED_BY_AUTHORIZED_BUSINESS_REPRESENTATIVE"] = BUSINESS_LEGAL_CONFIRMATION


VALID_BUSINESS_LEGAL_DOCUMENT_SETS = {
    BUSINESS_TERMS_DOCUMENT_SET,
    BUSINESS_CREDIT_TERMS_DOCUMENT_SET,
}
