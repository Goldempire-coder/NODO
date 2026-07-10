from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.business_intake.models import BusinessIntakeRequestRecord
from app.modules.business_intake.schemas import AdminBusinessIntakeReviewRequest
from app.modules.users.models import UserRecord


class BusinessIntakeBusinessCreationMixin:
    def _business_payload(self, business: Any) -> dict[str, Any]:
        return {
            "id": business.id,
            "business_name": business.business_name,
            "verification_status": business.verification_status,
        }

    def _maybe_create_business_from_intake(
        self,
        *,
        user: UserRecord,
        reviewed: BusinessIntakeRequestRecord,
        payload: AdminBusinessIntakeReviewRequest,
        public_business_name: str,
        request_id: str,
    ) -> tuple[BusinessIntakeRequestRecord, bool, dict[str, Any] | None]:
        if not payload.create_business:
            return reviewed, False, None

        if reviewed.created_business_id:
            business = self._businesses.get_business(reviewed.created_business_id)  # type: ignore[attr-defined]
            return reviewed, False, self._business_payload(business) if business is not None else None

        applicant = self._ensure_applicant_user(reviewed.telegram_user_id)  # type: ignore[attr-defined]
        if self._businesses.get_active_business_for_owner(applicant.id) is not None:  # type: ignore[attr-defined]
            raise ApiError("BUSINESS_ALREADY_EXISTS", status_code=409)
        business = self._businesses.create_business(  # type: ignore[attr-defined]
            owner_user_id=applicant.id,
            business_name=public_business_name,
            rif=None,
            address=None,
            phone=reviewed.business_phone or reviewed.contact_phone,
            country="VE",
        )
        updated = self._repository.attach_created_business(  # type: ignore[attr-defined]
            intake=reviewed,
            business_id=business.id,
            linked_telegram_user_id=reviewed.telegram_user_id,
        )
        self._write_admin_audit(  # type: ignore[attr-defined]
            event_type="business_created_from_intake",
            user=user,
            intake=updated,
            request_id=request_id,
            metadata={"business_id": business.id, "public_business_name": public_business_name},
        )
        return updated, True, self._business_payload(business)
