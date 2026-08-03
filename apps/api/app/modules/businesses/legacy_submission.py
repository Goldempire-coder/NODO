from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.businesses.models import REQUIRED_DOCUMENT_TYPES
from app.modules.businesses.payment_method_validation import normalize_payment_account, normalize_payment_holder, normalize_payment_network
from app.modules.businesses.policy import require_business_owner
from app.modules.businesses.presenters import business_payload, mask_account
from app.modules.businesses.schemas import BusinessVerificationSubmitRequest
from app.modules.businesses.state_machine import require_owner_submit_allowed
from app.modules.users.models import UserRecord


class LegacyBusinessSubmissionMixin:
    def submit_verification(
        self,
        *,
        user: UserRecord,
        business_id: str,
        payload: BusinessVerificationSubmitRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        self._rate_limit("submit", user)  # type: ignore[attr-defined]
        business = self._business_or_404(business_id)  # type: ignore[attr-defined]
        require_business_owner(user, business)
        require_owner_submit_allowed(business)
        data = payload.submitted_data

        def compute() -> dict[str, Any]:
            self._ensure_required_documents_uploaded(business_id=business.id, document_file_ids=data.document_file_ids)
            self._repository.update_business(  # type: ignore[attr-defined]
                business,
                {
                    "business_name": data.business_name,
                    "rif": data.rif,
                    "address": data.address,
                    "phone": data.phone,
                    "country": data.country,
                },
            )
            for method in data.payment_methods:
                self._add_submission_payment_method(business_id=business.id, method=method, user=user, request_id=request_id)
            submission = self._repository.create_submission(  # type: ignore[attr-defined]
                business_id=business.id,
                submitted_by_user_id=user.id,
                submitted_data_json=data.model_dump(),
            )
            self._audit.write(  # type: ignore[attr-defined]
                event_type="business_submitted",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="business",
                resource_id=business.id,
                request_id=request_id,
            )
            return {
                "business": business_payload(business),
                "submission": {
                    "id": submission.id,
                    "business_id": submission.business_id,
                    "status": submission.status,
                    "submitted_at": submission.submitted_at.isoformat(),
                },
            }

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            idempotency_key,
            payload={"id": business_id, **payload.model_dump()},
            compute=compute,
        )

    def _ensure_required_documents_uploaded(self, *, business_id: str, document_file_ids: list[str]) -> None:
        files = self._repository.list_files_for_business(business_id)  # type: ignore[attr-defined]
        uploaded_types = {file.file_type for file in files if file.id in document_file_ids}
        if REQUIRED_DOCUMENT_TYPES - uploaded_types:
            raise ApiError("BUSINESS_DOCUMENT_REQUIRED", status_code=400)

    def _add_submission_payment_method(self, *, business_id: str, method, user: UserRecord, request_id: str) -> None:  # type: ignore[no-untyped-def]
        if method.method_type not in {"zelle", "usdt_trc20"} or (method.method_type == "zelle" and method.network is not None):
            raise ApiError("BUSINESS_VERIFICATION_REQUIRED", status_code=400)
        try:
            account_value = normalize_payment_account(method_type=method.method_type, account_value=method.account_value)
            network = normalize_payment_network(method_type=method.method_type, network=method.network)
            holder_name = normalize_payment_holder(method.holder_name)
        except ApiError:
            raise ApiError("BUSINESS_VERIFICATION_REQUIRED", status_code=400)
        payment = self._repository.add_payment_method(  # type: ignore[attr-defined]
            business_id=business_id,
            method_type=method.method_type,
            network=network,
            account_value=account_value,
            account_masked=mask_account(account_value),
            holder_name=holder_name,
        )
        self._audit.write(  # type: ignore[attr-defined]
            event_type="payment_method_added",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="business",
            resource_id=business_id,
            request_id=request_id,
            metadata_json={"payment_method_id": payment.id, "method_type": payment.method_type},
        )
