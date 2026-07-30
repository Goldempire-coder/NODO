from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from psycopg.errors import UniqueViolation

from app.core.errors import ApiError
from app.modules.ads.row_mappers import ad_from_row
from app.modules.orders.integrity import AtomicCancellationResult
from app.modules.orders.models import OrderRecord, PaymentReportRecord
from app.modules.orders.row_mappers import jsonb, order_from_row, payment_report_from_row


class PostgresOrderIntegrityMixin:
    moves_ad_on_atomic_cancel = True

    def reveal_payment_instructions_atomically(
        self,
        *,
        order_id: str,
        remitter_user_id: str,
        request_id: str,
        audit_metadata: dict[str, Any],
    ) -> OrderRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            order_row = conn.execute(
                "select * from orders where id = %s for update",
                (order_id,),
            ).fetchone()
            locked_at = conn.execute(
                "select clock_timestamp() as locked_at"
            ).fetchone()["locked_at"]
            if order_row is None or str(order_row["remitter_user_id"]) != remitter_user_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if order_row["status"] != "waiting_payment":
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            if order_row["payment_report_deadline_at"] <= locked_at:
                raise ApiError("ORDER_EXPIRED", status_code=409)
            if (
                order_row["payment_data_revealed_at"] is None
                or order_row["payment_data_revealed_by"] is None
            ):
                order_row = conn.execute(
                    """
                    update orders
                    set payment_data_revealed_at = coalesce(payment_data_revealed_at, %s),
                        payment_data_revealed_by = coalesce(payment_data_revealed_by, %s),
                        updated_at = now()
                    where id = %s and status = 'waiting_payment'
                    returning *
                    """,
                    (locked_at, remitter_user_id, order_id),
                ).fetchone()
                if order_row is None:
                    raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            self._insert_integrity_audit(
                conn,
                event_type="payment_instructions_viewed",
                actor_user_id=remitter_user_id,
                actor_role="remitter",
                resource_id=order_id,
                request_id=request_id,
                metadata_json=audit_metadata,
            )
            conn.commit()
        return order_from_row(order_row)

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
        warning_delay = business_response_warning_at - paid_reported_at
        deadline_delay = business_response_deadline_at - paid_reported_at
        try:
            with self._connect() as conn:  # type: ignore[attr-defined]
                order_row = conn.execute(
                    "select * from orders where id = %s for update",
                    (order_id,),
                ).fetchone()
                locked_at = conn.execute(
                    "select clock_timestamp() as locked_at"
                ).fetchone()["locked_at"]
                self._require_reportable_locked_order(
                    order_row,
                    remitter_user_id=remitter_user_id,
                    payment_type=create_report_fields["payment_type"],
                    payment_amount=create_report_fields["payment_amount"],
                    now=locked_at,
                )
                existing = conn.execute(
                    "select 1 from payment_reports where order_id = %s and status = 'submitted' limit 1",
                    (order_id,),
                ).fetchone()
                if existing is not None:
                    raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
                proof_reuse = conn.execute(
                    "select 1 from payment_reports where id = %s for update",
                    (create_report_fields["report_id"],),
                ).fetchone()
                proof_file_id = create_report_fields.get("proof_file_id")
                if proof_reuse is None and proof_file_id is not None:
                    proof_reuse = conn.execute(
                        """
                        select 1
                        from payment_reports
                        where proof_file_id = %s
                        for update
                        """,
                        (proof_file_id,),
                    ).fetchone()
                proof_content_sha256 = create_report_fields.get("proof_content_sha256")
                if proof_reuse is None and proof_content_sha256 is not None:
                    proof_reuse = conn.execute(
                        """
                        select 1
                        from payment_reports
                        where proof_content_sha256 = %s
                        for update
                        """,
                        (proof_content_sha256,),
                    ).fetchone()
                if proof_reuse is not None:
                    raise ApiError(
                        "PAYMENT_REPORT_PROOF_ALREADY_USED",
                        status_code=409,
                    )
                report_row = self._insert_payment_report(  # type: ignore[attr-defined]
                    conn,
                    **create_report_fields,
                )
                updated_row = conn.execute(
                    """
                    update orders
                    set status = 'payment_reported',
                        paid_reported_at = %s,
                        business_response_warning_at = %s,
                        business_response_deadline_at = %s,
                        updated_at = now()
                    where id = %s and status = 'waiting_payment'
                    returning *
                    """,
                    (
                        locked_at,
                        locked_at + warning_delay,
                        locked_at + deadline_delay,
                        order_id,
                    ),
                ).fetchone()
                if updated_row is None:
                    raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
                self._insert_integrity_state_event(
                    conn,
                    order_id=order_id,
                    from_status="waiting_payment",
                    to_status="payment_reported",
                    event_type="payment_reported",
                    actor_user_id=remitter_user_id,
                    actor_role="remitter",
                    reason=None,
                    request_id=request_id,
                    metadata_json=event_metadata,
                )
                self._insert_integrity_audit(
                    conn,
                    event_type="payment_reported",
                    actor_user_id=remitter_user_id,
                    actor_role="remitter",
                    resource_id=order_id,
                    request_id=request_id,
                    metadata_json=audit_metadata,
                )
                conn.commit()
            return order_from_row(updated_row), payment_report_from_row(report_row)
        except UniqueViolation as exc:
            if exc.diag.constraint_name in {
                "payment_reports_network_tx_hash_unique_idx",
                "payment_reports_proof_content_sha256_unique_idx",
                "payment_reports_proof_file_unique_idx",
                "payment_reports_pkey",
            }:
                raise ApiError(
                    "PAYMENT_REPORT_PROOF_ALREADY_USED",
                    status_code=409,
                ) from exc
            raise

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
        with self._connect() as conn:  # type: ignore[attr-defined]
            order_row = conn.execute(
                "select * from orders where id = %s for update",
                (order_id,),
            ).fetchone()
            locked_at = conn.execute(
                "select clock_timestamp() as locked_at"
            ).fetchone()["locked_at"]
            if order_row is None:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if expected_remitter_user_id and str(order_row["remitter_user_id"]) != expected_remitter_user_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if expected_business_id and str(order_row["business_id"]) != expected_business_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            if order_row["status"] != "waiting_payment":
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            expired = order_row["payment_report_deadline_at"] <= locked_at
            if require_expired and not expired:
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            if not require_expired and expired:
                raise ApiError("ORDER_EXPIRED", status_code=409)
            if (
                enforce_payment_not_sent_confirmation
                and order_row["payment_data_revealed_at"] is not None
                and not payment_not_sent_confirmed
            ):
                raise ApiError(
                    "ORDER_PAYMENT_NOT_SENT_CONFIRMATION_REQUIRED",
                    status_code=409,
                )
            if order_row["paid_reported_at"] is not None:
                raise ApiError("ORDER_PAYMENT_ALREADY_REPORTED", status_code=409)
            report = conn.execute(
                "select 1 from payment_reports where order_id = %s and status = 'submitted' limit 1",
                (order_id,),
            ).fetchone()
            if report is not None:
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            ad_row = conn.execute(
                "select * from ads where id = %s for update",
                (order_row["ad_id"],),
            ).fetchone()
            if ad_row is None or ad_row["status"] != "in_order":
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            updated_row = conn.execute(
                """
                update orders
                set status = 'cancelled', cancel_reason = %s, updated_at = now()
                where id = %s and status = 'waiting_payment'
                returning *
                """,
                (cancel_reason, order_id),
            ).fetchone()
            if updated_row is None:
                raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
            capacity_released = False
            if self._capacity is not None:  # type: ignore[attr-defined]
                capacity_released = self._capacity.transition_in_transaction(  # type: ignore[attr-defined]
                    conn,
                    order_id=order_id,
                    target_status="released",
                    reason=cancel_reason,
                )
            ad_requires_expiration = (
                ad_row["expires_at"] is not None
                and ad_row["expires_at"] <= locked_at
            )
            if ad_requires_expiration:
                if self._ads is None:  # type: ignore[attr-defined]
                    raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
                ledger_row = self._ads.expire_hold_in_transaction(  # type: ignore[attr-defined]
                    conn,
                    ad=ad_from_row(ad_row),
                    created_by=actor_user_id,
                    reason="ad_expired_after_order_without_purchase",
                    related_order_id=order_id,
                    source="orders",
                )
                self._insert_integrity_audit(
                    conn,
                    event_type="ad_expired",
                    actor_user_id=actor_user_id,
                    actor_role=actor_role,
                    resource_type="ad",
                    resource_id=str(ad_row["id"]),
                    request_id=request_id,
                    metadata_json={"order_id": order_id},
                )
                if ledger_row is not None:
                    self._insert_integrity_audit(
                        conn,
                        event_type="credits_consumed",
                        actor_user_id=actor_user_id,
                        actor_role=actor_role,
                        resource_id=order_id,
                        request_id=request_id,
                        metadata_json={
                            "ledger_id": str(ledger_row["id"]),
                            "amount": ledger_row["amount"],
                            "ad_id": str(ad_row["id"]),
                            "reason": "ad_expired_after_order_without_purchase",
                        },
                    )
            else:
                conn.execute(
                    "update ads set status = 'active', updated_at = now() where id = %s",
                    (order_row["ad_id"],),
                )
            self._insert_integrity_state_event(
                conn,
                order_id=order_id,
                from_status="waiting_payment",
                to_status="cancelled",
                event_type=event_type,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                reason=event_reason,
                request_id=request_id,
                metadata_json=event_metadata,
            )
            self._insert_integrity_audit(
                conn,
                event_type=audit_event_type,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                resource_id=order_id,
                request_id=request_id,
                metadata_json=audit_metadata,
            )
            if capacity_released:
                self._insert_capacity_transition_audit(  # type: ignore[attr-defined]
                    conn,
                    order_id=order_id,
                    event_type="business_capacity_released",
                    context={
                        "actor_user_id": actor_user_id,
                        "actor_role": actor_role,
                        "request_id": request_id,
                        "reason": cancel_reason,
                    },
                )
            conn.commit()
        return AtomicCancellationResult(
            order=order_from_row(updated_row),
            ad_requires_expiration=False,
            capacity_released=capacity_released,
        )

    def _require_reportable_locked_order(
        self,
        order_row,
        *,
        remitter_user_id: str,
        payment_type: str,
        payment_amount: Decimal,
        now: datetime,
    ) -> None:  # type: ignore[no-untyped-def]
        if order_row is None or str(order_row["remitter_user_id"]) != remitter_user_id:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        if order_row["status"] != "waiting_payment":
            raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
        if order_row["paid_reported_at"] is not None:
            raise ApiError("ORDER_STATE_CONFLICT", status_code=409)
        if order_row["payment_report_deadline_at"] <= now:
            raise ApiError("ORDER_EXPIRED", status_code=409)
        if order_row["payment_method_snapshot"] != payment_type:
            raise ApiError("INVALID_PAYMENT_METHOD", status_code=400)
        if Decimal(str(order_row["amount_usd"])) != payment_amount:
            raise ApiError("PAYMENT_REPORT_AMOUNT_MISMATCH", status_code=409)

    def _insert_integrity_state_event(
        self,
        conn,
        *,
        order_id: str,
        from_status: str | None,
        to_status: str,
        event_type: str,
        actor_user_id: str | None,
        actor_role: str | None,
        reason: str | None,
        request_id: str,
        metadata_json: dict[str, Any],
    ) -> None:  # type: ignore[no-untyped-def]
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
                from_status,
                to_status,
                event_type,
                actor_user_id,
                actor_role,
                reason,
                request_id,
                jsonb(metadata_json),
            ),
        )

    def _insert_integrity_audit(
        self,
        conn,
        *,
        event_type: str,
        actor_user_id: str | None,
        actor_role: str | None,
        resource_id: str,
        request_id: str,
        metadata_json: dict[str, Any],
        resource_type: str = "order",
    ) -> None:  # type: ignore[no-untyped-def]
        conn.execute(
            """
            insert into audit_logs (
                actor_user_id, actor_role, event_type, resource_type,
                resource_id, request_id, metadata_json, created_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, now())
            """,
            (
                actor_user_id,
                actor_role,
                event_type,
                resource_type,
                resource_id,
                request_id,
                jsonb(metadata_json),
            ),
        )
