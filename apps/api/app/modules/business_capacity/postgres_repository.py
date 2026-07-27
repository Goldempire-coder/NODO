from __future__ import annotations

from decimal import Decimal

from app.core.errors import ApiError
from app.modules.business_capacity.models import (
    ZERO_USD,
    BusinessCapacityRecord,
    BusinessCapacityReservationRecord,
    BusinessCapacitySnapshot,
    money,
)
from app.modules.businesses.models import BusinessRecord
from app.shared.db.connection import pooled_connect


class PostgresBusinessCapacityRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def _ensure_capacity_row(self, conn, *, business_id: str) -> None:  # type: ignore[no-untyped-def]
        conn.execute(
            """
            insert into business_capacity (
                business_id, declared_available_capacity_usd, created_at, updated_at
            )
            values (%s, 0.00, now(), now())
            on conflict (business_id) do nothing
            """,
            (business_id,),
        )

    def get_snapshot(
        self,
        *,
        business: BusinessRecord,
        include_reservations: bool = False,
        now=None,  # type: ignore[no-untyped-def]
    ) -> BusinessCapacitySnapshot:
        del now
        with self._connect() as conn:
            row = conn.execute(
                """
                select
                    coalesce(capacity.declared_available_capacity_usd, 0.00) as declared,
                    capacity.updated_by_user_id,
                    capacity.updated_at,
                    coalesce(sum(reservation.amount_usd)
                        filter (where reservation.status = 'reserved'), 0.00) as reserved,
                    coalesce(sum(reservation.amount_usd)
                        filter (
                            where reservation.created_at >=
                                date_trunc('day', now() at time zone 'UTC') at time zone 'UTC'
                              and reservation.status in ('reserved', 'consumed')
                        ), 0.00) as daily_reserved
                from businesses
                left join business_capacity capacity on capacity.business_id = businesses.id
                left join business_capacity_reservations reservation
                    on reservation.business_id = businesses.id
                where businesses.id = %s
                group by capacity.declared_available_capacity_usd,
                         capacity.updated_by_user_id,
                         capacity.updated_at
                """,
                (business.id,),
            ).fetchone()
            reservation_rows = []
            if include_reservations:
                reservation_rows = conn.execute(
                    """
                    select *
                    from business_capacity_reservations
                    where business_id = %s and status = 'reserved'
                    order by created_at asc, id asc
                    """,
                    (business.id,),
                ).fetchall()
        if row is None:
            raise ApiError("BUSINESS_NOT_FOUND", status_code=404)
        declared = money(Decimal(str(row["declared"])))
        reserved = money(Decimal(str(row["reserved"])))
        daily_reserved = money(Decimal(str(row["daily_reserved"])))
        return BusinessCapacitySnapshot(
            business_id=business.id,
            declared_available_capacity_usd=declared,
            reserved_capacity_usd=reserved,
            effective_available_capacity_usd=max(ZERO_USD, money(declared - reserved)),
            daily_reserved_capacity_usd=daily_reserved,
            daily_remaining_usd=max(ZERO_USD, money(business.daily_limit_usd - daily_reserved)),
            updated_by_user_id=str(row["updated_by_user_id"]) if row["updated_by_user_id"] else None,
            updated_at=row["updated_at"],
            reservations=tuple(self._reservation_from_row(item) for item in reservation_rows),
        )

    def set_declared_capacity(
        self,
        *,
        business_id: str,
        amount_usd: Decimal,
        actor_user_id: str | None,
    ) -> BusinessCapacityRecord:
        amount = money(amount_usd)
        if amount < ZERO_USD:
            raise ApiError("CAPACITY_AMOUNT_INVALID", status_code=400)
        with self._connect() as conn:
            self._ensure_capacity_row(conn, business_id=business_id)
            conn.execute(
                "select business_id from business_capacity where business_id = %s for update",
                (business_id,),
            ).fetchone()
            reserved_row = conn.execute(
                """
                select coalesce(sum(amount_usd), 0.00) as reserved
                from business_capacity_reservations
                where business_id = %s and status = 'reserved'
                """,
                (business_id,),
            ).fetchone()
            if amount < Decimal(str(reserved_row["reserved"])):
                conn.rollback()
                raise ApiError("BUSINESS_CAPACITY_BELOW_RESERVED", status_code=409)
            row = conn.execute(
                """
                update business_capacity
                set declared_available_capacity_usd = %s,
                    updated_by_user_id = %s,
                    updated_at = now()
                where business_id = %s
                returning *
                """,
                (amount, actor_user_id, business_id),
            ).fetchone()
            conn.commit()
        return self._capacity_from_row(row)

    def update_capacity_and_availability(
        self,
        *,
        business: BusinessRecord,
        amount_usd: Decimal,
        accepting_orders: bool,
        actor_user_id: str | None,
    ) -> BusinessCapacitySnapshot:
        amount = money(amount_usd)
        if amount < ZERO_USD:
            raise ApiError("CAPACITY_AMOUNT_INVALID", status_code=400)
        with self._connect() as conn:
            self._ensure_capacity_row(conn, business_id=business.id)
            conn.execute(
                "select business_id from business_capacity where business_id = %s for update",
                (business.id,),
            ).fetchone()
            reserved_row = conn.execute(
                """
                select coalesce(sum(amount_usd), 0.00) as reserved
                from business_capacity_reservations
                where business_id = %s and status = 'reserved'
                """,
                (business.id,),
            ).fetchone()
            if amount < Decimal(str(reserved_row["reserved"])):
                conn.rollback()
                raise ApiError("BUSINESS_CAPACITY_BELOW_RESERVED", status_code=409)
            conn.execute(
                """
                update business_capacity
                set declared_available_capacity_usd = %s,
                    updated_by_user_id = %s,
                    updated_at = now()
                where business_id = %s
                """,
                (amount, actor_user_id, business.id),
            )
            conn.execute(
                "update businesses set is_accepting_orders = %s, updated_at = now() where id = %s",
                (accepting_orders, business.id),
            )
            conn.commit()
        business.is_accepting_orders = accepting_orders
        return self.get_snapshot(business=business)

    def can_cover(self, *, business: BusinessRecord, amount_usd: Decimal) -> bool:
        if (
            not business.is_accepting_orders
            or business.verification_status != "approved"
            or business.risk_level in {"restricted", "high_risk"}
        ):
            return False
        snapshot = self.get_snapshot(business=business)
        amount = money(amount_usd)
        return (
            amount >= business.min_order_amount_usd
            and amount <= business.max_order_amount_usd
            and amount <= snapshot.effective_available_capacity_usd
            and amount <= snapshot.daily_remaining_usd
        )

    def reserve(
        self,
        *,
        order_id: str,
        business: BusinessRecord,
        amount_usd: Decimal,
        reason: str,
    ) -> BusinessCapacityReservationRecord:
        with self._connect() as conn:
            reservation = self.reserve_in_transaction(
                conn,
                order_id=order_id,
                business_id=business.id,
                amount_usd=amount_usd,
                reason=reason,
            )
            conn.commit()
        return reservation

    def reserve_in_transaction(
        self,
        conn,
        *,
        order_id: str,
        business_id: str,
        amount_usd: Decimal,
        reason: str,
    ) -> BusinessCapacityReservationRecord:  # type: ignore[no-untyped-def]
        amount = money(amount_usd)
        existing = conn.execute(
            "select * from business_capacity_reservations where order_id = %s",
            (order_id,),
        ).fetchone()
        if existing is not None:
            if str(existing["business_id"]) == business_id and money(Decimal(str(existing["amount_usd"]))) == amount:
                return self._reservation_from_row(existing)
            raise ApiError("BUSINESS_CAPACITY_RESERVATION_CONFLICT", status_code=409)
        self._ensure_capacity_row(conn, business_id=business_id)
        capacity_row = conn.execute(
            """
            select
                capacity.declared_available_capacity_usd as declared,
                businesses.min_order_amount_usd,
                businesses.max_order_amount_usd,
                businesses.daily_limit_usd,
                businesses.verification_status,
                businesses.risk_level,
                businesses.is_accepting_orders
            from business_capacity capacity
            join businesses on businesses.id = capacity.business_id
            where capacity.business_id = %s
            for update of capacity, businesses
            """,
            (business_id,),
        ).fetchone()
        if capacity_row is None:
            raise ApiError("BUSINESS_NOT_FOUND", status_code=404)
        if (
            capacity_row["verification_status"] != "approved"
            or capacity_row["risk_level"] in {"restricted", "high_risk"}
            or not capacity_row["is_accepting_orders"]
        ):
            raise ApiError("BUSINESS_OFFLINE", status_code=409)
        totals = conn.execute(
            """
            select
                coalesce(sum(amount_usd) filter (where status = 'reserved'), 0.00) as reserved,
                coalesce(sum(amount_usd) filter (
                    where created_at >= date_trunc('day', now() at time zone 'UTC') at time zone 'UTC'
                      and status in ('reserved', 'consumed')
                ), 0.00) as daily_reserved
            from business_capacity_reservations
            where business_id = %s
            """,
            (business_id,),
        ).fetchone()
        declared = Decimal(str(capacity_row["declared"]))
        reserved = Decimal(str(totals["reserved"]))
        daily_reserved = Decimal(str(totals["daily_reserved"]))
        if (
            amount < Decimal(str(capacity_row["min_order_amount_usd"]))
            or amount > Decimal(str(capacity_row["max_order_amount_usd"]))
            or amount > declared - reserved
            or amount > Decimal(str(capacity_row["daily_limit_usd"])) - daily_reserved
        ):
            raise ApiError("BUSINESS_CAPACITY_INSUFFICIENT", status_code=409)
        row = conn.execute(
            """
            insert into business_capacity_reservations (
                order_id, business_id, amount_usd, status, reason, created_at, updated_at
            )
            values (%s, %s, %s, 'reserved', %s, now(), now())
            returning *
            """,
            (order_id, business_id, amount, reason),
        ).fetchone()
        return self._reservation_from_row(row)

    def get_reservation(self, order_id: str) -> BusinessCapacityReservationRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "select * from business_capacity_reservations where order_id = %s",
                (order_id,),
            ).fetchone()
        return self._reservation_from_row(row) if row else None

    def release(self, *, order_id: str, reason: str) -> bool:
        with self._connect() as conn:
            changed = self.transition_in_transaction(
                conn,
                order_id=order_id,
                target_status="released",
                reason=reason,
            )
            conn.commit()
        return changed

    def consume(self, *, order_id: str, reason: str) -> bool:
        with self._connect() as conn:
            changed = self.transition_in_transaction(
                conn,
                order_id=order_id,
                target_status="consumed",
                reason=reason,
            )
            conn.commit()
        return changed

    def transition_in_transaction(
        self,
        conn,
        *,
        order_id: str,
        target_status: str,
        reason: str,
    ) -> bool:  # type: ignore[no-untyped-def]
        row = conn.execute(
            "select * from business_capacity_reservations where order_id = %s for update",
            (order_id,),
        ).fetchone()
        if row is None or row["status"] != "reserved":
            return False
        if target_status == "consumed":
            self._ensure_capacity_row(conn, business_id=str(row["business_id"]))
            capacity = conn.execute(
                """
                select declared_available_capacity_usd
                from business_capacity
                where business_id = %s
                for update
                """,
                (row["business_id"],),
            ).fetchone()
            amount = Decimal(str(row["amount_usd"]))
            if Decimal(str(capacity["declared_available_capacity_usd"])) < amount:
                raise ApiError("BUSINESS_CAPACITY_RESERVATION_CONFLICT", status_code=409)
            conn.execute(
                """
                update business_capacity
                set declared_available_capacity_usd = declared_available_capacity_usd - %s,
                    updated_at = now()
                where business_id = %s
                """,
                (amount, row["business_id"]),
            )
            terminal_column = "consumed_at"
        elif target_status == "released":
            terminal_column = "released_at"
        else:
            raise ValueError("unsupported capacity reservation transition")
        conn.execute(
            f"""
            update business_capacity_reservations
            set status = %s, reason = %s, {terminal_column} = now(), updated_at = now()
            where order_id = %s and status = 'reserved'
            """,
            (target_status, reason, order_id),
        )
        return True

    def _capacity_from_row(self, row) -> BusinessCapacityRecord:  # type: ignore[no-untyped-def]
        return BusinessCapacityRecord(
            business_id=str(row["business_id"]),
            declared_available_capacity_usd=money(Decimal(str(row["declared_available_capacity_usd"]))),
            updated_by_user_id=str(row["updated_by_user_id"]) if row["updated_by_user_id"] else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _reservation_from_row(self, row) -> BusinessCapacityReservationRecord:  # type: ignore[no-untyped-def]
        return BusinessCapacityReservationRecord(
            id=str(row["id"]),
            order_id=str(row["order_id"]),
            business_id=str(row["business_id"]),
            amount_usd=money(Decimal(str(row["amount_usd"]))),
            status=row["status"],
            reason=row["reason"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            released_at=row["released_at"],
            consumed_at=row["consumed_at"],
        )
