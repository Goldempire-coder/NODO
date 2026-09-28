from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.errors import ApiError
from app.modules.disputes.models import DisputeRecord
from app.modules.disputes.row_mappers import dispute_from_row
from app.modules.orders.models import OrderRecord
from app.modules.orders.overdue_dispute_rules import (
    OVERDUE_DISPUTE_DESCRIPTION,
    OVERDUE_DISPUTE_RULES,
)
from app.modules.orders.row_mappers import jsonb, order_from_row


class PostgresOrderJobTransitionsMixin:
    def open_overdue_dispute_atomically(
        self,
        *,
        order_id: str,
        reason: str,
        transition_at: datetime,
        request_id: str,
        event_metadata: dict[str, Any],
    ) -> tuple[OrderRecord, DisputeRecord] | None:
        expected_status, deadline_field, event_type = OVERDUE_DISPUTE_RULES[reason]
        with self._connect() as conn:  # type: ignore[attr-defined]
            order_row = conn.execute(
                "select * from orders where id = %s for update",
                (order_id,),
            ).fetchone()
            if (
                order_row is None
                or order_row["status"] != expected_status
                or order_row[deadline_field] is None
                or order_row[deadline_field] > transition_at
            ):
                return None
            existing = conn.execute(
                "select id from disputes where order_id = %s and status in ('open', 'in_review') limit 1",
                (order_id,),
            ).fetchone()
            if existing is not None:
                return None
            dispute_row = conn.execute(
                """
                insert into disputes (
                    order_id, opened_by_user_id, opened_by_role, previous_order_status,
                    reason, description, status, created_at, updated_at
                )
                values (%s, %s, 'remitter', %s, %s, %s, 'open', now(), now())
                returning *
                """,
                (
                    order_id,
                    order_row["remitter_user_id"],
                    expected_status,
                    reason,
                    OVERDUE_DISPUTE_DESCRIPTION,
                ),
            ).fetchone()
            updated_row = conn.execute(
                """
                update orders
                set status = 'disputed', dispute_reason = %s, updated_at = now()
                where id = %s and status = %s
                returning *
                """,
                (reason, order_id, expected_status),
            ).fetchone()
            if updated_row is None:
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            dispute_id = str(dispute_row["id"])
            conn.execute(
                """
                insert into dispute_events (
                    dispute_id, order_id, actor_user_id, actor_role, event_type,
                    old_status, new_status, reason, metadata_json, created_at
                )
                values (%s, %s, %s, 'remitter', 'dispute_opened', null, 'open', %s, %s, now())
                """,
                (
                    dispute_id,
                    order_id,
                    order_row["remitter_user_id"],
                    reason,
                    jsonb(event_metadata),
                ),
            )
            self._insert_integrity_state_event(  # type: ignore[attr-defined]
                conn,
                order_id=order_id,
                from_status=expected_status,
                to_status="disputed",
                event_type=event_type,
                actor_user_id=None,
                actor_role=None,
                reason=reason,
                request_id=request_id,
                metadata_json=event_metadata,
            )
            self._insert_integrity_audit(  # type: ignore[attr-defined]
                conn,
                event_type=event_type,
                actor_user_id=None,
                actor_role=None,
                resource_id=order_id,
                request_id=request_id,
                metadata_json={**event_metadata, "dispute_id": dispute_id},
            )
            conn.commit()
        return order_from_row(updated_row), dispute_from_row(dispute_row)
