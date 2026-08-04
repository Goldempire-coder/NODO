from __future__ import annotations

from typing import Any, Callable

from app.core.errors import ApiError
from app.modules.businesses.presenters import decimal_text
from app.modules.notifications.order_notifications import NoopOrderNotificationService
from app.modules.orders.helpers import require_uuid
from app.modules.orders.payment_constants import PAYMENT_INSTRUCTIONS_DISCLAIMER
from app.modules.orders.payment_evidence import PaymentEvidenceMixin
from app.modules.orders.payment_reporting import PaymentReportingMixin
from app.modules.orders.policy import require_order_owner, require_remitter
from app.modules.users.models import UserRecord



class OrderPaymentFlow(PaymentEvidenceMixin, PaymentReportingMixin):
    def __init__(
        self,
        *,
        repository,
        chat_repository,
        audit_writer,
        idempotency_store,
        storage,
        rate_limit: Callable[[str, UserRecord], None],
        notification_service=None,
    ) -> None:  # type: ignore[no-untyped-def]
        self._repository = repository
        self._chat = chat_repository
        self._audit = audit_writer
        self._idempotency = idempotency_store
        self._storage = storage
        self._rate_limit = rate_limit
        self._notifications = notification_service or NoopOrderNotificationService()

    def payment_instructions(self, *, user: UserRecord, order_id: str, request_id: str) -> dict[str, Any]:
        require_remitter(user)
        self._rate_limit("payment_instructions", user)
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND") or order_id
        order = self._repository.get_by_id(order_id)
        if order is None:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        require_order_owner(user, order)
        self._require_payment_details_shared(order)
        order = self._repository.reveal_payment_instructions_atomically(
            order_id=order.id,
            remitter_user_id=user.id,
            request_id=request_id,
            audit_metadata={
                "public_order_code": order.public_order_code,
                "payment_method": order.payment_method_snapshot,
            },
        )
        payment = order.payment_instructions_snapshot or {}
        return {
            "order": {
                "id": order.id,
                "public_order_code": order.public_order_code,
                "status": order.status,
                "amount_usd": decimal_text(order.amount_usd),
                "amount_bs_calculated": decimal_text(order.amount_bs_calculated),
                "rate_snapshot": decimal_text(order.rate_snapshot),
                "payment_report_deadline_at": order.payment_report_deadline_at.isoformat(),
            },
            "payment_instructions": {
                "method_type": payment.get("method_type"),
                "network": payment.get("network"),
                "account_value": payment.get("account_value"),
                "account_masked": payment.get("account_masked"),
                "holder_name": payment.get("holder_name"),
            },
            "disclaimer": PAYMENT_INSTRUCTIONS_DISCLAIMER,
        }

    def _require_payment_details_shared(self, order) -> None:  # type: ignore[no-untyped-def]
        account_value = str(
            (order.payment_instructions_snapshot or {}).get("account_value") or ""
        ).strip()
        if not account_value or not self._chat.has_business_message_containing(
            order_id=order.id,
            text=account_value,
        ):
            raise ApiError("ORDER_PAYMENT_DETAILS_NOT_SHARED", status_code=409)
