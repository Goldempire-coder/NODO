from __future__ import annotations

from typing import Any, Callable

from app.core.errors import ApiError
from app.modules.businesses.models import BusinessRecord
from app.modules.businesses.presenters import file_payload
from app.modules.orders.business_order_actions_ops import OrderBusinessActionsMixin
from app.modules.orders.business_payment_confirmation_ops import OrderBusinessPaymentConfirmationMixin
from app.modules.orders.helpers import require_uuid
from app.modules.orders.order_copy import ORDER_DISCLAIMER
from app.modules.orders.serializers import business_order_payload, business_payment_report_payload, business_receiver_payload
from app.modules.users.models import UserRecord


class OrderBusinessOps(OrderBusinessPaymentConfirmationMixin, OrderBusinessActionsMixin):
    def __init__(
        self,
        *,
        repository,
        ad_repository,
        audit_writer,
        idempotency_store,
        rate_limit: Callable[[str, UserRecord], None],
        approved_business_for_owner: Callable[[UserRecord], BusinessRecord],
    ) -> None:  # type: ignore[no-untyped-def]
        self._repository = repository
        self._ads = ad_repository
        self._audit = audit_writer
        self._idempotency = idempotency_store
        self._rate_limit = rate_limit
        self._approved_business_for_owner = approved_business_for_owner

    def business_orders(self, *, user: UserRecord, status: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        business = self._approved_business_for_owner(user)
        self._rate_limit("business_orders", user)
        allowed_statuses = {None, "payment_reported", "payment_rejected", "payment_confirmed", "delivered", "disputed"}
        if status not in allowed_statuses:
            raise ApiError("VALIDATION_ERROR", status_code=422)
        items, next_cursor = self._repository.list_for_business(business_id=business.id, status=status, cursor=cursor, limit=limit)
        return {
            "items": [business_order_payload(order, list_view=True) for order in items],
            "next_cursor": next_cursor,
            "disclaimer": ORDER_DISCLAIMER,
        }

    def business_order_detail(self, *, user: UserRecord, order_id: str, request_id: str) -> dict[str, Any]:
        business = self._approved_business_for_owner(user)
        self._rate_limit("business_order_detail", user)
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND") or order_id
        order = self._repository.get_by_id_for_business(order_id=order_id, business_id=business.id)
        if order is None:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        report = self._repository.get_submitted_payment_report_for_order(order.id)
        if report is None and order.status in {"payment_confirmed", "delivered", "payment_rejected"}:
            report = self._repository.get_latest_payment_report_for_order(order.id)
        files = self._repository.list_payment_evidence_for_report(report.id) if report is not None else []
        events = self._repository.list_state_events_for_order(order.id)
        return {
            "order": business_order_payload(order),
            "receiver_data": business_receiver_payload(order),
            "payment_report": business_payment_report_payload(report) if report else None,
            "evidence": [file_payload(file) for file in files],
            "timeline": [
                {
                    "event_type": event.event_type,
                    "from_status": event.from_status,
                    "to_status": event.to_status,
                    "created_at": event.created_at.isoformat(),
                    "reason": event.reason,
                }
                for event in events
            ],
            "disclaimer": ORDER_DISCLAIMER,
        }
