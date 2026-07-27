from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4


ZERO_USD = Decimal("0.00")
DAILY_CAPACITY_ENTRY_LIMIT = 50


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def utc_day_window(value: datetime | None = None) -> tuple[datetime, datetime]:
    current = as_utc(value or utc_now())
    starts_at = current.replace(hour=0, minute=0, second=0, microsecond=0)
    return starts_at, starts_at + timedelta(days=1)


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class BusinessCapacityRecord:
    business_id: str
    declared_available_capacity_usd: Decimal = ZERO_USD
    updated_by_user_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class BusinessCapacityReservationRecord:
    id: str
    order_id: str
    business_id: str
    amount_usd: Decimal
    status: str
    reason: str
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    released_at: datetime | None = None
    consumed_at: datetime | None = None


@dataclass(frozen=True)
class BusinessCapacitySnapshot:
    business_id: str
    declared_available_capacity_usd: Decimal
    reserved_capacity_usd: Decimal
    effective_available_capacity_usd: Decimal
    daily_reserved_usd: Decimal
    daily_consumed_usd: Decimal
    daily_remaining_usd: Decimal
    daily_window_starts_at: datetime
    daily_window_ends_at: datetime
    updated_by_user_id: str | None
    updated_at: datetime | None
    reservations: tuple[BusinessCapacityReservationRecord, ...] = ()
    daily_orders_truncated: bool = False


def new_id() -> str:
    return str(uuid4())
