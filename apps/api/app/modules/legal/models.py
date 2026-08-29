from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


BUSINESS_TERMS_DOCUMENT_SET = "business_terms"
BUSINESS_CREDIT_TERMS_DOCUMENT_SET = "business_credit_terms"
BUSINESS_LEGAL_DOCUMENT_SETS = {BUSINESS_TERMS_DOCUMENT_SET, BUSINESS_CREDIT_TERMS_DOCUMENT_SET}
BUSINESS_LEGAL_CONFIRMATION = "ACCEPTED_BY_AUTHORIZED_BUSINESS_REPRESENTATIVE"
CURRENT_BUSINESS_TERMS_VERSION = "2026-08-29"
CURRENT_BUSINESS_CREDIT_TERMS_VERSION = "2026-08-29"


@dataclass(frozen=True)
class BusinessLegalDocument:
    document_set: str
    document_version: str
    title: str


@dataclass(frozen=True)
class BusinessLegalAcceptanceRecord:
    id: str
    business_id: str
    user_id: str
    document_set: str
    document_version: str
    confirmation: str
    surface: str
    locale: str
    request_id: str
    accepted_at: datetime = field(default_factory=utc_now)
    created_at: datetime = field(default_factory=utc_now)


BUSINESS_LEGAL_DOCUMENTS = {
    BUSINESS_TERMS_DOCUMENT_SET: BusinessLegalDocument(
        document_set=BUSINESS_TERMS_DOCUMENT_SET,
        document_version=CURRENT_BUSINESS_TERMS_VERSION,
        title="Terminos de NODO Negocio",
    ),
    BUSINESS_CREDIT_TERMS_DOCUMENT_SET: BusinessLegalDocument(
        document_set=BUSINESS_CREDIT_TERMS_DOCUMENT_SET,
        document_version=CURRENT_BUSINESS_CREDIT_TERMS_VERSION,
        title="Terminos de compra de creditos",
    ),
}


def business_legal_document(document_set: str) -> BusinessLegalDocument | None:
    return BUSINESS_LEGAL_DOCUMENTS.get(document_set)


def required_business_legal_documents() -> tuple[BusinessLegalDocument, ...]:
    return tuple(BUSINESS_LEGAL_DOCUMENTS.values())
