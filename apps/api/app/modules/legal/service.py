from __future__ import annotations

from app.core.errors import ApiError
from app.modules.businesses.access_control import require_active_business_access
from app.modules.legal.models import (
    BUSINESS_CREDIT_TERMS_DOCUMENT_SET,
    BUSINESS_LEGAL_CONFIRMATION,
    BUSINESS_TERMS_DOCUMENT_SET,
    BusinessLegalAcceptanceRecord,
    BusinessLegalDocument,
    business_legal_document,
    required_business_legal_documents,
)
from app.modules.legal.schemas import BusinessLegalAcceptanceRequest
from app.modules.users.models import UserRecord


def _present_acceptance(record: BusinessLegalAcceptanceRecord) -> dict:
    return {
        "id": record.id,
        "business_id": record.business_id,
        "user_id": record.user_id,
        "document_set": record.document_set,
        "document_version": record.document_version,
        "accepted_at": record.accepted_at.isoformat(),
    }


class BusinessLegalService:
    def __init__(
        self,
        *,
        business_repository,
        legal_acceptance_repository,
        audit_writer,
    ) -> None:
        self._business_repository = business_repository
        self._legal_acceptance_repository = legal_acceptance_repository
        self._audit_writer = audit_writer

    def requirements(self, *, user: UserRecord) -> dict:
        business, _link = require_active_business_access(
            user=user,
            business_repository=self._business_repository,
        )
        return self._requirements_payload(business_id=business.id, user_id=user.id)

    def accept(
        self,
        *,
        user: UserRecord,
        payload: BusinessLegalAcceptanceRequest,
        request_id: str,
        surface: str,
        locale: str = "es",
    ) -> dict:
        business, _link = require_active_business_access(
            user=user,
            business_repository=self._business_repository,
        )
        document = self._require_document(payload.document_set)
        if payload.document_version != document.document_version:
            raise ApiError("BUSINESS_LEGAL_DOCUMENT_VERSION_INVALID", status_code=409)
        if payload.confirmation != BUSINESS_LEGAL_CONFIRMATION:
            raise ApiError("BUSINESS_LEGAL_CONFIRMATION_REQUIRED", status_code=400)

        acceptance = self._legal_acceptance_repository.record_acceptance(
            business_id=business.id,
            user_id=user.id,
            document_set=document.document_set,
            document_version=document.document_version,
            confirmation=payload.confirmation,
            surface=surface,
            locale=locale,
            request_id=request_id,
        )
        self._audit_writer.write(
            event_type="business_legal_terms_accepted",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="business",
            resource_id=business.id,
            request_id=request_id,
            metadata_json={
                "document_set": document.document_set,
                "document_version": document.document_version,
                "surface": surface,
            },
        )
        return {
            "acceptance": _present_acceptance(acceptance),
            "requirements": self._requirements_payload(business_id=business.id, user_id=user.id)["requirements"],
        }

    def require_business_credit_terms(self, *, user: UserRecord) -> None:
        business, _link = require_active_business_access(
            user=user,
            business_repository=self._business_repository,
        )
        if not self._has_current_acceptance(
            business_id=business.id,
            user_id=user.id,
            document_set=BUSINESS_TERMS_DOCUMENT_SET,
        ):
            raise ApiError("BUSINESS_TERMS_ACCEPTANCE_REQUIRED", status_code=403)
        if not self._has_current_acceptance(
            business_id=business.id,
            user_id=user.id,
            document_set=BUSINESS_CREDIT_TERMS_DOCUMENT_SET,
        ):
            raise ApiError("BUSINESS_CREDIT_TERMS_ACCEPTANCE_REQUIRED", status_code=403)

    def _requirements_payload(self, *, business_id: str, user_id: str) -> dict:
        acceptances = self._legal_acceptance_repository.list_for_business_user(
            business_id=business_id,
            user_id=user_id,
        )
        by_document = {
            (acceptance.document_set, acceptance.document_version): acceptance
            for acceptance in acceptances
        }
        return {
            "business_id": business_id,
            "requirements": [
                self._present_requirement(document, by_document.get((document.document_set, document.document_version)))
                for document in required_business_legal_documents()
            ],
        }

    def _has_current_acceptance(self, *, business_id: str, user_id: str, document_set: str) -> bool:
        document = self._require_document(document_set)
        return self._legal_acceptance_repository.get_for_document(
            business_id=business_id,
            user_id=user_id,
            document_set=document.document_set,
            document_version=document.document_version,
        ) is not None

    @staticmethod
    def _require_document(document_set: str) -> BusinessLegalDocument:
        document = business_legal_document(document_set)
        if document is None:
            raise ApiError("BUSINESS_LEGAL_DOCUMENT_INVALID", status_code=400)
        return document

    @staticmethod
    def _present_requirement(
        document: BusinessLegalDocument,
        acceptance: BusinessLegalAcceptanceRecord | None,
    ) -> dict:
        return {
            "document_set": document.document_set,
            "document_version": document.document_version,
            "title": document.title,
            "accepted": acceptance is not None,
            "accepted_at": acceptance.accepted_at.isoformat() if acceptance else None,
        }
