from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.disputes.policy import (
    require_admin_dispute_resolve,
    require_dispute_resolution_reason,
    require_dispute_resolution_type,
)
from app.modules.disputes.presenters import dispute_payload, safe_order_summary
from app.modules.disputes.schemas import DisputeResolveRequest
from app.modules.disputes.service_constants import DISPUTE_DISCLAIMER
from app.modules.disputes.utils import require_uuid
from app.modules.orders.models import OrderRecord, utc_now
from app.modules.users.models import UserRecord


class AdminDisputeResolutionMixin:
    def resolve_admin_dispute(self, *, user: UserRecord, dispute_id: str, payload: DisputeResolveRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        require_admin_dispute_resolve(user)
        dispute_id = require_uuid(dispute_id, "DISPUTE_NOT_FOUND")
        request_payload = {"dispute_id": dispute_id, "resolution_type": payload.resolution_type, "reason": payload.reason, "notes": payload.notes}

        def compute() -> dict[str, Any]:
            return self._compute_admin_dispute_resolution(user=user, dispute_id=dispute_id, payload=payload, request_id=request_id)

        return self._idempotency.replay_or_store(f"disputes:resolve:{user.id}:{dispute_id}:{idempotency_key}", payload=request_payload, compute=compute)  # type: ignore[attr-defined]

    def _compute_admin_dispute_resolution(self, *, user: UserRecord, dispute_id: str, payload: DisputeResolveRequest, request_id: str) -> dict[str, Any]:
        dispute, order = self._resolvable_admin_dispute(user=user, dispute_id=dispute_id, payload=payload)
        old_dispute_status = dispute.status
        old_order_status = order.status
        atomic_resolver = getattr(self._orders, "resolve_admin_dispute_atomically", None)
        if callable(atomic_resolver):
            updated_dispute, updated_order, event_type, credit_effect, ad_payload = atomic_resolver(
                dispute_id=dispute.id,
                resolution_type=payload.resolution_type,
                reason=payload.reason,
                notes=payload.notes,
                actor_user_id=user.id,
                actor_role=user.role,
                request_id=request_id,
            )
        else:
            updated_dispute, updated_order, event_type, credit_effect, ad_payload = self._apply_admin_dispute_resolution(
                user=user,
                dispute=dispute,
                order=order,
                payload=payload,
                request_id=request_id,
            )
            self._record_admin_dispute_resolution(
                user=user,
                dispute=dispute,
                updated_dispute=updated_dispute,
                order=order,
                updated_order=updated_order,
                payload=payload,
                request_id=request_id,
                event_type=event_type,
                old_dispute_status=old_dispute_status,
                old_order_status=old_order_status,
                credit_effect=credit_effect,
            )
        self._notifications.order_dispute_resolution_parties(  # type: ignore[attr-defined]
            order=updated_order,
            dispute_id=updated_dispute.id,
            resolution_type=payload.resolution_type,
            request_id=request_id,
        )
        return {
            "dispute": dispute_payload(updated_dispute),
            "order": safe_order_summary(updated_order),
            "credit_effect": credit_effect,
            "ad": ad_payload,
            "disclaimer": DISPUTE_DISCLAIMER,
        }

    def _resolvable_admin_dispute(self, *, user: UserRecord, dispute_id: str, payload: DisputeResolveRequest):  # type: ignore[no-untyped-def]
        self._rate_limit("admin_resolve", user, dispute_id)
        require_dispute_resolution_type(payload.resolution_type)
        require_dispute_resolution_reason(payload.reason)
        dispute = self._repository.get_dispute(dispute_id)  # type: ignore[attr-defined]
        if dispute is None:
            raise ApiError("DISPUTE_NOT_FOUND", status_code=404)
        if dispute.status not in {"open", "in_review"}:
            raise ApiError("DISPUTE_STATUS_INVALID", status_code=409)
        order = self._orders.get_by_id(dispute.order_id)  # type: ignore[attr-defined]
        if order is None:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        if order.status != "disputed":
            raise ApiError("ORDER_STATUS_INVALID", status_code=409)
        return dispute, order

    def _apply_admin_dispute_resolution(self, *, user: UserRecord, dispute, order: OrderRecord, payload: DisputeResolveRequest, request_id: str):  # type: ignore[no-untyped-def]
        if payload.resolution_type == "keep_under_review":
            updated_dispute = self._repository.update_dispute(dispute, status="in_review", resolution_type=payload.resolution_type, resolution_reason=payload.reason)  # type: ignore[attr-defined]
            return updated_dispute, order, "dispute_marked_in_review", {"type": "none", "amount": 0, "ledger_id": None}, None

        updated_order = self._orders.update_order(  # type: ignore[attr-defined]
            order,
            **self._order_fields_for_dispute_resolution(payload),
            capacity_event_context={
                "actor_user_id": user.id,
                "actor_role": user.role,
                "request_id": request_id,
                "reason": f"dispute_{payload.resolution_type}",
            },
        )
        target_dispute_status = "cancelled" if payload.resolution_type == "cancelled" else "resolved"
        updated_dispute = self._repository.update_dispute(  # type: ignore[attr-defined]
            dispute,
            status=target_dispute_status,
            resolution_type=payload.resolution_type,
            resolution_reason=payload.reason,
            resolved_by_admin_id=user.id,
            resolved_at=updated_order.updated_at,
            cancelled_at=updated_order.updated_at if target_dispute_status == "cancelled" else None,
        )
        credit_effect, ad_payload = self._apply_resolution_credit_and_ad(user=user, dispute=dispute, order=order, resolution_type=payload.resolution_type)
        return updated_dispute, updated_order, "dispute_resolved", credit_effect, ad_payload

    def _order_fields_for_dispute_resolution(self, payload: DisputeResolveRequest) -> dict[str, Any]:
        if payload.resolution_type in {"remitter_favored", "cancelled"}:
            return {"status": "cancelled", "cancel_reason": "admin_cancelled"}
        if payload.resolution_type in {"business_favored", "completed"}:
            return {"status": "completed", "completion_reason": "admin_resolved", "completed_at": utc_now()}
        return {}

    def _apply_resolution_credit_and_ad(self, *, user: UserRecord, dispute, order: OrderRecord, resolution_type: str) -> tuple[dict[str, Any], dict[str, Any] | None]:  # type: ignore[no-untyped-def]
        credit_effect: dict[str, Any] = {"type": "none", "amount": 0, "ledger_id": None}
        ad_payload: dict[str, Any] | None = None
        ad = self._ads.get_ad(order.ad_id)  # type: ignore[attr-defined]
        if ad is None:
            return credit_effect, ad_payload
        should_move_blocked = dispute.previous_order_status in {"payment_reported", "payment_rejected"}
        if should_move_blocked and resolution_type == "cancelled":
            ledger = self._ads.release_hold(ad=ad, created_by=user.id, reason="admin_dispute_resolution_release", related_order_id=order.id, source="disputes")  # type: ignore[attr-defined]
            if ledger is not None:
                credit_effect = {"type": "release", "amount": ledger.amount, "ledger_id": ledger.id}
        elif should_move_blocked:
            ledger = self._ads.consume_hold_for_order(ad=ad, order_id=order.id, created_by=user.id, reason="admin_dispute_resolution_consume", source="disputes")  # type: ignore[attr-defined]
            credit_effect = {"type": "consume", "amount": ledger.amount, "ledger_id": ledger.id}
        self._ads.set_status(ad, "archived")  # type: ignore[attr-defined]
        ad_payload = {"id": ad.id, "status": ad.status}
        return credit_effect, ad_payload

    def _record_admin_dispute_resolution(
        self,
        *,
        user: UserRecord,
        dispute,
        updated_dispute,
        order: OrderRecord,
        updated_order: OrderRecord,
        payload: DisputeResolveRequest,
        request_id: str,
        event_type: str,
        old_dispute_status: str,
        old_order_status: str,
        credit_effect: dict[str, Any],
    ) -> None:  # type: ignore[no-untyped-def]
        self._repository.add_event(  # type: ignore[attr-defined]
            dispute_id=updated_dispute.id,
            order_id=order.id,
            actor_user_id=user.id,
            actor_role=user.role,
            event_type=event_type,
            old_status=old_dispute_status,
            new_status=updated_dispute.status,
            reason=payload.reason,
            metadata_json={"resolution_type": payload.resolution_type, "notes": payload.notes, "credit_effect": credit_effect},
        )
        if updated_order.status != old_order_status:
            self._orders.add_state_event(  # type: ignore[attr-defined]
                order_id=order.id,
                from_status=old_order_status,
                to_status=updated_order.status,
                event_type=event_type,
                actor_user_id=user.id,
                actor_role=user.role,
                reason=payload.reason,
                request_id=request_id,
                metadata_json={"dispute_id": updated_dispute.id, "resolution_type": payload.resolution_type, "credit_effect": credit_effect},
            )
        self._audit.write(  # type: ignore[attr-defined]
            event_type=event_type,
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="dispute",
            resource_id=updated_dispute.id,
            request_id=request_id,
            metadata_json={
                "order_id": order.id,
                "resolution_type": payload.resolution_type,
                "new_dispute_status": updated_dispute.status,
                "new_order_status": updated_order.status,
                "credit_effect": credit_effect,
            },
        )
