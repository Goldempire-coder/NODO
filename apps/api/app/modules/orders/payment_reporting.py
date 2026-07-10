from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.core.errors import ApiError
from app.modules.orders.helpers import require_uuid
from app.modules.orders.payment_constants import PAYMENT_REPORT_DISCLAIMER
from app.modules.orders.payment_report_builder import build_payment_report_plan, payment_report_audit_metadata, payment_report_state_metadata
from app.modules.orders.policy import require_order_owner, require_remitter
from app.modules.orders.schemas import PaymentReportRequest
from app.modules.orders.serializers import payment_report_order_payload, payment_report_payload
from app.modules.orders.state_machine import now_utc, require_payment_report_allowed
from app.modules.users.models import UserRecord
from app.shared.idempotency.store import canonical_payload_hash


class PaymentReportingMixin:
    def report_payment(self, *, user: UserRecord, order_id: str, payload: PaymentReportRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        require_remitter(user)
        self._rate_limit("payment_report", user)  # type: ignore[attr-defined]
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND") or order_id
        payload_hash = canonical_payload_hash({"order_id": order_id, **payload.model_dump()})
        existing_by_key = self._repository.get_payment_report_by_idempotency_key(reported_by_user_id=user.id, idempotency_key=idempotency_key)  # type: ignore[attr-defined]
        if existing_by_key is not None:
            return self._existing_payment_report_response(existing_by_key=existing_by_key, payload_hash=payload_hash)

        def compute() -> dict[str, Any]:
            return self._compute_payment_report(
                user=user,
                order_id=order_id,
                payload=payload,
                payload_hash=payload_hash,
                idempotency_key=idempotency_key,
                request_id=request_id,
            )

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"orders:payment_report:{user.id}:{order_id}:{idempotency_key}",
            payload={"order_id": order_id, **payload.model_dump()},
            compute=compute,
        )

    def _existing_payment_report_response(self, *, existing_by_key, payload_hash: str) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        if existing_by_key.report_payload_hash != payload_hash:
            raise ApiError("IDEMPOTENCY_PAYLOAD_MISMATCH", status_code=409)
        order = self._repository.get_by_id(existing_by_key.order_id)  # type: ignore[attr-defined]
        if order is None:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        return {"payment_report": payment_report_payload(existing_by_key), "order": payment_report_order_payload(order), "disclaimer": PAYMENT_REPORT_DISCLAIMER}

    def _compute_payment_report(
        self,
        *,
        user: UserRecord,
        order_id: str,
        payload: PaymentReportRequest,
        payload_hash: str,
        idempotency_key: str,
        request_id: str,
    ) -> dict[str, Any]:
        order = self._reportable_order(user=user, order_id=order_id)
        report = self._create_payment_report(user=user, order=order, payload=payload, payload_hash=payload_hash, idempotency_key=idempotency_key)
        updated = self._mark_order_payment_reported(order=order)
        self._record_payment_reported(user=user, order=order, report=report, idempotency_key=idempotency_key, request_id=request_id)
        return {"payment_report": payment_report_payload(report), "order": payment_report_order_payload(updated), "disclaimer": PAYMENT_REPORT_DISCLAIMER}

    def _reportable_order(self, *, user: UserRecord, order_id: str):  # type: ignore[no-untyped-def]
        order = self._repository.get_by_id(order_id)  # type: ignore[attr-defined]
        if order is None:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        require_order_owner(user, order)
        require_payment_report_allowed(order)
        return order

    def _create_payment_report(self, *, user: UserRecord, order, payload: PaymentReportRequest, payload_hash: str, idempotency_key: str):  # type: ignore[no-untyped-def]
        plan = build_payment_report_plan(
            user=user,
            order=order,
            payload=payload,
            payload_hash=payload_hash,
            idempotency_key=idempotency_key,
            proof_lookup=self._repository.get_payment_evidence_file,  # type: ignore[attr-defined]
        )
        return self._repository.create_payment_report(**plan.create_report_fields)  # type: ignore[attr-defined]

    def _mark_order_payment_reported(self, *, order):  # type: ignore[no-untyped-def]
        now = now_utc()
        return self._repository.update_order(  # type: ignore[attr-defined]
            order,
            status="payment_reported",
            paid_reported_at=now,
            business_response_warning_at=now + timedelta(hours=2),
            business_response_deadline_at=now + timedelta(hours=6),
        )

    def _record_payment_reported(self, *, user: UserRecord, order, report, idempotency_key: str, request_id: str) -> None:  # type: ignore[no-untyped-def]
        self._repository.add_state_event(  # type: ignore[attr-defined]
            order_id=order.id,
            from_status="waiting_payment",
            to_status="payment_reported",
            event_type="payment_reported",
            actor_user_id=user.id,
            actor_role=user.role,
            reason=None,
            request_id=request_id,
            metadata_json=payment_report_state_metadata(report, idempotency_key=idempotency_key),
        )
        self._audit.write(  # type: ignore[attr-defined]
            event_type="payment_reported",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="order",
            resource_id=order.id,
            request_id=request_id,
            metadata_json=payment_report_audit_metadata(report),
        )
