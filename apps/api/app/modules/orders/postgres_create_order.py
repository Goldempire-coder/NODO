from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.ads.row_mappers import ad_from_row
from app.modules.businesses.row_mappers import business_from_row, payment_method_from_row
from app.modules.orders.create_order_builder import bind_created_order_to_audit_events
from app.modules.orders.models import OrderRecord, new_public_order_code
from app.modules.orders.row_mappers import jsonb, order_from_row


BUSINESS_COLUMNS = (
    "id",
    "owner_user_id",
    "business_name",
    "rif",
    "address",
    "phone",
    "country",
    "verification_status",
    "trust_level",
    "risk_level",
    "min_order_amount_usd",
    "max_order_amount_usd",
    "daily_limit_usd",
    "active_order_limit",
    "is_accepting_orders",
    "rating_avg",
    "completed_orders_count",
    "disputes_count",
    "evasion_reports_count",
    "referral_code",
    "referral_credits_earned",
    "founder_status",
    "founder_started_at",
    "founder_expires_at",
    "created_at",
    "updated_at",
    "approved_at",
)

PAYMENT_METHOD_COLUMNS = (
    "id",
    "business_id",
    "method_type",
    "network",
    "account_value",
    "account_masked",
    "holder_name",
    "verified_status",
    "active",
    "created_at",
    "updated_at",
)


def _prefixed_row(row, prefix: str, columns: tuple[str, ...]) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    return {column: row[f"{prefix}{column}"] for column in columns}


class PostgresCreateOrderMixin:
    creates_audit_events_on_create_order = True
    skips_idempotency_precheck_on_create_order = True

    def get_order_create_start_context(self, *, remitter_user_id: str, idempotency_key: str, ad_id: str) -> dict[str, Any]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            existing = conn.execute(
                "select * from orders where remitter_user_id = %s and idempotency_key = %s limit 1",
                (remitter_user_id, idempotency_key),
            ).fetchone()
            if existing is not None:
                return {"existing_order": order_from_row(existing), "context": None}
            row = conn.execute(self._order_create_context_sql(), (ad_id,)).fetchone()
        return {"existing_order": None, "context": self._order_create_context_from_row(row)}

    def get_order_create_context(self, *, ad_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(self._order_create_context_sql(), (ad_id,)).fetchone()
        return self._order_create_context_from_row(row)

    def _order_create_context_from_row(self, row) -> dict[str, Any] | None:  # type: ignore[no-untyped-def]
        if row is None:
            return None
        return {
            "ad": ad_from_row(row),
            "business": business_from_row(_prefixed_row(row, "business_ctx_", BUSINESS_COLUMNS)),
            "payment": payment_method_from_row(_prefixed_row(row, "payment_ctx_", PAYMENT_METHOD_COLUMNS)),
            "active_order_count": int(row["active_order_count"]),
        }

    def _order_create_context_sql(self) -> str:
        return """
            select
                ads.*,
                businesses.id as business_ctx_id,
                businesses.owner_user_id as business_ctx_owner_user_id,
                businesses.business_name as business_ctx_business_name,
                businesses.rif as business_ctx_rif,
                businesses.address as business_ctx_address,
                businesses.phone as business_ctx_phone,
                businesses.country as business_ctx_country,
                businesses.verification_status as business_ctx_verification_status,
                businesses.trust_level as business_ctx_trust_level,
                businesses.risk_level as business_ctx_risk_level,
                businesses.min_order_amount_usd as business_ctx_min_order_amount_usd,
                businesses.max_order_amount_usd as business_ctx_max_order_amount_usd,
                businesses.daily_limit_usd as business_ctx_daily_limit_usd,
                businesses.active_order_limit as business_ctx_active_order_limit,
                businesses.is_accepting_orders as business_ctx_is_accepting_orders,
                businesses.rating_avg as business_ctx_rating_avg,
                businesses.completed_orders_count as business_ctx_completed_orders_count,
                businesses.disputes_count as business_ctx_disputes_count,
                businesses.evasion_reports_count as business_ctx_evasion_reports_count,
                businesses.referral_code as business_ctx_referral_code,
                businesses.referral_credits_earned as business_ctx_referral_credits_earned,
                businesses.founder_status as business_ctx_founder_status,
                businesses.founder_started_at as business_ctx_founder_started_at,
                businesses.founder_expires_at as business_ctx_founder_expires_at,
                businesses.created_at as business_ctx_created_at,
                businesses.updated_at as business_ctx_updated_at,
                businesses.approved_at as business_ctx_approved_at,
                business_payment_methods.id as payment_ctx_id,
                business_payment_methods.business_id as payment_ctx_business_id,
                business_payment_methods.method_type as payment_ctx_method_type,
                business_payment_methods.network as payment_ctx_network,
                business_payment_methods.account_value as payment_ctx_account_value,
                business_payment_methods.account_masked as payment_ctx_account_masked,
                business_payment_methods.holder_name as payment_ctx_holder_name,
                business_payment_methods.verified_status as payment_ctx_verified_status,
                business_payment_methods.active as payment_ctx_active,
                business_payment_methods.created_at as payment_ctx_created_at,
                business_payment_methods.updated_at as payment_ctx_updated_at,
                (
                    select count(*)
                    from orders
                    where orders.business_id = businesses.id
                      and orders.status in (
                          'waiting_payment',
                          'payment_reported',
                          'payment_rejected',
                          'payment_confirmed',
                          'delivered',
                          'disputed'
                      )
                ) as active_order_count
            from ads
            join businesses on businesses.id = ads.business_id
            join business_payment_methods on business_payment_methods.id = ads.payment_method_id
            where ads.id = %s
            limit 1
        """

    def create_order(self, **fields: Any) -> OrderRecord:
        initial_state_event = fields.pop("initial_state_event", None)
        audit_events = fields.pop("audit_events", None)
        capacity_reservation = fields.pop("capacity_reservation", None)
        with self._connect() as conn:  # type: ignore[attr-defined]
            if capacity_reservation is not None and self._capacity is not None:  # type: ignore[attr-defined]
                self._capacity.lock_order_create_capacity_in_transaction(  # type: ignore[attr-defined]
                    conn,
                    business_id=fields["business_id"],
                )
            self._move_ad_to_in_order_or_raise(conn, ad_id=fields["ad_id"])
            row = self._insert_order(conn, fields)
            if capacity_reservation is not None and self._capacity is not None:  # type: ignore[attr-defined]
                self._capacity.reserve_in_transaction(  # type: ignore[attr-defined]
                    conn,
                    order_id=str(row["id"]),
                    business_id=fields["business_id"],
                    amount_usd=capacity_reservation["amount_usd"],
                    reason=capacity_reservation["reason"],
                )
            if initial_state_event is not None:
                self._insert_initial_state_event(conn, order_id=row["id"], initial_state_event=initial_state_event)
            if audit_events is not None:
                self._insert_create_order_audit_events(conn, order_id=str(row["id"]), audit_events=audit_events)
            conn.commit()
        return order_from_row(row)

    def _move_ad_to_in_order_or_raise(self, conn, *, ad_id: str) -> None:  # type: ignore[no-untyped-def]
        moved_ad = conn.execute(
            "update ads set status = 'in_order', updated_at = now() where id = %s and status = 'active' returning id",
            (ad_id,),
        ).fetchone()
        if moved_ad is None:
            conn.rollback()
            raise ApiError("AD_NOT_AVAILABLE", status_code=409)

    def _insert_order(self, conn, fields: dict[str, Any]):  # type: ignore[no-untyped-def]
        return conn.execute(
            """
            insert into orders (
                public_order_code, ad_id, business_id, remitter_user_id, status, idempotency_key,
                amount_usd, rate_snapshot, amount_bs_calculated, business_name_snapshot,
                payment_method_snapshot, delivery_method_snapshot, min_amount_snapshot, max_amount_snapshot,
                payment_instructions_snapshot, receiver_data_json, payment_report_deadline_at,
                extension_used, expires_at, created_at, updated_at
            )
            values (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, %s, now(), now()
            )
            returning *
            """,
            (
                new_public_order_code(),
                fields["ad_id"],
                fields["business_id"],
                fields["remitter_user_id"],
                fields["status"],
                fields["idempotency_key"],
                fields["amount_usd"],
                fields["rate_snapshot"],
                fields["amount_bs_calculated"],
                fields["business_name_snapshot"],
                fields["payment_method_snapshot"],
                fields["delivery_method_snapshot"],
                fields["min_amount_snapshot"],
                fields["max_amount_snapshot"],
                jsonb(fields["payment_instructions_snapshot"]),
                jsonb(fields["receiver_data_json"]),
                fields["payment_report_deadline_at"],
                fields["expires_at"],
            ),
        ).fetchone()

    def _insert_initial_state_event(self, conn, *, order_id: str, initial_state_event: dict[str, Any]) -> None:  # type: ignore[no-untyped-def]
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
                initial_state_event["from_status"],
                initial_state_event["to_status"],
                initial_state_event["event_type"],
                initial_state_event["actor_user_id"],
                initial_state_event["actor_role"],
                initial_state_event["reason"],
                initial_state_event["request_id"],
                jsonb(initial_state_event["metadata_json"]),
            ),
        )

    def _insert_create_order_audit_events(self, conn, *, order_id: str, audit_events: list[dict[str, Any]]) -> None:  # type: ignore[no-untyped-def]
        bound_events = bind_created_order_to_audit_events(audit_events, order_id=order_id)
        if not bound_events:
            return
        values_sql = ", ".join(["(%s, %s, %s, %s, %s, %s, %s, now())"] * len(bound_events))
        params: list[object] = []
        for event in bound_events:
            params.extend(
                [
                    event.get("actor_user_id"),
                    event.get("actor_role"),
                    event["event_type"],
                    event["resource_type"],
                    event.get("resource_id"),
                    event["request_id"],
                    jsonb(event.get("metadata_json")),
                ]
            )
        conn.execute(
            f"""
            insert into audit_logs (
                actor_user_id, actor_role, event_type, resource_type, resource_id,
                request_id, metadata_json, created_at
            )
            values {values_sql}
            """,
            params,
        )
