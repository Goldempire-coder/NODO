from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.errors import ApiError
from app.modules.business_intake.models import BusinessIntakeRequestRecord
from app.modules.business_intake.schemas import AdminBusinessIntakeReviewRequest
from app.modules.business_intake.telegram_client import telegram_send_message_sync, telegram_set_chat_menu_button_sync
from app.modules.users.models import UserRecord


BUSINESS_APPROVAL_MESSAGE = (
    "🎉 ¡Felicitaciones! Tu negocio fue aprobado en NODO.\n\n"
    "Ya puedes abrir NODO Negocio para gestionar tus anuncios, órdenes y créditos."
)
BUSINESS_APPROVAL_BUTTON_TEXT = "🚀 Abrir NODO Negocio"
BUSINESS_MENU_BUTTON_TEXT = "Abrir NODO Negocio"


class BusinessIntakeBusinessCreationMixin:
    def _business_payload(self, business: Any) -> dict[str, Any]:
        return {
            "id": business.id,
            "business_name": business.business_name,
            "verification_status": business.verification_status,
            "rif": business.rif,
            "min_order_amount_usd": str(business.min_order_amount_usd),
            "max_order_amount_usd": str(business.max_order_amount_usd),
            "daily_limit_usd": str(business.daily_limit_usd),
        }

    def _intake_decimal_or_default(self, value: str | None, fallback: str) -> Decimal:
        return Decimal(value or fallback)

    def _maybe_create_business_from_intake(
        self,
        *,
        user: UserRecord,
        reviewed: BusinessIntakeRequestRecord,
        payload: AdminBusinessIntakeReviewRequest,
        public_business_name: str,
        request_id: str,
    ) -> tuple[BusinessIntakeRequestRecord, bool, dict[str, Any] | None, bool, bool]:
        if not payload.create_business:
            if not reviewed.created_business_id:
                return reviewed, False, None, False, False
            business = self._businesses.get_business(reviewed.created_business_id)  # type: ignore[attr-defined]
            if business is None:
                return reviewed, False, None, False, False
            access_link_created, notification_sent = self._approve_business_intake_access_if_requested(
                user=user,
                reviewed=reviewed,
                business=business,
                payload=payload,
                request_id=request_id,
            )
            if payload.approve_business:
                business = self._businesses.get_business(business.id) or business  # type: ignore[attr-defined]
            return reviewed, False, self._business_payload(business), access_link_created, notification_sent

        if reviewed.created_business_id:
            business = self._businesses.get_business(reviewed.created_business_id)  # type: ignore[attr-defined]
            if business is None:
                return reviewed, False, None, False, False
            access_link_created, notification_sent = self._approve_business_intake_access_if_requested(
                user=user,
                reviewed=reviewed,
                business=business,
                payload=payload,
                request_id=request_id,
            )
            if payload.approve_business:
                business = self._businesses.get_business(business.id) or business  # type: ignore[attr-defined]
            return reviewed, False, self._business_payload(business), access_link_created, notification_sent

        applicant = self._ensure_applicant_user(reviewed.telegram_user_id)  # type: ignore[attr-defined]
        if self._businesses.get_active_business_for_owner(applicant.id) is not None:  # type: ignore[attr-defined]
            raise ApiError("BUSINESS_ALREADY_EXISTS", status_code=409)
        business = self._businesses.create_business(  # type: ignore[attr-defined]
            owner_user_id=applicant.id,
            business_name=public_business_name,
            rif=reviewed.business_tax_id,
            address=None,
            phone=reviewed.business_phone or reviewed.contact_phone,
            country="VE",
        )
        business = self._businesses.update_business_capacity(  # type: ignore[attr-defined]
            business=business,
            trust_level=business.trust_level or "new",
            min_order_amount_usd=self._intake_decimal_or_default(reviewed.min_amount_usd, "20.00"),
            max_order_amount_usd=self._intake_decimal_or_default(reviewed.max_amount_usd, "100.00"),
            daily_limit_usd=self._intake_decimal_or_default(reviewed.daily_limit_usd, "1000.00"),
            active_order_limit=business.active_order_limit,
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
        access_link_created, notification_sent = self._approve_business_intake_access_if_requested(
            user=user,
            reviewed=updated,
            business=business,
            payload=payload,
            request_id=request_id,
        )
        if payload.approve_business:
            business = self._businesses.get_business(business.id) or business  # type: ignore[attr-defined]
        return updated, True, self._business_payload(business), access_link_created, notification_sent

    def _approve_business_intake_access_if_requested(
        self,
        *,
        user: UserRecord,
        reviewed: BusinessIntakeRequestRecord,
        business: Any,
        payload: AdminBusinessIntakeReviewRequest,
        request_id: str,
    ) -> tuple[bool, bool]:
        if not payload.approve_business:
            return False, False

        applicant = self._ensure_applicant_user(reviewed.telegram_user_id)  # type: ignore[attr-defined]
        if applicant.status != "active":
            raise ApiError("USER_NOT_ACTIVE", status_code=403)
        if applicant.role != "business_owner":
            self._users.set_user_role(applicant.id, "business_owner")  # type: ignore[attr-defined]
            applicant.role = "business_owner"

        if business.verification_status != "approved":
            business = self._businesses.approve_business_from_intake(business=business)  # type: ignore[attr-defined]
            self._audit.write(  # type: ignore[attr-defined]
                event_type="business_approved",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="business",
                resource_id=business.id,
                request_id=request_id,
                metadata_json={"source": "business_intake", "intake_id": reviewed.id},
            )

        existing_link = self._businesses.get_active_access_link_for_business_user(  # type: ignore[attr-defined]
            business_id=business.id,
            user_id=applicant.id,
        )
        link = self._businesses.create_access_link(  # type: ignore[attr-defined]
            business_id=business.id,
            user_id=applicant.id,
            telegram_id_snapshot=reviewed.telegram_user_id,
            role_in_business="owner",
            linked_by_admin_id=user.id,
            reason=payload.reason.strip(),
        )
        access_link_created = existing_link is None
        if access_link_created:
            self._audit.write(  # type: ignore[attr-defined]
                event_type="business_access_linked",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="business_access_link",
                resource_id=link.id,
                request_id=request_id,
                metadata_json={
                    "business_id": business.id,
                    "target_user_id": applicant.id,
                    "source": "business_intake",
                    "intake_id": reviewed.id,
                },
            )

        notification_sent = self._notify_business_approval(
            user=user,
            reviewed=reviewed,
            business=business,
            link_id=link.id,
            request_id=request_id,
        )
        return access_link_created, notification_sent

    def _notify_business_approval(
        self,
        *,
        user: UserRecord,
        reviewed: BusinessIntakeRequestRecord,
        business: Any,
        link_id: str,
        request_id: str,
    ) -> bool:
        bot_token = self._settings.business_intake_bot_token  # type: ignore[attr-defined]
        if not bot_token:
            self._write_admin_audit(  # type: ignore[attr-defined]
                event_type="business_intake_approval_notification_skipped",
                user=user,
                intake=reviewed,
                request_id=request_id,
                metadata={"business_id": business.id, "reason": "missing_business_intake_bot_token"},
            )
            return False

        try:
            telegram_send_message_sync(
                bot_token,
                reviewed.telegram_chat_id,
                BUSINESS_APPROVAL_MESSAGE,
                reply_markup=self._business_approval_reply_markup(),
            )
            self._set_business_open_menu_button(
                bot_token=bot_token,
                chat_id=reviewed.telegram_chat_id,
                user=user,
                reviewed=reviewed,
                business=business,
                link_id=link_id,
                request_id=request_id,
            )
        except ApiError as exc:
            self._write_admin_audit(  # type: ignore[attr-defined]
                event_type="business_intake_approval_notification_failed",
                user=user,
                intake=reviewed,
                request_id=request_id,
                metadata={"business_id": business.id, "link_id": link_id, "error_code": exc.code},
            )
            return False

        self._write_admin_audit(  # type: ignore[attr-defined]
            event_type="business_intake_approval_notification_sent",
            user=user,
            intake=reviewed,
            request_id=request_id,
            metadata={"business_id": business.id, "link_id": link_id},
        )
        return True

    def _set_business_open_menu_button(
        self,
        *,
        bot_token: str,
        chat_id: int,
        user: UserRecord,
        reviewed: BusinessIntakeRequestRecord,
        business: Any,
        link_id: str,
        request_id: str,
    ) -> None:
        try:
            telegram_set_chat_menu_button_sync(
                bot_token,
                chat_id,
                BUSINESS_MENU_BUTTON_TEXT,
                self._business_web_app_url(),
            )
        except ApiError as exc:
            self._write_admin_audit(  # type: ignore[attr-defined]
                event_type="business_intake_approval_menu_button_failed",
                user=user,
                intake=reviewed,
                request_id=request_id,
                metadata={"business_id": business.id, "link_id": link_id, "error_code": exc.code},
            )

    def _business_approval_reply_markup(self) -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {
                        "text": BUSINESS_APPROVAL_BUTTON_TEXT,
                        "web_app": {"url": self._business_web_app_url()},
                    }
                ]
            ]
        }

    def _business_web_app_url(self) -> str:
        base_url = self._settings.telegram_web_app_url.rstrip("/")  # type: ignore[attr-defined]
        return f"{base_url}/business/"
