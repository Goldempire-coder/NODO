from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.errors import ApiError
from app.modules.orders.models import OrderReceiverDetailsRecord, OrderRecord
from app.modules.orders.row_mappers import order_from_row


def receiver_details_from_row(row) -> OrderReceiverDetailsRecord:  # type: ignore[no-untyped-def]
    return OrderReceiverDetailsRecord(
        id=str(row["id"]),
        order_id=str(row["order_id"]),
        bank_code=row["bank_code"],
        phone=row["phone"],
        document=row["document"],
        holder=row["holder"],
        payload_hash=row["payload_hash"],
        shared_by_user_id=str(row["shared_by_user_id"]),
        shared_at=row["shared_at"],
    )


class PostgresOrderReceiverCompletionMixin:
    def create_receiver_details_atomically(
        self,
        *,
        order_id: str,
        remitter_user_id: str,
        payload: dict[str, str],
        payload_hash: str,
        request_id: str,
        audit_metadata: dict[str, Any],
    ) -> tuple[OrderReceiverDetailsRecord, bool]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            order_row = conn.execute(
                "select * from orders where id = %s for update",
                (order_id,),
            ).fetchone()
            if order_row is None or str(order_row["remitter_user_id"]) != remitter_user_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            existing = conn.execute(
                "select * from order_receiver_details where order_id = %s",
                (order_id,),
            ).fetchone()
            if existing is not None:
                if existing["payload_hash"] == payload_hash:
                    return receiver_details_from_row(existing), False
                raise ApiError("ORDER_RECEIVER_DETAILS_ALREADY_SHARED", status_code=409)
            if order_row["status"] != "payment_confirmed":
                raise ApiError("ORDER_STATUS_INVALID", status_code=409)
            row = conn.execute(
                """
                insert into order_receiver_details (
                    order_id, bank_code, phone, document, holder, payload_hash,
                    shared_by_user_id, shared_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, now())
                returning *
                """,
                (
                    order_id,
                    payload["bank"],
                    payload["phone"],
                    payload["document"],
                    payload["holder"],
                    payload_hash,
                    remitter_user_id,
                ),
            ).fetchone()
            self._insert_integrity_audit(  # type: ignore[attr-defined]
                conn,
                event_type="order_receiver_details_shared",
                actor_user_id=remitter_user_id,
                actor_role="remitter",
                resource_type="order_receiver_details",
                resource_id=str(row["id"]),
                request_id=request_id,
                metadata_json=audit_metadata,
            )
            conn.commit()
        return receiver_details_from_row(row), True

    def has_receiver_details(self, order_id: str) -> bool:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                "select 1 from order_receiver_details where order_id = %s",
                (order_id,),
            ).fetchone()
        return row is not None

    def receiver_details_order_ids(self, order_ids: list[str]) -> set[str]:
        if not order_ids:
            return set()
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(
                """
                select order_id::text as order_id
                from order_receiver_details
                where order_id = any(%s::uuid[])
                """,
                (order_ids,),
            ).fetchall()
        return {row["order_id"] for row in rows}

    def get_receiver_details(self, order_id: str) -> OrderReceiverDetailsRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                "select * from order_receiver_details where order_id = %s",
                (order_id,),
            ).fetchone()
        return receiver_details_from_row(row) if row else None

    def reveal_receiver_details_with_audit(
        self,
        *,
        order_id: str,
        actor_user_id: str,
        actor_role: str,
        business_owner_user_id: str | None,
        request_id: str,
        audit_metadata: dict[str, Any],
    ) -> OrderReceiverDetailsRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            order_row = conn.execute(
                "select * from orders where id = %s for share",
                (order_id,),
            ).fetchone()
            if order_row is None:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            is_remitter = actor_role == "remitter" and str(order_row["remitter_user_id"]) == actor_user_id
            is_business_owner = actor_role == "business_owner" and business_owner_user_id == actor_user_id
            if not (is_remitter or is_business_owner):
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if order_row["status"] not in {"payment_confirmed", "delivered", "disputed"}:
                raise ApiError("ORDER_STATUS_INVALID", status_code=409)
            row = conn.execute(
                "select * from order_receiver_details where order_id = %s",
                (order_id,),
            ).fetchone()
            if row is None:
                raise ApiError("ORDER_RECEIVER_DETAILS_NOT_FOUND", status_code=404)
            self._insert_integrity_audit(  # type: ignore[attr-defined]
                conn,
                event_type="order_receiver_details_viewed",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                resource_type="order_receiver_details",
                resource_id=str(row["id"]),
                request_id=request_id,
                metadata_json=audit_metadata,
            )
            conn.commit()
        return receiver_details_from_row(row)

    def mark_delivered_atomically(
        self,
        *,
        order_id: str,
        business_id: str,
        actor_user_id: str,
        actor_role: str,
        delivered_at: datetime,
        warning_12h_at: datetime,
        warning_23h_at: datetime,
        auto_complete_at: datetime,
        reason: str | None,
        request_id: str,
        event_metadata: dict[str, Any],
        audit_metadata: dict[str, Any],
    ) -> OrderRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            order_row = conn.execute(
                "select * from orders where id = %s for update",
                (order_id,),
            ).fetchone()
            if order_row is None or str(order_row["business_id"]) != business_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if order_row["status"] != "payment_confirmed":
                raise ApiError("DELIVERY_NOT_ALLOWED", status_code=409)
            receiver_details_row = conn.execute(
                "select 1 from order_receiver_details where order_id = %s",
                (order_id,),
            ).fetchone()
            if receiver_details_row is None:
                raise ApiError("ORDER_RECEIVER_DETAILS_REQUIRED", status_code=409)
            updated_row = conn.execute(
                """
                update orders
                set status = 'delivered', delivered_at = %s,
                    auto_complete_warning_12h_at = %s,
                    auto_complete_warning_23h_at = %s,
                    auto_complete_at = %s, updated_at = now()
                where id = %s and status = 'payment_confirmed'
                returning *
                """,
                (delivered_at, warning_12h_at, warning_23h_at, auto_complete_at, order_id),
            ).fetchone()
            if updated_row is None:
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            self._insert_integrity_state_event(  # type: ignore[attr-defined]
                conn,
                order_id=order_id,
                from_status="payment_confirmed",
                to_status="delivered",
                event_type="order_delivered",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                reason=reason,
                request_id=request_id,
                metadata_json=event_metadata,
            )
            self._insert_integrity_audit(  # type: ignore[attr-defined]
                conn,
                event_type="order_delivered",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                resource_id=order_id,
                request_id=request_id,
                metadata_json=audit_metadata,
            )
            conn.commit()
        return order_from_row(updated_row)

    def confirm_received_atomically(
        self,
        *,
        order_id: str,
        remitter_user_id: str,
        completed_at: datetime,
        request_id: str,
        event_metadata: dict[str, Any],
        audit_metadata: dict[str, Any],
    ) -> OrderRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            order_row = conn.execute(
                "select * from orders where id = %s for update",
                (order_id,),
            ).fetchone()
            if order_row is None or str(order_row["remitter_user_id"]) != remitter_user_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if order_row["status"] != "delivered":
                raise ApiError("ORDER_RECEIPT_CONFIRMATION_NOT_ALLOWED", status_code=409)
            dispute = conn.execute(
                """
                select 1 from disputes
                where order_id = %s and status in ('open', 'in_review')
                limit 1
                """,
                (order_id,),
            ).fetchone()
            if dispute is not None:
                raise ApiError("ORDER_COMPLETION_BLOCKED_BY_DISPUTE", status_code=409)
            capacity_consumed = self._capacity.transition_in_transaction(  # type: ignore[attr-defined]
                conn,
                order_id=order_id,
                target_status="consumed",
                reason="manual_confirmed",
            )
            if not capacity_consumed:
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            updated_row = conn.execute(
                """
                update orders
                set status = 'completed', completion_reason = 'manual_confirmed',
                    completed_at = %s, updated_at = now()
                where id = %s and status = 'delivered'
                returning *
                """,
                (completed_at, order_id),
            ).fetchone()
            if updated_row is None:
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            self._apply_terminal_publication_cooldown_in_transaction(  # type: ignore[attr-defined]
                conn,
                order_row=order_row,
                target_status="completed",
            )
            self._insert_integrity_state_event(  # type: ignore[attr-defined]
                conn,
                order_id=order_id,
                from_status="delivered",
                to_status="completed",
                event_type="order_completed",
                actor_user_id=remitter_user_id,
                actor_role="remitter",
                reason="manual_confirmed",
                request_id=request_id,
                metadata_json=event_metadata,
            )
            self._insert_integrity_audit(  # type: ignore[attr-defined]
                conn,
                event_type="order_completed",
                actor_user_id=remitter_user_id,
                actor_role="remitter",
                resource_id=order_id,
                request_id=request_id,
                metadata_json=audit_metadata,
            )
            self._insert_capacity_transition_audit(  # type: ignore[attr-defined]
                conn,
                order_id=order_id,
                event_type="business_capacity_consumed",
                context={
                    "actor_user_id": remitter_user_id,
                    "actor_role": "remitter",
                    "request_id": request_id,
                    "reason": "manual_confirmed",
                },
            )
            conn.commit()
        return order_from_row(updated_row)
