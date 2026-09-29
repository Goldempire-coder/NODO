from __future__ import annotations

from app.core.errors import ApiError
from app.modules.disputes.models import DisputeRecord
from app.modules.disputes.policy import (
    require_dispute_order_state,
    require_dispute_reason,
)
from app.modules.disputes.row_mappers import dispute_from_row
from app.modules.orders.models import OrderRecord
from app.modules.orders.row_mappers import jsonb, order_from_row


class PostgresParticipantDisputeMixin:
    def open_participant_dispute_atomically(
        self,
        *,
        order_id: str,
        expected_status: str,
        actor_user_id: str,
        actor_role: str,
        business_owner_user_id: str | None,
        reason: str,
        description: str | None,
        evidence_file_ids: list[str],
        request_id: str,
    ) -> tuple[OrderRecord, DisputeRecord]:
        # Ownership comes from the locked database context, not the earlier service read.
        with self._connect() as conn:
            row = conn.execute(
                """
                select order_row.*, business.owner_user_id as dispute_business_owner_id
                from orders order_row
                join businesses business on business.id = order_row.business_id
                where order_row.id = %s
                for update of order_row
                """,
                (order_id,),
            ).fetchone()
            if row is None or not (
                (
                    actor_role == "remitter"
                    and str(row["remitter_user_id"]) == actor_user_id
                )
                or (
                    actor_role == "business_owner"
                    and str(row["dispute_business_owner_id"]) == actor_user_id
                )
            ):
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            existing = conn.execute(
                "select id from disputes where order_id = %s and status in ('open', 'in_review') limit 1",
                (order_id,),
            ).fetchone()
            if existing is not None:
                raise ApiError("DISPUTE_ALREADY_OPEN", status_code=409)
            if row["status"] != expected_status:
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            require_dispute_order_state(order_from_row(row))
            require_dispute_reason(reason)
            dispute_row = conn.execute(
                """
                insert into disputes (
                    order_id, opened_by_user_id, opened_by_role, previous_order_status,
                    reason, description, status, created_at, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, 'open', now(), now()) returning *
                """,
                (
                    order_id,
                    actor_user_id,
                    actor_role,
                    expected_status,
                    reason,
                    description,
                ),
            ).fetchone()
            updated = conn.execute(
                """
                update orders set status = 'disputed', dispute_reason = %s, updated_at = now()
                where id = %s and status = %s returning *
                """,
                (reason, order_id, expected_status),
            ).fetchone()
            if updated is None:
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            dispute_id = str(dispute_row["id"])
            conn.execute(
                """
                insert into dispute_events (
                    dispute_id, order_id, actor_user_id, actor_role, event_type,
                    old_status, new_status, reason, metadata_json, created_at
                ) values (%s, %s, %s, %s, 'dispute_opened', null, 'open', %s, %s, now())
                """,
                (
                    dispute_id,
                    order_id,
                    actor_user_id,
                    actor_role,
                    reason,
                    jsonb(
                        {
                            "previous_order_status": expected_status,
                            "evidence_file_ids": evidence_file_ids,
                        }
                    ),
                ),
            )
            conn.execute(
                """
                insert into order_state_events (
                    order_id, from_status, to_status, event_type, actor_user_id,
                    actor_role, reason, request_id, metadata_json, created_at
                ) values (%s, %s, 'disputed', 'dispute_opened', %s, %s, %s, %s, %s, now())
                """,
                (
                    order_id,
                    expected_status,
                    actor_user_id,
                    actor_role,
                    reason,
                    request_id,
                    jsonb(
                        {
                            "dispute_id": dispute_id,
                            "previous_order_status": expected_status,
                        }
                    ),
                ),
            )
            conn.execute(
                """
                insert into audit_logs (
                    actor_user_id, actor_role, event_type, resource_type,
                    resource_id, request_id, metadata_json, created_at
                ) values (%s, %s, 'dispute_opened', 'dispute', %s, %s, %s, now())
                """,
                (
                    actor_user_id,
                    actor_role,
                    dispute_id,
                    request_id,
                    jsonb(
                        {
                            "order_id": order_id,
                            "previous_order_status": expected_status,
                            "new_order_status": "disputed",
                            "reason": reason,
                        }
                    ),
                ),
            )
            result = order_from_row(updated), dispute_from_row(dispute_row)
        return result
