from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.ads.row_mappers import ad_from_row, credit_ledger_from_row
from app.modules.disputes.models import DisputeRecord
from app.modules.disputes.row_mappers import dispute_from_row
from app.modules.orders.models import OrderRecord
from app.modules.orders.row_mappers import jsonb, order_from_row


class PostgresAdminDisputeResolutionMixin:
    def resolve_admin_dispute_atomically(
        self,
        *,
        dispute_id: str,
        resolution_type: str,
        reason: str,
        notes: str | None,
        actor_user_id: str,
        actor_role: str,
        request_id: str,
    ) -> tuple[DisputeRecord, OrderRecord, str, dict[str, Any], dict[str, Any] | None]:
        # This is the durable boundary for Admin terminal resolution. The order,
        # dispute, capacity, credit ledger, ad and audit records must commit
        # together so a resolved order cannot leave a blocked ad behind.
        with self._connect() as conn:  # type: ignore[attr-defined]
            dispute_row, order_row = self._lock_resolvable_admin_dispute_rows(conn, dispute_id=dispute_id)
            if resolution_type == "keep_under_review":
                return self._mark_admin_dispute_in_review_in_transaction(
                    conn,
                    dispute_row=dispute_row,
                    order_row=order_row,
                    reason=reason,
                    notes=notes,
                    actor_user_id=actor_user_id,
                    actor_role=actor_role,
                    request_id=request_id,
                )
            return self._resolve_terminal_admin_dispute_in_transaction(
                conn,
                dispute_row=dispute_row,
                order_row=order_row,
                resolution_type=resolution_type,
                reason=reason,
                notes=notes,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                request_id=request_id,
            )

    def _lock_resolvable_admin_dispute_rows(self, conn, *, dispute_id: str):  # type: ignore[no-untyped-def]
        dispute_row = conn.execute(
            "select * from disputes where id = %s for update",
            (dispute_id,),
        ).fetchone()
        if dispute_row is None:
            raise ApiError("DISPUTE_NOT_FOUND", status_code=404)
        if dispute_row["status"] not in {"open", "in_review"}:
            raise ApiError("DISPUTE_STATUS_INVALID", status_code=409)
        order_row = conn.execute(
            "select * from orders where id = %s for update",
            (dispute_row["order_id"],),
        ).fetchone()
        if order_row is None:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        if order_row["status"] != "disputed":
            raise ApiError("ORDER_STATUS_INVALID", status_code=409)
        return dispute_row, order_row

    def _mark_admin_dispute_in_review_in_transaction(
        self,
        conn,
        *,
        dispute_row,
        order_row,
        reason: str,
        notes: str | None,
        actor_user_id: str,
        actor_role: str,
        request_id: str,
    ) -> tuple[DisputeRecord, OrderRecord, str, dict[str, Any], dict[str, Any] | None]:  # type: ignore[no-untyped-def]
        updated_dispute_row = conn.execute(
            """
            update disputes
            set status = 'in_review',
                resolution_type = 'keep_under_review',
                resolution_reason = %s,
                updated_at = now()
            where id = %s
            returning *
            """,
            (reason, dispute_row["id"]),
        ).fetchone()
        credit_effect = {"type": "none", "amount": 0, "ledger_id": None}
        self._insert_admin_dispute_resolution_events(
            conn,
            dispute_id=str(dispute_row["id"]),
            order_id=str(order_row["id"]),
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            request_id=request_id,
            reason=reason,
            notes=notes,
            event_type="dispute_marked_in_review",
            old_dispute_status=dispute_row["status"],
            new_dispute_status="in_review",
            old_order_status=order_row["status"],
            new_order_status=order_row["status"],
            resolution_type="keep_under_review",
            credit_effect=credit_effect,
        )
        conn.commit()
        return dispute_from_row(updated_dispute_row), order_from_row(order_row), "dispute_marked_in_review", credit_effect, None

    def _resolve_terminal_admin_dispute_in_transaction(
        self,
        conn,
        *,
        dispute_row,
        order_row,
        resolution_type: str,
        reason: str,
        notes: str | None,
        actor_user_id: str,
        actor_role: str,
        request_id: str,
    ) -> tuple[DisputeRecord, OrderRecord, str, dict[str, Any], dict[str, Any] | None]:  # type: ignore[no-untyped-def]
        updated_order_row = self._update_order_for_admin_dispute_resolution(
            conn,
            order_id=str(order_row["id"]),
            resolution_type=resolution_type,
        )
        target_status = updated_order_row["status"]
        self._apply_terminal_publication_cooldown_in_transaction(  # type: ignore[attr-defined]
            conn,
            order_row=order_row,
            target_status=target_status,
        )
        self._transition_capacity_for_admin_dispute_resolution(
            conn,
            order_id=str(order_row["id"]),
            target_order_status=target_status,
            resolution_type=resolution_type,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            request_id=request_id,
        )
        target_dispute_status = "cancelled" if resolution_type == "cancelled" else "resolved"
        updated_dispute_row = self._update_dispute_for_terminal_admin_resolution(
            conn,
            dispute_id=str(dispute_row["id"]),
            target_dispute_status=target_dispute_status,
            resolution_type=resolution_type,
            reason=reason,
            actor_user_id=actor_user_id,
        )
        credit_effect, ad_payload = self._apply_admin_resolution_credit_and_ad_in_transaction(
            conn,
            order_row=order_row,
            dispute_row=dispute_row,
            resolution_type=resolution_type,
            actor_user_id=actor_user_id,
        )
        self._insert_admin_dispute_resolution_events(
            conn,
            dispute_id=str(dispute_row["id"]),
            order_id=str(order_row["id"]),
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            request_id=request_id,
            reason=reason,
            notes=notes,
            event_type="dispute_resolved",
            old_dispute_status=dispute_row["status"],
            new_dispute_status=target_dispute_status,
            old_order_status=order_row["status"],
            new_order_status=target_status,
            resolution_type=resolution_type,
            credit_effect=credit_effect,
        )
        conn.commit()
        return dispute_from_row(updated_dispute_row), order_from_row(updated_order_row), "dispute_resolved", credit_effect, ad_payload

    def _transition_capacity_for_admin_dispute_resolution(
        self,
        conn,
        *,
        order_id: str,
        target_order_status: str,
        resolution_type: str,
        actor_user_id: str,
        actor_role: str,
        request_id: str,
    ) -> None:  # type: ignore[no-untyped-def]
        transition_event = None
        if self._capacity is not None and target_order_status == "cancelled":  # type: ignore[attr-defined]
            transition_event = "business_capacity_released"
            changed = self._capacity.transition_in_transaction(  # type: ignore[attr-defined]
                conn,
                order_id=order_id,
                target_status="released",
                reason=f"dispute_{resolution_type}",
            )
        elif self._capacity is not None and target_order_status == "completed":  # type: ignore[attr-defined]
            transition_event = "business_capacity_consumed"
            changed = self._capacity.transition_in_transaction(  # type: ignore[attr-defined]
                conn,
                order_id=order_id,
                target_status="consumed",
                reason=f"dispute_{resolution_type}",
            )
        else:
            changed = False
        if changed and transition_event:
            self._insert_capacity_transition_audit(
                conn,
                order_id=order_id,
                event_type=transition_event,
                context={
                    "actor_user_id": actor_user_id,
                    "actor_role": actor_role,
                    "request_id": request_id,
                    "reason": f"dispute_{resolution_type}",
                },
            )

    def _update_dispute_for_terminal_admin_resolution(
        self,
        conn,
        *,
        dispute_id: str,
        target_dispute_status: str,
        resolution_type: str,
        reason: str,
        actor_user_id: str,
    ):  # type: ignore[no-untyped-def]
        return conn.execute(
            """
            update disputes
            set status = %s,
                resolution_type = %s,
                resolution_reason = %s,
                resolved_by_admin_id = %s,
                resolved_at = now(),
                cancelled_at = case when %s = 'cancelled' then now() else null end,
                updated_at = now()
            where id = %s
            returning *
            """,
            (target_dispute_status, resolution_type, reason, actor_user_id, target_dispute_status, dispute_id),
        ).fetchone()

    def _update_order_for_admin_dispute_resolution(self, conn, *, order_id: str, resolution_type: str):  # type: ignore[no-untyped-def]
        if resolution_type in {"remitter_favored", "cancelled"}:
            return conn.execute(
                """
                update orders
                set status = 'cancelled',
                    cancel_reason = 'admin_cancelled',
                    updated_at = now()
                where id = %s
                returning *
                """,
                (order_id,),
            ).fetchone()
        if resolution_type in {"business_favored", "completed"}:
            return conn.execute(
                """
                update orders
                set status = 'completed',
                    completion_reason = 'admin_resolved',
                    completed_at = now(),
                    updated_at = now()
                where id = %s
                returning *
                """,
                (order_id,),
            ).fetchone()
        raise ApiError("DISPUTE_RESOLUTION_TYPE_INVALID", status_code=400)

    def _apply_admin_resolution_credit_and_ad_in_transaction(
        self,
        conn,
        *,
        order_row,
        dispute_row,
        resolution_type: str,
        actor_user_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:  # type: ignore[no-untyped-def]
        credit_effect: dict[str, Any] = {"type": "none", "amount": 0, "ledger_id": None}
        ad_row = conn.execute("select * from ads where id = %s for update", (order_row["ad_id"],)).fetchone()
        if ad_row is None:
            return credit_effect, None
        ad = ad_from_row(ad_row)
        should_move_blocked = dispute_row["previous_order_status"] in {"payment_reported", "payment_rejected"}
        if should_move_blocked and resolution_type == "cancelled":
            ledger_row = self._ads.release_hold_in_transaction(  # type: ignore[attr-defined]
                conn,
                ad=ad,
                created_by=actor_user_id,
                reason="admin_dispute_resolution_release",
                related_order_id=str(order_row["id"]),
                source="disputes",
            )
            if ledger_row is not None:
                ledger = credit_ledger_from_row(ledger_row)
                credit_effect = {"type": "release", "amount": ledger.amount, "ledger_id": ledger.id}
        elif should_move_blocked:
            ledger_row = self._ads.consume_hold_for_order_in_transaction(  # type: ignore[attr-defined]
                conn,
                ad=ad,
                order_id=str(order_row["id"]),
                created_by=actor_user_id,
                reason="admin_dispute_resolution_consume",
                source="disputes",
            )
            ledger = credit_ledger_from_row(ledger_row)
            credit_effect = {"type": "consume", "amount": ledger.amount, "ledger_id": ledger.id}

        updated_ad_row = conn.execute(
            "update ads set status = 'archived', updated_at = now() where id = %s returning *",
            (ad_row["id"],),
        ).fetchone()
        ad = ad_from_row(updated_ad_row)
        return credit_effect, {"id": ad.id, "status": ad.status}

    def _insert_admin_dispute_resolution_events(
        self,
        conn,
        *,
        dispute_id: str,
        order_id: str,
        actor_user_id: str,
        actor_role: str,
        request_id: str,
        reason: str,
        notes: str | None,
        event_type: str,
        old_dispute_status: str,
        new_dispute_status: str,
        old_order_status: str,
        new_order_status: str,
        resolution_type: str,
        credit_effect: dict[str, Any],
    ) -> None:  # type: ignore[no-untyped-def]
        metadata = {"resolution_type": resolution_type, "notes": notes, "credit_effect": credit_effect}
        conn.execute(
            """
            insert into dispute_events (
                dispute_id, order_id, actor_user_id, actor_role, event_type,
                old_status, new_status, reason, metadata_json, created_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            """,
            (dispute_id, order_id, actor_user_id, actor_role, event_type, old_dispute_status, new_dispute_status, reason, jsonb(metadata)),
        )
        if new_order_status != old_order_status:
            conn.execute(
                """
                insert into order_state_events (
                    order_id, from_status, to_status, event_type, actor_user_id,
                    actor_role, reason, request_id, metadata_json, created_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                """,
                (
                    order_id,
                    old_order_status,
                    new_order_status,
                    event_type,
                    actor_user_id,
                    actor_role,
                    reason,
                    request_id,
                    jsonb({"dispute_id": dispute_id, "resolution_type": resolution_type, "credit_effect": credit_effect}),
                ),
            )
        conn.execute(
            """
            insert into audit_logs (
                actor_user_id, actor_role, event_type, resource_type,
                resource_id, request_id, metadata_json, created_at
            )
            values (%s, %s, %s, 'dispute', %s, %s, %s, now())
            """,
            (
                actor_user_id,
                actor_role,
                event_type,
                dispute_id,
                request_id,
                jsonb(
                    {
                        "order_id": order_id,
                        "resolution_type": resolution_type,
                        "new_dispute_status": new_dispute_status,
                        "new_order_status": new_order_status,
                        "credit_effect": credit_effect,
                    }
                ),
            ),
        )
