from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from threading import RLock

from app.core.errors import ApiError
from app.modules.business_capacity.models import (
    DAILY_CAPACITY_ENTRY_LIMIT,
    ZERO_USD,
    BusinessCapacityRecord,
    BusinessCapacityReservationRecord,
    BusinessCapacitySnapshot,
    as_utc,
    money,
    new_id,
    utc_day_window,
    utc_now,
)
from app.modules.businesses.models import BusinessRecord


class InMemoryBusinessCapacityRepository:
    def __init__(self, *, default_declared_capacity_usd: Decimal = ZERO_USD) -> None:
        self._lock = RLock()
        self._default_declared_capacity_usd = money(default_declared_capacity_usd)
        self.capacities: dict[str, BusinessCapacityRecord] = {}
        self.reservations: dict[str, BusinessCapacityReservationRecord] = {}

    def _capacity(self, business_id: str) -> BusinessCapacityRecord:
        capacity = self.capacities.get(business_id)
        if capacity is None:
            capacity = BusinessCapacityRecord(
                business_id=business_id,
                declared_available_capacity_usd=self._default_declared_capacity_usd,
            )
            self.capacities[business_id] = capacity
        return capacity

    def _reserved(self, business_id: str) -> Decimal:
        return money(
            sum(
                (
                    reservation.amount_usd
                    for reservation in self.reservations.values()
                    if reservation.business_id == business_id and reservation.status == "reserved"
                ),
                ZERO_USD,
            )
        )

    def _daily_consumed(
        self,
        business_id: str,
        *,
        starts_at: datetime,
        ends_at: datetime,
    ) -> Decimal:
        return money(
            sum(
                (
                    reservation.amount_usd
                    for reservation in self.reservations.values()
                    if reservation.business_id == business_id
                    and reservation.status == "consumed"
                    and reservation.consumed_at is not None
                    and starts_at <= as_utc(reservation.consumed_at) < ends_at
                ),
                ZERO_USD,
            )
        )

    def get_snapshot(
        self,
        *,
        business: BusinessRecord,
        include_reservations: bool = False,
        now: datetime | None = None,
    ) -> BusinessCapacitySnapshot:
        with self._lock:
            capacity = self._capacity(business.id)
            current = now or utc_now()
            daily_starts_at, daily_ends_at = utc_day_window(current)
            reserved = self._reserved(business.id)
            daily_consumed = self._daily_consumed(
                business.id,
                starts_at=daily_starts_at,
                ends_at=daily_ends_at,
            )
            effective = max(ZERO_USD, money(capacity.declared_available_capacity_usd - reserved))
            daily_remaining = max(
                ZERO_USD,
                money(business.daily_limit_usd - reserved - daily_consumed),
            )
            reservations: tuple[BusinessCapacityReservationRecord, ...] = ()
            daily_orders_truncated = False
            if include_reservations:
                explanatory_entries = sorted(
                    (
                        reservation
                        for reservation in self.reservations.values()
                        if reservation.business_id == business.id
                        and (
                            reservation.status == "reserved"
                            or (
                                reservation.status == "consumed"
                                and reservation.consumed_at is not None
                                and daily_starts_at
                                <= as_utc(reservation.consumed_at)
                                < daily_ends_at
                            )
                        )
                    ),
                    key=lambda reservation: (
                        0 if reservation.status == "reserved" else 1,
                        reservation.created_at,
                        reservation.id,
                    ),
                )
                reservations = tuple(
                    explanatory_entries[:DAILY_CAPACITY_ENTRY_LIMIT]
                )
                daily_orders_truncated = (
                    len(explanatory_entries) > DAILY_CAPACITY_ENTRY_LIMIT
                )
            return BusinessCapacitySnapshot(
                business_id=business.id,
                declared_available_capacity_usd=capacity.declared_available_capacity_usd,
                reserved_capacity_usd=reserved,
                effective_available_capacity_usd=effective,
                daily_reserved_usd=reserved,
                daily_consumed_usd=daily_consumed,
                daily_remaining_usd=daily_remaining,
                daily_window_starts_at=daily_starts_at,
                daily_window_ends_at=daily_ends_at,
                updated_by_user_id=capacity.updated_by_user_id,
                updated_at=capacity.updated_at,
                reservations=reservations,
                daily_orders_truncated=daily_orders_truncated,
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
        with self._lock:
            reserved = self._reserved(business_id)
            if amount < reserved:
                raise ApiError("BUSINESS_CAPACITY_BELOW_RESERVED", status_code=409)
            capacity = self._capacity(business_id)
            capacity.declared_available_capacity_usd = amount
            capacity.updated_by_user_id = actor_user_id
            capacity.updated_at = utc_now()
            return capacity

    def update_capacity_and_availability(
        self,
        *,
        business: BusinessRecord,
        amount_usd: Decimal,
        accepting_orders: bool,
        actor_user_id: str | None,
    ) -> BusinessCapacitySnapshot:
        with self._lock:
            self.set_declared_capacity(
                business_id=business.id,
                amount_usd=amount_usd,
                actor_user_id=actor_user_id,
            )
            business.is_accepting_orders = accepting_orders
            business.updated_at = utc_now()
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
        amount = money(amount_usd)
        with self._lock:
            existing = self.reservations.get(order_id)
            if existing is not None:
                if existing.business_id == business.id and existing.amount_usd == amount:
                    return existing
                raise ApiError("BUSINESS_CAPACITY_RESERVATION_CONFLICT", status_code=409)
            snapshot = self.get_snapshot(business=business)
            if (
                amount < business.min_order_amount_usd
                or amount > business.max_order_amount_usd
                or amount > snapshot.effective_available_capacity_usd
            ):
                raise ApiError("BUSINESS_CAPACITY_INSUFFICIENT", status_code=409)
            if amount > snapshot.daily_remaining_usd:
                raise ApiError("BUSINESS_DAILY_LIMIT_EXCEEDED", status_code=409)
            now = utc_now()
            reservation = BusinessCapacityReservationRecord(
                id=new_id(),
                order_id=order_id,
                business_id=business.id,
                amount_usd=amount,
                status="reserved",
                reason=reason,
                created_at=now,
                updated_at=now,
            )
            self.reservations[order_id] = reservation
            return reservation

    def get_reservation(self, order_id: str) -> BusinessCapacityReservationRecord | None:
        return self.reservations.get(order_id)

    def release(self, *, order_id: str, reason: str) -> bool:
        with self._lock:
            reservation = self.reservations.get(order_id)
            if reservation is None or reservation.status != "reserved":
                return False
            now = utc_now()
            reservation.status = "released"
            reservation.reason = reason
            reservation.released_at = now
            reservation.updated_at = now
            return True

    def consume(self, *, order_id: str, reason: str) -> bool:
        with self._lock:
            reservation = self.reservations.get(order_id)
            if reservation is None or reservation.status != "reserved":
                return False
            capacity = self._capacity(reservation.business_id)
            if capacity.declared_available_capacity_usd < reservation.amount_usd:
                raise ApiError("BUSINESS_CAPACITY_RESERVATION_CONFLICT", status_code=409)
            now = utc_now()
            capacity.declared_available_capacity_usd = money(
                capacity.declared_available_capacity_usd - reservation.amount_usd
            )
            capacity.updated_at = now
            reservation.status = "consumed"
            reservation.reason = reason
            reservation.consumed_at = now
            reservation.updated_at = now
            return True
