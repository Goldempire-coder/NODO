from __future__ import annotations

from datetime import datetime, timedelta, timezone


TERMINAL_ORDER_STATUSES = frozenset({"completed", "cancelled"})
TERMINAL_POST_PAYMENT_COOLDOWN = timedelta(minutes=15)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def terminal_transition_starts_publication_cooldown(
    *,
    previous_status: str,
    target_status: str,
    paid_reported_at: datetime | None,
) -> bool:
    return (
        paid_reported_at is not None
        and previous_status not in TERMINAL_ORDER_STATUSES
        and target_status in TERMINAL_ORDER_STATUSES
    )


def terminal_publication_cooldown_candidate(transition_at: datetime) -> datetime:
    return _as_utc(transition_at) + TERMINAL_POST_PAYMENT_COOLDOWN
