from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.business_intake.policy import require_admin_mutation
from app.modules.business_intake.schemas import AdminBusinessIntakeDeleteRequest
from app.modules.users.models import UserRecord


class BusinessIntakeAdminDeleteMixin:
    def delete(
        self,
        *,
        user: UserRecord,
        intake_id: str,
        payload: AdminBusinessIntakeDeleteRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        require_admin_mutation(user)
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        reason = payload.reason.strip()
        if not reason:
            raise ApiError("ADMIN_REASON_REQUIRED", status_code=400)
        self._rate_limit("admin_delete", user.id)  # type: ignore[attr-defined]

        def compute() -> dict[str, Any]:
            current = self._get_intake(intake_id)  # type: ignore[attr-defined]
            documents_count = len(self._repository.list_documents(current.id))  # type: ignore[attr-defined]
            self._write_admin_audit(  # type: ignore[attr-defined]
                event_type="business_intake_deleted",
                user=user,
                intake=current,
                request_id=request_id,
                metadata={"reason": reason, "documents_count": documents_count},
            )
            result = self._repository.delete_intake(intake_id=current.id)  # type: ignore[attr-defined]
            return {"deleted": True, **result}

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"business_intake:admin:delete:{intake_id}:{user.id}:{idempotency_key}",
            payload={"reason": reason},
            compute=compute,
        )
