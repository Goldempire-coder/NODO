from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from app.core.errors import ApiError
from app.modules.business_capacity.postgres_repository import (
    PostgresBusinessCapacityRepository,
)
from app.modules.orders.postgres_repository import PostgresOrderRepository


ROOT = Path(__file__).resolve().parents[3]
POSTGRES_OPT_IN = "NODO_RUN_TERMINAL_COOLDOWN_POSTGRES"
POSTGRES_URL_ENV = "NODO_TERMINAL_COOLDOWN_POSTGRES_URL"


def _require_disposable_local_database() -> str:
    if os.environ.get(POSTGRES_OPT_IN) != "1":
        pytest.skip(f"set {POSTGRES_OPT_IN}=1 for disposable local PostgreSQL validation")
    database_url = os.environ.get(POSTGRES_URL_ENV, "")
    parsed = urlparse(database_url)
    database_name = parsed.path.removeprefix("/").lower()
    if parsed.hostname not in {"127.0.0.1", "localhost"} or not database_name.startswith(
        "nodo_c3_"
    ):
        raise RuntimeError(
            "terminal cooldown PostgreSQL tests require a disposable localhost nodo_c3_* database"
        )
    return database_url


@pytest.fixture(scope="module")
def cooldown_database_url() -> str:
    database_url = _require_disposable_local_database()
    with psycopg.connect(database_url) as conn:
        current_database = conn.execute("select current_database()").fetchone()[0]
        pause_column = conn.execute(
            """
            select 1
            from information_schema.columns
            where table_schema = 'public'
              and table_name = 'businesses'
              and column_name = 'ad_publication_paused_until'
            """
        ).fetchone()
    assert current_database.lower().startswith("nodo_c3_")
    assert pause_column is not None
    return database_url


def _seed_business_orders(
    database_url: str,
    *,
    order_count: int,
    paid_reported: bool,
) -> dict[str, object]:
    owner_id = str(uuid4())
    business_id = str(uuid4())
    payment_method_id = str(uuid4())
    ad_id = str(uuid4())
    remitter_ids = [str(uuid4()) for _ in range(order_count)]
    order_ids = [str(uuid4()) for _ in range(order_count)]
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            cursor.executemany(
                "insert into users (id, role, status) values (%s, %s, 'active')",
                [(owner_id, "business_owner"), *[(item, "remitter") for item in remitter_ids]],
            )
        conn.execute(
            """
            insert into businesses (
                id, owner_user_id, business_name, verification_status, approved_at
            )
            values (%s, %s, 'C3 Local Business', 'approved', now())
            """,
            (business_id, owner_id),
        )
        conn.execute(
            """
            insert into business_payment_methods (
                id, business_id, method_type, network, account_value, account_masked,
                holder_name, verified_status, active
            )
            values (%s, %s, 'zelle', null, 'local@example.test', 'l***@example.test',
                    'Local Holder', 'approved', true)
            """,
            (payment_method_id, business_id),
        )
        conn.execute(
            """
            insert into ads (
                id, business_id, payment_method_id, payment_method, delivery_method,
                rate_bs_per_usd, amount_min_usd, amount_max_usd, required_credits,
                status, activated_at, expires_at
            )
            values (%s, %s, %s, 'zelle', 'pago_movil_ve', 40, 20, 100, 1,
                    'in_order', now(), now() + interval '7 days')
            """,
            (ad_id, business_id, payment_method_id),
        )
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                insert into orders (
                    id, public_order_code, ad_id, business_id, remitter_user_id,
                    status, amount_usd, rate_snapshot, amount_bs_calculated,
                    business_name_snapshot, payment_method_snapshot,
                    delivery_method_snapshot, min_amount_snapshot, max_amount_snapshot,
                    payment_instructions_snapshot, receiver_data_json,
                    payment_report_deadline_at, expires_at, paid_reported_at,
                    payment_confirmed_at, delivered_at
                )
                values (
                    %s, %s, %s, %s, %s, 'delivered', 50, 40, 2000,
                    'C3 Local Business', 'zelle', 'pago_movil_ve', 20, 100,
                    '{}'::jsonb, '{}'::jsonb, now() + interval '30 minutes',
                    now() + interval '30 minutes',
                    case when %s then now() - interval '10 minutes' else null end,
                    now() - interval '5 minutes', now() - interval '1 minute'
                )
                """,
                [
                    (
                        order_id,
                        f"NODO-{uuid4().hex[:8].upper()}",
                        ad_id,
                        business_id,
                        remitter_id,
                        paid_reported,
                    )
                    for order_id, remitter_id in zip(order_ids, remitter_ids, strict=True)
                ],
            )
        conn.commit()
    return {
        "owner_id": owner_id,
        "business_id": business_id,
        "payment_method_id": payment_method_id,
        "ad_id": ad_id,
        "remitter_ids": remitter_ids,
        "order_ids": order_ids,
    }


def _cleanup(database_url: str, ids: dict[str, object]) -> None:
    with psycopg.connect(database_url) as conn:
        conn.execute("delete from order_receiver_details where order_id = any(%s)", (ids["order_ids"],))
        conn.execute("delete from dispute_events where order_id = any(%s)", (ids["order_ids"],))
        conn.execute("delete from disputes where order_id = any(%s)", (ids["order_ids"],))
        conn.execute("delete from order_state_events where order_id = any(%s)", (ids["order_ids"],))
        # audit_logs are intentionally append-only; the disposable database is
        # removed after this test module instead of weakening that invariant.
        conn.execute(
            "delete from business_capacity_reservations where order_id = any(%s)",
            (ids["order_ids"],),
        )
        conn.execute("delete from orders where id = any(%s)", (ids["order_ids"],))
        conn.execute("delete from ads where id = %s", (ids["ad_id"],))
        conn.execute(
            "delete from business_payment_methods where id = %s",
            (ids["payment_method_id"],),
        )
        conn.execute("delete from business_capacity where business_id = %s", (ids["business_id"],))
        conn.execute("delete from businesses where id = %s", (ids["business_id"],))
        # Audit actors must remain referentially valid for the lifetime of this
        # disposable database; the container teardown removes them afterward.
        conn.commit()


def test_postgres_manual_completion_applies_cooldown_with_capacity_transition(
    cooldown_database_url: str,
) -> None:
    ids = _seed_business_orders(cooldown_database_url, order_count=1, paid_reported=True)
    order_id = ids["order_ids"][0]
    remitter_id = ids["remitter_ids"][0]
    with psycopg.connect(cooldown_database_url) as conn:
        conn.execute(
            """
            insert into business_capacity (
                business_id, declared_available_capacity_usd, created_at, updated_at
            )
            values (%s, 100, now(), now())
            """,
            (ids["business_id"],),
        )
        conn.execute(
            """
            insert into business_capacity_reservations (
                order_id, business_id, amount_usd, status, reason, created_at, updated_at
            )
            values (%s, %s, 50, 'reserved', 'order_created', now(), now())
            """,
            (order_id, ids["business_id"]),
        )
        conn.execute(
            """
            insert into order_receiver_details (
                order_id, bank_code, phone, document, holder, payload_hash,
                shared_by_user_id, shared_at
            )
            values (%s, '0102', '0414 1234567', '12345678', 'Local Receiver',
                    %s, %s, now())
            """,
            (order_id, "0" * 64, remitter_id),
        )
        started_at = conn.execute("select clock_timestamp()").fetchone()[0]
        conn.commit()

    capacity = PostgresBusinessCapacityRepository(cooldown_database_url)
    repository = PostgresOrderRepository(
        cooldown_database_url,
        capacity_repository=capacity,
    )
    completed = repository.confirm_received_atomically(
        order_id=order_id,
        remitter_user_id=remitter_id,
        completed_at=datetime.now(timezone.utc),
        request_id="c3_postgres_manual_completion",
        event_metadata={"completion_reason": "manual_confirmed"},
        audit_metadata={"completion_reason": "manual_confirmed"},
    )
    with psycopg.connect(cooldown_database_url, row_factory=dict_row) as conn:
        state = conn.execute(
            """
            select businesses.ad_publication_paused_until,
                   reservations.status as reservation_status,
                   ads.status as ad_status
            from businesses
            join business_capacity_reservations reservations
              on reservations.business_id = businesses.id
            join ads on ads.business_id = businesses.id
            where businesses.id = %s and reservations.order_id = %s
            """,
            (ids["business_id"], order_id),
        ).fetchone()
    pause_after_completion = state["ad_publication_paused_until"]

    with pytest.raises(ApiError) as replay_error:
        repository.confirm_received_atomically(
            order_id=order_id,
            remitter_user_id=remitter_id,
            completed_at=datetime.now(timezone.utc),
            request_id="c3_postgres_manual_completion_replay",
            event_metadata={"completion_reason": "manual_confirmed"},
            audit_metadata={"completion_reason": "manual_confirmed"},
        )
    with psycopg.connect(cooldown_database_url, row_factory=dict_row) as conn:
        pause_after_replay = conn.execute(
            "select ad_publication_paused_until from businesses where id = %s",
            (ids["business_id"],),
        ).fetchone()["ad_publication_paused_until"]

    assert completed.status == "completed"
    assert state["reservation_status"] == "consumed"
    assert state["ad_status"] == "in_order"
    assert pause_after_completion >= started_at + timedelta(minutes=15)
    assert pause_after_replay == pause_after_completion
    assert replay_error.value.code == "ORDER_RECEIPT_CONFIRMATION_NOT_ALLOWED"
    _cleanup(cooldown_database_url, ids)


def test_postgres_terminal_transitions_apply_cooldown_once_and_preserve_ad(
    cooldown_database_url: str,
) -> None:
    ids = _seed_business_orders(cooldown_database_url, order_count=2, paid_reported=True)
    repository = PostgresOrderRepository(cooldown_database_url)
    completed_order = repository.get_by_id(ids["order_ids"][0])
    cancelled_order = repository.get_by_id(ids["order_ids"][1])
    assert completed_order is not None and cancelled_order is not None

    repository.update_order(
        completed_order,
        status="completed",
        completion_reason="auto_completed_after_24h",
        completed_at=completed_order.updated_at,
    )
    with psycopg.connect(cooldown_database_url, row_factory=dict_row) as conn:
        pause_after_first = conn.execute(
            "select ad_publication_paused_until from businesses where id = %s",
            (ids["business_id"],),
        ).fetchone()["ad_publication_paused_until"]
    repository.update_order(
        repository.get_by_id(completed_order.id),
        status="completed",
        completion_reason="auto_completed_after_24h",
        completed_at=completed_order.updated_at,
    )
    repository.update_order(
        cancelled_order,
        status="cancelled",
        cancel_reason="admin_cancelled",
    )

    with psycopg.connect(cooldown_database_url, row_factory=dict_row) as conn:
        state = conn.execute(
            """
            select businesses.ad_publication_paused_until, ads.status as ad_status
            from businesses
            join ads on ads.business_id = businesses.id
            where businesses.id = %s
            """,
            (ids["business_id"],),
        ).fetchone()
    assert pause_after_first is not None
    assert state["ad_publication_paused_until"] >= pause_after_first
    assert state["ad_status"] == "in_order"
    _cleanup(cooldown_database_url, ids)


def test_postgres_pre_report_terminal_does_not_start_cooldown(
    cooldown_database_url: str,
) -> None:
    ids = _seed_business_orders(cooldown_database_url, order_count=1, paid_reported=False)
    repository = PostgresOrderRepository(cooldown_database_url)
    order = repository.get_by_id(ids["order_ids"][0])
    assert order is not None

    repository.update_order(order, status="cancelled", cancel_reason="admin_cancelled")

    with psycopg.connect(cooldown_database_url, row_factory=dict_row) as conn:
        paused_until = conn.execute(
            "select ad_publication_paused_until from businesses where id = %s",
            (ids["business_id"],),
        ).fetchone()["ad_publication_paused_until"]
    assert paused_until is None
    _cleanup(cooldown_database_url, ids)


@pytest.mark.parametrize(
    ("resolution_type", "expected_dispute_status", "expected_order_status"),
    [
        ("business_favored", "resolved", "completed"),
        ("cancelled", "cancelled", "cancelled"),
    ],
)
def test_postgres_admin_dispute_terminal_resolution_applies_cooldown_in_same_transaction(
    cooldown_database_url: str,
    resolution_type: str,
    expected_dispute_status: str,
    expected_order_status: str,
) -> None:
    ids = _seed_business_orders(cooldown_database_url, order_count=1, paid_reported=True)
    order_id = ids["order_ids"][0]
    admin_id = str(uuid4())
    dispute_id = str(uuid4())
    with psycopg.connect(cooldown_database_url) as conn:
        conn.execute(
            "insert into users (id, role, status) values (%s, 'super_admin', 'active')",
            (admin_id,),
        )
        conn.execute(
            "update orders set status = 'disputed' where id = %s",
            (order_id,),
        )
        conn.execute(
            """
            insert into disputes (
                id, order_id, opened_by_user_id, opened_by_role,
                previous_order_status, reason, status
            )
            values (%s, %s, %s, 'remitter', 'delivered', 'other', 'open')
            """,
            (dispute_id, order_id, ids["remitter_ids"][0]),
        )
        started_at = conn.execute("select clock_timestamp()").fetchone()[0]
        conn.commit()

    repository = PostgresOrderRepository(cooldown_database_url)
    dispute, order, event_type, _, _ = repository.resolve_admin_dispute_atomically(
        dispute_id=dispute_id,
        resolution_type=resolution_type,
        reason="C3 local admin resolution",
        notes=None,
        actor_user_id=admin_id,
        actor_role="super_admin",
        request_id="c3_postgres_admin_completion",
    )

    with psycopg.connect(cooldown_database_url, row_factory=dict_row) as conn:
        state = conn.execute(
            """
            select businesses.ad_publication_paused_until, ads.status as ad_status
            from businesses
            join ads on ads.business_id = businesses.id
            where businesses.id = %s
            """,
            (ids["business_id"],),
        ).fetchone()

    assert dispute.status == expected_dispute_status
    assert order.status == expected_order_status
    assert event_type == "dispute_resolved"
    assert state["ad_publication_paused_until"] >= started_at + timedelta(minutes=15)
    assert state["ad_status"] == "archived"
    _cleanup(cooldown_database_url, ids)


def test_concurrent_postgres_terminal_orders_preserve_greatest_cooldown(
    cooldown_database_url: str,
) -> None:
    ids = _seed_business_orders(cooldown_database_url, order_count=2, paid_reported=True)
    repository = PostgresOrderRepository(cooldown_database_url)
    started_at = None
    with psycopg.connect(cooldown_database_url, row_factory=dict_row) as conn:
        started_at = conn.execute("select clock_timestamp() as value").fetchone()["value"]

    def complete(order_id: str) -> None:
        order = repository.get_by_id(order_id)
        assert order is not None
        repository.update_order(
            order,
            status="completed",
            completion_reason="auto_completed_after_24h",
            completed_at=order.updated_at,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(complete, ids["order_ids"]))

    with psycopg.connect(cooldown_database_url, row_factory=dict_row) as conn:
        stored = conn.execute(
            "select ad_publication_paused_until from businesses where id = %s",
            (ids["business_id"],),
        ).fetchone()["ad_publication_paused_until"]
        terminal_count = conn.execute(
            "select count(*) as value from orders where id = any(%s) and status = 'completed'",
            (ids["order_ids"],),
        ).fetchone()["value"]
    assert terminal_count == 2
    assert stored >= started_at + timedelta(minutes=15)
    _cleanup(cooldown_database_url, ids)


def test_postgres_terminal_paths_share_the_transactional_cooldown_helper() -> None:
    repository = (
        ROOT / "apps/api/app/modules/orders/postgres_repository.py"
    ).read_text(encoding="utf-8")
    receiver = (
        ROOT / "apps/api/app/modules/orders/postgres_receiver_completion.py"
    ).read_text(encoding="utf-8")
    admin = (
        ROOT / "apps/api/app/modules/orders/postgres_admin_dispute_resolution.py"
    ).read_text(encoding="utf-8")

    assert "ad_publication_paused_until = greatest(" in repository
    assert "now() + interval '15 minutes'" in repository
    assert "_apply_terminal_publication_cooldown_in_transaction" in receiver
    assert "_apply_terminal_publication_cooldown_in_transaction" in admin
