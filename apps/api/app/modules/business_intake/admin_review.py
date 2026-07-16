from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.business_intake.models import BusinessIntakeRequestRecord
from app.modules.business_intake.policy import require_admin_mutation
from app.modules.business_intake.schemas import AdminBusinessIntakeReviewRequest
from app.modules.users.models import UserRecord


class BusinessIntakeAdminReviewMixin:
    def accept(
        self,
        *,
        user: UserRecord,
        intake_id: str,
        payload: AdminBusinessIntakeReviewRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        return self._review(
            user=user,
            intake_id=intake_id,
            status="accepted",
            payload=payload,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    def reject(
        self,
        *,
        user: UserRecord,
        intake_id: str,
        payload: AdminBusinessIntakeReviewRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        return self._review(
            user=user,
            intake_id=intake_id,
            status="rejected",
            payload=payload,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    def _review(
        self,
        *,
        user: UserRecord,
        intake_id: str,
        status: str,
        payload: AdminBusinessIntakeReviewRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        public_business_name = self._validate_review_request(
            user=user,
            status=status,
            payload=payload,
            idempotency_key=idempotency_key,
        )
        intake = self._get_intake(intake_id)  # type: ignore[attr-defined]
        self._rate_limit(f"admin_{status}", user.id)  # type: ignore[attr-defined]

        def compute() -> dict[str, Any]:
            return self._compute_review(
                user=user,
                intake_id=intake_id,
                status=status,
                payload=payload,
                public_business_name=public_business_name,
                request_id=request_id,
            )

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"business_intake:admin:{status}:{intake.id}:{user.id}:{idempotency_key}",
            payload={"status": status, **payload.model_dump()},
            compute=compute,
        )

    def _validate_review_request(
        self,
        *,
        user: UserRecord,
        status: str,
        payload: AdminBusinessIntakeReviewRequest,
        idempotency_key: str | None,
    ) -> str:
        require_admin_mutation(user)
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        if not payload.reason.strip():
            raise ApiError("ADMIN_REASON_REQUIRED", status_code=400)
        if status != "accepted" and payload.create_business:
            raise ApiError("BUSINESS_INTAKE_STATUS_INVALID", status_code=409)
        if status != "accepted" and payload.approve_business:
            raise ApiError("BUSINESS_INTAKE_STATUS_INVALID", status_code=409)
        public_business_name = (payload.public_business_name or "").strip()
        if payload.create_business and not public_business_name:
            raise ApiError("VALIDATION_ERROR", status_code=422)
        return public_business_name

    def _compute_review(
        self,
        *,
        user: UserRecord,
        intake_id: str,
        status: str,
        payload: AdminBusinessIntakeReviewRequest,
        public_business_name: str,
        request_id: str,
    ) -> dict[str, Any]:
        current = self._reviewable_intake(intake_id=intake_id, status=status)
        reviewed = self._apply_review_if_needed(
            current=current,
            status=status,
            user=user,
            payload=payload,
            request_id=request_id,
        )
        if payload.approve_business and not (payload.create_business or reviewed.created_business_id):
            raise ApiError("VALIDATION_ERROR", status_code=422)
        created_business = False
        access_link_created = False
        approval_notification_sent = False
        business_payload: dict[str, Any] | None = None
        if status == "accepted" and (payload.create_business or payload.approve_business):
            (
                reviewed,
                created_business,
                business_payload,
                access_link_created,
                approval_notification_sent,
            ) = self._maybe_create_business_from_intake(  # type: ignore[attr-defined]
                user=user,
                reviewed=reviewed,
                payload=payload,
                public_business_name=public_business_name,
                request_id=request_id,
            )
        return {
            "intake": self._public_intake(reviewed),  # type: ignore[attr-defined]
            "created_business": created_business,
            "business": business_payload,
            "access_link_created": access_link_created,
            "approval_notification_sent": approval_notification_sent,
        }

    def _reviewable_intake(self, *, intake_id: str, status: str) -> BusinessIntakeRequestRecord:
        current = self._get_intake(intake_id)  # type: ignore[attr-defined]
        if current.status not in {"submitted", status}:
            raise ApiError("BUSINESS_INTAKE_STATUS_INVALID", status_code=409)
        return current

    def _apply_review_if_needed(
        self,
        *,
        current: BusinessIntakeRequestRecord,
        status: str,
        user: UserRecord,
        payload: AdminBusinessIntakeReviewRequest,
        request_id: str,
    ) -> BusinessIntakeRequestRecord:
        if current.status == status:
            return current
        reviewed = self._repository.review(  # type: ignore[attr-defined]
            intake=current,
            status=status,
            admin_user_id=user.id,
            reason=payload.reason.strip(),
        )
        self._write_admin_audit(  # type: ignore[attr-defined]
            event_type=f"business_intake_{status}",
            user=user,
            intake=reviewed,
            request_id=request_id,
        )
        return reviewed
