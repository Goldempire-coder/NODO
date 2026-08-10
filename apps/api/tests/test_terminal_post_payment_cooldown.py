from datetime import datetime, timedelta, timezone

import pytest

from app.modules.orders.terminal_publication_cooldown import (
    terminal_publication_cooldown_candidate,
    terminal_transition_starts_publication_cooldown,
)


@pytest.mark.parametrize("target_status", ["completed", "cancelled"])
def test_paid_reported_terminal_transition_starts_publication_cooldown(
    target_status: str,
) -> None:
    assert terminal_transition_starts_publication_cooldown(
        previous_status="disputed",
        target_status=target_status,
        paid_reported_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
    )


@pytest.mark.parametrize(
    ("previous_status", "target_status", "paid_reported_at"),
    [
        ("waiting_payment", "cancelled", None),
        ("delivered", "disputed", datetime(2026, 8, 9, tzinfo=timezone.utc)),
        ("completed", "completed", datetime(2026, 8, 9, tzinfo=timezone.utc)),
        ("cancelled", "cancelled", datetime(2026, 8, 9, tzinfo=timezone.utc)),
    ],
)
def test_non_qualifying_transition_does_not_restart_publication_cooldown(
    previous_status: str,
    target_status: str,
    paid_reported_at: datetime | None,
) -> None:
    assert not terminal_transition_starts_publication_cooldown(
        previous_status=previous_status,
        target_status=target_status,
        paid_reported_at=paid_reported_at,
    )


def test_publication_cooldown_candidate_is_exactly_fifteen_minutes() -> None:
    transition_at = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)

    assert terminal_publication_cooldown_candidate(transition_at) == (
        transition_at + timedelta(minutes=15)
    )
