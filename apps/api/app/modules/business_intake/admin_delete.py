from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.business_intake.policy import require_admin_mutation
from app.modules.business_intake.schemas import AdminBusinessIntakeDeleteRequest
from app.modules.business_intake.telegram_client import telegram_send_message_sync
from app.modules.users.models import UserRecord


BUSINESS_INTAKE_RESET_MESSAGE = (
    "Tu solicitud de NODO Negocio fue reiniciada.\n\n"
    "Puedes comenzar de nuevo desde /start y enviar la informacion corregida."
)


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
        reason = (payload.reason or "").strip() or "admin_reset_onboarding"
        self._rate_limit("admin_delete", user.id)  # type: ignore[attr-defined]

        def compute() -> dict[str, Any]:
            current = self._get_intake(intake_id)  # type: ignore[attr-defined]
            documents_count = len(self._repository.list_documents(current.id))  # type: ignore[attr-defined]
            notification_sent = self._notify_business_intake_reset(
                user=user,
                intake=current,
                request_id=request_id,
            )
            self._write_admin_audit(  # type: ignore[attr-defined]
                event_type="business_intake_deleted",
                user=user,
                intake=current,
                request_id=request_id,
                metadata={"reason": reason, "documents_count": documents_count},
            )
            result = self._repository.delete_intake(intake_id=current.id)  # type: ignore[attr-defined]
            return {"deleted": True, "reset_notification_sent": notification_sent, **result}

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"business_intake:admin:delete:{intake_id}:{user.id}:{idempotency_key}",
            payload={"reason": reason},
            compute=compute,
        )

    def _notify_business_intake_reset(
        self,
        *,
        user: UserRecord,
        intake,  # type: ignore[no-untyped-def]
        request_id: str,
    ) -> bool:
        bot_token = self._settings.business_intake_bot_token  # type: ignore[attr-defined]
        if not bot_token:
            self._write_admin_audit(  # type: ignore[attr-defined]
                event_type="business_intake_reset_notification_skipped",
                user=user,
                intake=intake,
                request_id=request_id,
                metadata={"reason": "missing_business_intake_bot_token"},
            )
            return False
        try:
            telegram_send_message_sync(bot_token, intake.telegram_chat_id, BUSINESS_INTAKE_RESET_MESSAGE)
        except ApiError as exc:
            self._write_admin_audit(  # type: ignore[attr-defined]
                event_type="business_intake_reset_notification_failed",
                user=user,
                intake=intake,
                request_id=request_id,
                metadata={"error_code": exc.code},
            )
            return False
        self._write_admin_audit(  # type: ignore[attr-defined]
            event_type="business_intake_reset_notification_sent",
            user=user,
            intake=intake,
            request_id=request_id,
        )
        return True
