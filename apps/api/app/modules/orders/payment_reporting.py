from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.core.errors import ApiError
from app.modules.orders.helpers import require_uuid
from app.modules.orders.payment_constants import PAYMENT_REPORT_DISCLAIMER
from app.modules.orders.payment_report_builder import (
    build_payment_report_plan,
    payment_report_plan_audit_metadata,
    payment_report_plan_state_metadata,
)
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
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND")
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
        plan = build_payment_report_plan(
            user=user,
            order=order,
            payload=payload,
            payload_hash=payload_hash,
            idempotency_key=idempotency_key,
            proof_lookup=self._repository.get_payment_evidence_file,  # type: ignore[attr-defined]
        )
        reported_at = now_utc()
        updated, report = self._repository.report_payment_atomically(  # type: ignore[attr-defined]
            order_id=order.id,
            remitter_user_id=user.id,
            create_report_fields=plan.create_report_fields,
            paid_reported_at=reported_at,
            business_response_warning_at=reported_at + timedelta(hours=2),
            business_response_deadline_at=reported_at + timedelta(hours=6),
            request_id=request_id,
            event_metadata=payment_report_plan_state_metadata(
                plan,
                idempotency_key=idempotency_key,
            ),
            audit_metadata=payment_report_plan_audit_metadata(plan),
        )
        self._notifications.payment_reported_business(order=updated, request_id=request_id)  # type: ignore[attr-defined]
        return {"payment_report": payment_report_payload(report), "order": payment_report_order_payload(updated), "disclaimer": PAYMENT_REPORT_DISCLAIMER}

    def _reportable_order(self, *, user: UserRecord, order_id: str):  # type: ignore[no-untyped-def]
        order = self._repository.get_by_id(order_id)  # type: ignore[attr-defined]
        if order is None:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        require_order_owner(user, order)
        try:
            require_payment_report_allowed(order)
        except ApiError as exc:
            if exc.code == "PAYMENT_REPORT_NOT_ALLOWED":
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409) from exc
            raise
        self._require_payment_details_shared(order)  # type: ignore[attr-defined]
        return order
