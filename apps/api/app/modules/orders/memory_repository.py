from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from threading import RLock
from typing import Any

from app.core.errors import ApiError
from app.modules.businesses.models import FileAssetRecord
from app.modules.orders.integrity import AtomicCancellationResult
from app.modules.orders.memory_receiver_completion import InMemoryOrderReceiverCompletionMixin
from app.modules.orders.memory_payment_reports import InMemoryOrderPaymentReportsMixin
from app.modules.orders.memory_queries import InMemoryOrderQueriesMixin
from app.modules.orders.memory_state_events import InMemoryOrderStateEventsMixin
from app.modules.orders.models import OrderRecord, OrderStateEventRecord, PaymentReportRecord, new_id, new_public_order_code, utc_now


class InMemoryOrderRepository(InMemoryOrderReceiverCompletionMixin, InMemoryOrderPaymentReportsMixin, InMemoryOrderQueriesMixin, InMemoryOrderStateEventsMixin):
    moves_ad_on_create_order = False
    moves_ad_on_atomic_cancel = False
    creates_initial_state_event_on_create_order = False

    def __init__(self, *, capacity_repository=None, audit_writer=None, dispute_repository=None) -> None:  # type: ignore[no-untyped-def]
        self._lock = RLock()
        self._capacity = capacity_repository
        self._audit = audit_writer
        self._disputes = dispute_repository
        self.orders: dict[str, OrderRecord] = {}
        self.events: list[OrderStateEventRecord] = []
        self.payment_reports: dict[str, PaymentReportRecord] = {}
        self.files: dict[str, FileAssetRecord] = {}
        self.receiver_details = {}

    def get_by_id(self, order_id: str) -> OrderRecord | None:
        return self.orders.get(order_id)

    def get_by_idempotency_key(self, *, remitter_user_id: str, idempotency_key: str) -> OrderRecord | None:
        for order in self.orders.values():
            if order.remitter_user_id == remitter_user_id and order.idempotency_key == idempotency_key:
                return order
        return None

    def count_active_for_business(self, business_id: str) -> int:
        return sum(
            1
            for order in self.orders.values()
            if order.business_id == business_id
            and order.status
            in {
                "waiting_payment",
                "payment_reported",
                "payment_rejected",
                "payment_confirmed",
                "delivered",
                "disputed",
            }
        )

    def create_order(self, **fields: Any) -> OrderRecord:
        with self._lock:
            capacity_reservation = fields.pop("capacity_reservation", None)
            if capacity_reservation is not None:
                business = capacity_reservation["business"]
                if self.count_active_for_business(business.id) >= business.active_order_limit:
                    raise ApiError("AD_NOT_AVAILABLE", status_code=409)
            now = utc_now()
            order = OrderRecord(
                id=new_id(),
                public_order_code=new_public_order_code(),
                created_at=now,
                updated_at=now,
                **fields,
            )
            if capacity_reservation is not None and self._capacity is not None:
                self._capacity.reserve(
                    order_id=order.id,
                    business=capacity_reservation["business"],
                    amount_usd=capacity_reservation["amount_usd"],
                    reason=capacity_reservation["reason"],
                )
            self.orders[order.id] = order
            return order

    def reveal_payment_instructions_atomically(
        self,
        *,
        order_id: str,
        remitter_user_id: str,
        request_id: str,
        audit_metadata: dict[str, Any],
    ) -> OrderRecord:
        with self._lock:
            order = self.orders.get(order_id)
            if order is None or order.remitter_user_id != remitter_user_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            revealed_at = utc_now()
            if order.status != "waiting_payment":
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            if order.payment_report_deadline_at <= revealed_at:
                raise ApiError("ORDER_EXPIRED", status_code=409)
            if order.payment_data_revealed_at is None:
                order.payment_data_revealed_at = revealed_at
            if order.payment_data_revealed_by is None:
                order.payment_data_revealed_by = remitter_user_id
            order.updated_at = revealed_at
            if self._audit is not None:
                self._audit.write(
                    event_type="payment_instructions_viewed",
                    actor_user_id=remitter_user_id,
                    actor_role="remitter",
                    resource_type="order",
                    resource_id=order.id,
                    request_id=request_id,
                    metadata_json=audit_metadata,
                )
            return order

    def report_payment_atomically(
        self,
        *,
        order_id: str,
        remitter_user_id: str,
        create_report_fields: dict[str, Any],
        paid_reported_at: datetime,
        business_response_warning_at: datetime,
        business_response_deadline_at: datetime,
        request_id: str,
        event_metadata: dict[str, Any],
        audit_metadata: dict[str, Any],
    ) -> tuple[OrderRecord, PaymentReportRecord]:
        with self._lock:
            order = self.orders.get(order_id)
            if order is None or order.remitter_user_id != remitter_user_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if order.status != "waiting_payment":
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            if order.paid_reported_at is not None:
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            if order.payment_report_deadline_at <= paid_reported_at:
                raise ApiError("ORDER_EXPIRED", status_code=409)
            if order.payment_method_snapshot != create_report_fields["payment_type"]:
                raise ApiError("INVALID_PAYMENT_METHOD", status_code=400)
            if order.amount_usd != Decimal(str(create_report_fields["payment_amount"])):
                raise ApiError("PAYMENT_REPORT_AMOUNT_MISMATCH", status_code=409)
            if self.get_submitted_payment_report_for_order(order_id) is not None:
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            report_id = create_report_fields["report_id"]
            proof_file_id = create_report_fields.get("proof_file_id")
            if report_id in self.payment_reports or (
                proof_file_id is not None
                and any(
                    report.proof_file_id == proof_file_id
                    for report in self.payment_reports.values()
                )
            ):
                raise ApiError(
                    "PAYMENT_REPORT_PROOF_ALREADY_USED",
                    status_code=409,
                )
            tx_hash = create_report_fields.get("tx_hash")
            network = create_report_fields.get("network")
            if tx_hash is not None and any(
                report.tx_hash == tx_hash and report.network == network
                for report in self.payment_reports.values()
            ):
                raise ApiError("PAYMENT_REPORT_PROOF_ALREADY_USED", status_code=409)
            report = self.create_payment_report(**create_report_fields)
            order.status = "payment_reported"
            order.paid_reported_at = paid_reported_at
            order.business_response_warning_at = business_response_warning_at
            order.business_response_deadline_at = business_response_deadline_at
            order.updated_at = utc_now()
            self.add_state_event(
                order_id=order.id,
                from_status="waiting_payment",
                to_status="payment_reported",
                event_type="payment_reported",
                actor_user_id=remitter_user_id,
                actor_role="remitter",
                reason=None,
                request_id=request_id,
                metadata_json=event_metadata,
            )
            if self._audit is not None:
                self._audit.write(
                    event_type="payment_reported",
                    actor_user_id=remitter_user_id,
                    actor_role="remitter",
                    resource_type="order",
                    resource_id=order.id,
                    request_id=request_id,
                    metadata_json=audit_metadata,
                )
            return order, report

    def cancel_waiting_payment_atomically(
        self,
        *,
        order_id: str,
        expected_remitter_user_id: str | None,
        expected_business_id: str | None,
        transition_at: datetime,
        require_expired: bool,
        enforce_payment_not_sent_confirmation: bool,
        payment_not_sent_confirmed: bool,
        cancel_reason: str,
        event_type: str,
        actor_user_id: str | None,
        actor_role: str | None,
        event_reason: str | None,
        request_id: str,
        event_metadata: dict[str, Any],
        audit_event_type: str,
        audit_metadata: dict[str, Any],
    ) -> AtomicCancellationResult:
        with self._lock:
            order = self.orders.get(order_id)
            if order is None:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if expected_remitter_user_id and order.remitter_user_id != expected_remitter_user_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if expected_business_id and order.business_id != expected_business_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if order.status != "waiting_payment":
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            expired = order.payment_report_deadline_at <= transition_at
            if require_expired and not expired:
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            if not require_expired and expired:
                raise ApiError("ORDER_EXPIRED", status_code=409)
            if (
                enforce_payment_not_sent_confirmation
                and order.payment_data_revealed_at is not None
                and not payment_not_sent_confirmed
            ):
                raise ApiError(
                    "ORDER_PAYMENT_NOT_SENT_CONFIRMATION_REQUIRED",
                    status_code=409,
                )
            if order.paid_reported_at is not None:
                raise ApiError("ORDER_PAYMENT_ALREADY_REPORTED", status_code=409)
            if self.get_submitted_payment_report_for_order(order_id) is not None:
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            capacity_released = False
            if self._capacity is not None:
                capacity_released = self._capacity.release(
                    order_id=order.id,
                    reason=cancel_reason,
                )
            order.status = "cancelled"
            order.cancel_reason = cancel_reason
            order.updated_at = utc_now()
            self.add_state_event(
                order_id=order.id,
                from_status="waiting_payment",
                to_status="cancelled",
                event_type=event_type,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                reason=event_reason,
                request_id=request_id,
                metadata_json=event_metadata,
            )
            if self._audit is not None:
                self._audit.write(
                    event_type=audit_event_type,
                    actor_user_id=actor_user_id,
                    actor_role=actor_role,
                    resource_type="order",
                    resource_id=order.id,
                    request_id=request_id,
                    metadata_json=audit_metadata,
                )
                if capacity_released:
                    self._audit.write(
                        event_type="business_capacity_released",
                        actor_user_id=actor_user_id,
                        actor_role=actor_role,
                        resource_type="order",
                        resource_id=order.id,
                        request_id=request_id,
                        metadata_json={"reason": cancel_reason},
                    )
            return AtomicCancellationResult(
                order=order,
                ad_requires_expiration=False,
                capacity_released=capacity_released,
            )

    def update_order(self, order: OrderRecord, **fields: Any) -> OrderRecord:
        with self._lock:
            capacity_event_context = fields.pop("capacity_event_context", None)
            target_status = fields.get("status")
            transition_event = None
            changed = False
            if self._capacity is not None and target_status == "cancelled":
                transition_event = "business_capacity_released"
                changed = self._capacity.release(
                    order_id=order.id,
                    reason=(capacity_event_context or {}).get("reason", "order_cancelled"),
                )
            elif self._capacity is not None and target_status == "completed":
                transition_event = "business_capacity_consumed"
                changed = self._capacity.consume(
                    order_id=order.id,
                    reason=(capacity_event_context or {}).get("reason", "order_completed"),
                )
            for key, value in fields.items():
                setattr(order, key, value)
            order.updated_at = utc_now()
            if changed and transition_event and self._audit is not None:
                context = capacity_event_context or {}
                self._audit.write(
                    event_type=transition_event,
                    actor_user_id=context.get("actor_user_id"),
                    actor_role=context.get("actor_role"),
                    resource_type="order",
                    resource_id=order.id,
                    request_id=context.get("request_id", "capacity_transition"),
                    metadata_json={"reason": context.get("reason")},
                )
            return order

