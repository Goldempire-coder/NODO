from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.errors import ApiError
from app.modules.businesses.access_control import evaluate_business_access
from app.modules.disputes.admin_resolution import AdminDisputeResolutionMixin
from app.modules.disputes.policy import (
    require_admin_dispute_read,
    require_dispute_order_state,
    require_dispute_open_permission,
    require_dispute_reason,
)
from app.modules.disputes.presenters import dispute_payload
from app.modules.disputes.schemas import DisputeCreateRequest
from app.modules.disputes.service_constants import DISPUTE_DISCLAIMER
from app.modules.disputes.utils import require_uuid
from app.modules.orders.models import OrderRecord
from app.modules.users.models import UserRecord


class DisputeService(AdminDisputeResolutionMixin):
    def __init__(self, *, settings: Settings, repository, order_repository, chat_repository, business_repository, ad_repository, audit_writer, rate_limiter, idempotency_store) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._orders = order_repository
        self._chat = chat_repository
        self._businesses = business_repository
        self._ads = ad_repository
        self._audit = audit_writer
        self._rate_limiter = rate_limiter
        self._idempotency = idempotency_store

    def _rate_limit(self, action: str, user: UserRecord, resource_id: str | None = None) -> None:
        key = f"disputes:{action}:{user.id}:{resource_id or 'global'}"
        if not self._rate_limiter.allow(
            key,
            max_attempts=self._settings.business_rate_limit_max_attempts,
            window_seconds=self._settings.business_rate_limit_window_seconds,
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def _order(self, order_id: str) -> OrderRecord:
        order_id = require_uuid(order_id, "ORDER_NOT_FOUND")
        order = self._orders.get_by_id(order_id)
        if order is None:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        return order

    def _business_owner_id(self, order: OrderRecord) -> str | None:
        business = self._businesses.get_business(order.business_id)
        return business.owner_user_id if business else None

    def _require_business_actor_access(self, user: UserRecord, order: OrderRecord) -> None:
        if user.role != "business_owner":
            return
        business = self._businesses.get_business(order.business_id)
        evaluate_business_access(user=user, business=business, business_repository=self._businesses)

    def _validate_evidence_files(self, *, user: UserRecord, order: OrderRecord, evidence_file_ids: list[str]) -> None:
        for evidence_file_id in evidence_file_ids:
            attachment = self._chat.get_attachment(evidence_file_id)
            if attachment is None or attachment.order_id != order.id or attachment.uploaded_by_user_id != user.id:
                raise ApiError("MESSAGE_ATTACHMENT_INVALID", status_code=400)

    def open_dispute(self, *, user: UserRecord, order_id: str, payload: DisputeCreateRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        order = self._order(order_id)
        normalized_evidence = [require_uuid(file_id, "MESSAGE_ATTACHMENT_INVALID") for file_id in payload.evidence_file_ids]
        request_payload = {"order_id": order.id, "reason": payload.reason, "description": payload.description, "evidence_file_ids": normalized_evidence}

        def compute() -> dict[str, Any]:
            dispute = self._compute_open_dispute(
                user=user,
                order=order,
                payload=payload,
                normalized_evidence=normalized_evidence,
                request_id=request_id,
            )
            return {"dispute": dispute_payload(dispute), "disclaimer": DISPUTE_DISCLAIMER}

        return self._idempotency.replay_or_store(f"disputes:open:{user.id}:{order.id}:{idempotency_key}", payload=request_payload, compute=compute)

    def _compute_open_dispute(
        self,
        *,
        user: UserRecord,
        order: OrderRecord,
        payload: DisputeCreateRequest,
        normalized_evidence: list[str],
        request_id: str,
    ):  # type: ignore[no-untyped-def]
        self._validate_open_dispute(user=user, order=order, payload=payload, normalized_evidence=normalized_evidence)
        previous_status = order.status
        updated = self._orders.update_order(order, status="disputed", dispute_reason=payload.reason)
        dispute = self._repository.create_dispute(
            order_id=order.id,
            opened_by_user_id=user.id,
            opened_by_role=user.role,
            previous_order_status=previous_status,
            reason=payload.reason,
            description=payload.description,
        )
        self._record_open_dispute(user=user, order=order, updated_order=updated, dispute=dispute, payload=payload, previous_status=previous_status, normalized_evidence=normalized_evidence, request_id=request_id)
        return dispute

    def _validate_open_dispute(self, *, user: UserRecord, order: OrderRecord, payload: DisputeCreateRequest, normalized_evidence: list[str]) -> None:
        self._rate_limit("open", user, order.id)
        require_dispute_reason(payload.reason)
        require_dispute_open_permission(user, order, self._business_owner_id(order))
        self._require_business_actor_access(user, order)
        existing = self._repository.get_open_for_order(order.id)
        if existing is not None:
            raise ApiError("DISPUTE_ALREADY_OPEN", status_code=409)
        require_dispute_order_state(order)
        self._validate_evidence_files(user=user, order=order, evidence_file_ids=normalized_evidence)

    def _record_open_dispute(
        self,
        *,
        user: UserRecord,
        order: OrderRecord,
        updated_order: OrderRecord,
        dispute,
        payload: DisputeCreateRequest,
        previous_status: str,
        normalized_evidence: list[str],
        request_id: str,
    ) -> None:  # type: ignore[no-untyped-def]
        self._repository.add_event(
            dispute_id=dispute.id,
            order_id=order.id,
            actor_user_id=user.id,
            actor_role=user.role,
            event_type="dispute_opened",
            old_status=None,
            new_status="open",
            reason=payload.reason,
            metadata_json={"previous_order_status": previous_status, "evidence_file_ids": normalized_evidence},
        )
        self._orders.add_state_event(
            order_id=order.id,
            from_status=previous_status,
            to_status="disputed",
            event_type="dispute_opened",
            actor_user_id=user.id,
            actor_role=user.role,
            reason=payload.reason,
            request_id=request_id,
            metadata_json={"dispute_id": dispute.id, "previous_order_status": previous_status},
        )
        self._audit.write(
            event_type="dispute_opened",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="dispute",
            resource_id=dispute.id,
            request_id=request_id,
            metadata_json={"order_id": order.id, "previous_order_status": previous_status, "new_order_status": updated_order.status, "reason": payload.reason},
        )

    def list_admin_disputes(self, *, user: UserRecord, status: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        require_admin_dispute_read(user)
        self._rate_limit("admin_list", user)
        if status is not None and status not in {"open", "in_review", "resolved", "cancelled"}:
            raise ApiError("DISPUTE_STATUS_INVALID", status_code=400)
        items, next_cursor = self._repository.list_disputes(status=status, cursor=cursor, limit=limit)
        return {"items": [dispute_payload(item) for item in items], "next_cursor": next_cursor, "disclaimer": DISPUTE_DISCLAIMER}

    def admin_dispute_detail(self, *, user: UserRecord, dispute_id: str, request_id: str) -> dict[str, Any]:
        require_admin_dispute_read(user)
        dispute_id = require_uuid(dispute_id, "DISPUTE_NOT_FOUND")
        self._rate_limit("admin_detail", user, dispute_id)
        dispute = self._repository.get_dispute(dispute_id)
        if dispute is None:
            raise ApiError("DISPUTE_NOT_FOUND", status_code=404)
        order = self._orders.get_by_id(dispute.order_id)
        events = self._repository.list_events(dispute.id)
        return {
            "dispute": dispute_payload(dispute),
            "order_summary": {
                "id": order.id if order else dispute.order_id,
                "public_order_code": order.public_order_code if order else None,
                "status": order.status if order else None,
                "amount_usd": str(order.amount_usd) if order else None,
            },
            "events": [
                {
                    "event_type": event.event_type,
                    "old_status": event.old_status,
                    "new_status": event.new_status,
                    "reason": event.reason,
                    "created_at": event.created_at.isoformat(),
                }
                for event in events
            ],
            "messages": [],
            "disclaimer": DISPUTE_DISCLAIMER,
        }

