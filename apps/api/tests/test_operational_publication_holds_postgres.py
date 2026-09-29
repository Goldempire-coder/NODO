from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from app.core.errors import ApiError
from app.modules.ads.postgres_repository import PostgresAdRepository
from app.modules.business_capacity.postgres_repository import PostgresBusinessCapacityRepository
from app.modules.orders.postgres_repository import PostgresOrderRepository
from app.modules.support.postgres_repository import PostgresSupportRepository


ROOT = Path(__file__).resolve().parents[3]
POSTGRES_OPT_IN = "NODO_RUN_OPERATION_HOLD_POSTGRES"
POSTGRES_URL_ENV = "NODO_OPERATION_HOLD_POSTGRES_URL"


def _migration(name: str) -> str:
    return (ROOT / "database" / "migrations" / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def hold_database_url() -> str:
    if os.environ.get(POSTGRES_OPT_IN) != "1":
        pytest.skip(f"set {POSTGRES_OPT_IN}=1 for disposable local PostgreSQL validation")
    database_url = os.environ.get(POSTGRES_URL_ENV, "")
    parsed = urlparse(database_url)
    database_name = parsed.path.removeprefix("/").lower()
    if parsed.hostname not in {"127.0.0.1", "localhost"} or not database_name.startswith(
        "nodo_operation_hold_"
    ):
        raise RuntimeError(
            "hold PostgreSQL tests require a disposable localhost nodo_operation_hold_* database"
        )
    with psycopg.connect(database_url) as conn:
        table = conn.execute(
            """
            select 1 from information_schema.tables
            where table_schema = 'public'
              and table_name = 'business_publication_holds'
            """
        ).fetchone()
    assert table is not None
    return database_url


def _seed_case(database_url: str, *, pause_active: bool = True) -> dict[str, str]:
    ids = {
        "owner_id": str(uuid4()),
        "remitter_id": str(uuid4()),
        "admin_id": str(uuid4()),
        "business_id": str(uuid4()),
        "payment_method_id": str(uuid4()),
        "report_ad_id": str(uuid4()),
        "order_ad_id": str(uuid4()),
        "completed_order_id": str(uuid4()),
    }
    pause_sql = "now() + interval '15 minutes'" if pause_active else "now() - interval '1 second'"
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            cursor.executemany(
                "insert into users (id, role, status) values (%s, %s, 'active')",
                (
                    (ids["owner_id"], "business_owner"),
                    (ids["remitter_id"], "remitter"),
                    (ids["admin_id"], "admin"),
                ),
            )
        conn.execute(
            f"""
            insert into businesses (
                id, owner_user_id, business_name, verification_status, approved_at,
                min_order_amount_usd, max_order_amount_usd, daily_limit_usd,
                active_order_limit, is_accepting_orders, ad_publication_paused_until
            )
            values (%s, %s, 'Operational Hold Business', 'approved', now(),
                    20, 100, 1000, 2, true, {pause_sql})
            """,
            (ids["business_id"], ids["owner_id"]),
        )
        conn.execute(
            """
            insert into business_capacity (
                business_id, declared_available_capacity_usd, created_at, updated_at
            )
            values (%s, 200, now(), now())
            """,
            (ids["business_id"],),
        )
        conn.execute(
            """
            insert into business_payment_methods (
                id, business_id, method_type, account_value, account_masked,
                holder_name, verified_status, active
            )
            values (%s, %s, 'zelle', 'local@example.test', 'l***@example.test',
                    'Local Holder', 'approved', true)
            """,
            (ids["payment_method_id"], ids["business_id"]),
        )
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                insert into ads (
                    id, business_id, payment_method_id, payment_method, delivery_method,
                    rate_bs_per_usd, amount_min_usd, amount_max_usd, required_credits,
                    status, activated_at, expires_at
                )
                values (%s, %s, %s, 'zelle', 'pago_movil_ve', 40, 20, 100, 1,
                        %s, now(), now() + interval '7 days')
                """,
                (
                    (
                        ids["report_ad_id"],
                        ids["business_id"],
                        ids["payment_method_id"],
                        "archived",
                    ),
                    (
                        ids["order_ad_id"],
                        ids["business_id"],
                        ids["payment_method_id"],
                        "active",
                    ),
                ),
            )
        conn.execute(
            """
            insert into orders (
                id, public_order_code, ad_id, business_id, remitter_user_id,
                status, completion_reason, amount_usd, rate_snapshot,
                amount_bs_calculated, business_name_snapshot,
                payment_method_snapshot, delivery_method_snapshot,
                min_amount_snapshot, max_amount_snapshot,
                payment_instructions_snapshot, receiver_data_json,
                payment_report_deadline_at, expires_at, completed_at
            )
            values (%s, %s, %s, %s, %s, 'completed', 'manual_confirmed', 50, 40,
                    2000, 'Operational Hold Business', 'zelle', 'pago_movil_ve',
                    20, 100, '{}'::jsonb, '{}'::jsonb,
                    now() + interval '30 minutes', now() + interval '30 minutes', now())
            """,
            (
                ids["completed_order_id"],
                f"NODO-{uuid4().hex[:8].upper()}",
                ids["report_ad_id"],
                ids["business_id"],
                ids["remitter_id"],
            ),
        )
        conn.commit()
    return ids


def _ticket_fields(ids: dict[str, str]) -> dict[str, object]:
    return {
        "requester_user_id": ids["remitter_id"],
        "requester_role": "remitter",
        "requester_surface": "client_mini_app",
        "scope": "client_order",
        "category": "order_help",
        "status": "open",
        "priority": "normal",
        "subject": "Local structured operation report",
        "report_kind": "structured_operation_report",
        "business_id": ids["business_id"],
        "order_id": ids["completed_order_id"],
        "ad_id": None,
        "credit_purchase_id": None,
        "dispute_id": None,
        "assigned_support_user_id": None,
        "last_message_at": None,
        "escalated_at": None,
        "resolved_at": None,
        "closed_at": None,
    }


def _create_report(repository: PostgresSupportRepository, ids: dict[str, str]):
    return repository.create_operation_report(
        ticket_fields=_ticket_fields(ids),
        message_body="Local report without sensitive values",
        event_metadata={"report_kind": "structured_operation_report"},
    )


def _order_fields(ids: dict[str, str], *, idempotency_key: str) -> dict[str, object]:
    deadline = datetime.now(timezone.utc) + timedelta(minutes=30)
    return {
        "ad_id": ids["order_ad_id"],
        "business_id": ids["business_id"],
        "remitter_user_id": ids["remitter_id"],
        "status": "waiting_payment",
        "idempotency_key": idempotency_key,
        "amount_usd": Decimal("50.00"),
        "rate_snapshot": Decimal("40.000000"),
        "amount_bs_calculated": Decimal("2000.00"),
        "business_name_snapshot": "Operational Hold Business",
        "payment_method_snapshot": "zelle",
        "delivery_method_snapshot": "pago_movil_ve",
        "min_amount_snapshot": Decimal("20.00"),
        "max_amount_snapshot": Decimal("100.00"),
        "payment_instructions_snapshot": {},
        "receiver_data_json": {},
        "payment_report_deadline_at": deadline,
        "expires_at": deadline,
        "capacity_reservation": {
            "amount_usd": Decimal("50.00"),
            "reason": "order_created",
        },
    }


def _cleanup(database_url: str, ids: dict[str, str]) -> None:
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "delete from notification_jobs where metadata_json ->> 'business_id' = %s",
            (ids["business_id"],),
        )
        conn.execute(
            "delete from business_capacity_reservations where business_id = %s",
            (ids["business_id"],),
        )
        conn.execute(
            "delete from order_state_events where order_id in (select id from orders where business_id = %s)",
            (ids["business_id"],),
        )
        conn.execute(
            "delete from audit_logs where resource_id in (select id from orders where business_id = %s)",
            (ids["business_id"],),
        )
        conn.execute(
            "delete from business_publication_holds where business_id = %s",
            (ids["business_id"],),
        )
        conn.execute(
            "delete from support_ticket_events where ticket_id in (select id from support_tickets where business_id = %s)",
            (ids["business_id"],),
        )
        conn.execute(
            "delete from support_messages where ticket_id in (select id from support_tickets where business_id = %s)",
            (ids["business_id"],),
        )
        conn.execute("delete from support_tickets where business_id = %s", (ids["business_id"],))
        conn.execute("delete from orders where business_id = %s", (ids["business_id"],))
        conn.execute("delete from credits_ledger where business_id = %s", (ids["business_id"],))
        conn.execute("delete from credit_wallets where business_id = %s", (ids["business_id"],))
        conn.execute("delete from ads where business_id = %s", (ids["business_id"],))
        conn.execute(
            "delete from business_payment_methods where business_id = %s",
            (ids["business_id"],),
        )
        conn.execute("delete from business_capacity where business_id = %s", (ids["business_id"],))
        conn.execute("delete from businesses where id = %s", (ids["business_id"],))
        conn.execute(
            "delete from users where id = any(%s)",
            ([ids["owner_id"], ids["remitter_id"], ids["admin_id"]],),
        )
        conn.commit()


def test_0052_down_up_is_reversible_and_fail_closed_with_existing_holds(
    hold_database_url: str,
) -> None:
    ids = _seed_case(hold_database_url)
    repository = PostgresSupportRepository(hold_database_url)
    _ticket, hold = _create_report(repository, ids)
    assert hold is not None
    try:
        with psycopg.connect(hold_database_url) as conn:
            with pytest.raises(psycopg.Error):
                conn.execute(_migration("0052_business_publication_holds.down.sql"))
            conn.rollback()
            assert conn.execute(
                "select 1 from business_publication_holds where id = %s",
                (hold.id,),
            ).fetchone() is not None

            conn.execute("delete from business_publication_holds where id = %s", (hold.id,))
            conn.commit()
            conn.execute(_migration("0052_business_publication_holds.down.sql"))
            conn.commit()
            assert conn.execute(
                """
                select 1 from information_schema.tables
                where table_schema = 'public' and table_name = 'business_publication_holds'
                """
            ).fetchone() is None

            conn.execute(_migration("0052_business_publication_holds.up.sql"))
            conn.commit()
            assert conn.execute(
                "select 1 from businesses where id = %s",
                (ids["business_id"],),
            ).fetchone() is not None
    finally:
        _cleanup(hold_database_url, ids)


def test_postgres_operation_report_creates_hold_only_during_active_pause(
    hold_database_url: str,
) -> None:
    repository = PostgresSupportRepository(hold_database_url)
    active_ids = _seed_case(hold_database_url, pause_active=True)
    expired_ids = _seed_case(hold_database_url, pause_active=False)
    try:
        active_ticket, active_hold = _create_report(repository, active_ids)
        expired_ticket, expired_hold = _create_report(repository, expired_ids)
        assert active_hold is not None
        assert active_hold.support_ticket_id == active_ticket.id
        assert active_hold.business_id == active_ids["business_id"]
        assert repository.get_publication_hold_for_ticket(active_ticket.id).id == active_hold.id
        assert expired_hold is None

        with psycopg.connect(hold_database_url, row_factory=dict_row) as conn:
            counts = conn.execute(
                """
                select
                    (select count(*) from support_messages where ticket_id = %s) as message_count,
                    (select count(*) from support_ticket_events where ticket_id = %s) as event_count,
                    (select count(*) from business_publication_holds where support_ticket_id = %s) as hold_count,
                    (select count(*) from business_publication_holds where support_ticket_id = %s) as expired_hold_count
                """,
                (active_ticket.id, active_ticket.id, active_ticket.id, expired_ticket.id),
            ).fetchone()
            assert counts == {
                "message_count": 1,
                "event_count": 1,
                "hold_count": 1,
                "expired_hold_count": 0,
            }
    finally:
        _cleanup(hold_database_url, active_ids)
        _cleanup(hold_database_url, expired_ids)


def test_concurrent_postgres_operation_report_does_not_duplicate_hold(
    hold_database_url: str,
) -> None:
    ids = _seed_case(hold_database_url)
    repository = PostgresSupportRepository(hold_database_url)

    def create_once() -> str:
        try:
            ticket, hold = _create_report(repository, ids)
            assert hold is not None
            return f"created:{ticket.id}"
        except ApiError as exc:
            return exc.code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _index: create_once(), range(2)))
        assert sum(result.startswith("created:") for result in results) == 1
        assert results.count("OPERATION_REPORT_DUPLICATE") == 1
        with psycopg.connect(hold_database_url, row_factory=dict_row) as conn:
            counts = conn.execute(
                """
                select
                    (select count(*) from support_tickets where order_id = %s) as ticket_count,
                    (select count(*) from business_publication_holds where order_id = %s) as hold_count
                """,
                (ids["completed_order_id"], ids["completed_order_id"]),
            ).fetchone()
            assert counts == {"ticket_count": 1, "hold_count": 1}
    finally:
        _cleanup(hold_database_url, ids)


def test_postgres_hold_blocks_marketplace_publish_and_direct_order(
    hold_database_url: str,
) -> None:
    ids = _seed_case(hold_database_url)
    support = PostgresSupportRepository(hold_database_url)
    _ticket, hold = _create_report(support, ids)
    assert hold is not None
    ads = PostgresAdRepository(hold_database_url)
    capacity = PostgresBusinessCapacityRepository(hold_database_url)
    orders = PostgresOrderRepository(hold_database_url, capacity_repository=capacity)
    try:
        with psycopg.connect(hold_database_url) as conn:
            conn.execute(
                "update businesses set ad_publication_paused_until = now() where id = %s",
                (ids["business_id"],),
            )
            conn.commit()

        marketplace, _cursor = ads.list_marketplace_ads_with_businesses(
            amount_usd=Decimal("50.00"),
            payment_method=None,
            delivery_method=None,
            cursor=None,
            limit=20,
        )
        assert marketplace == []
        with pytest.raises(ApiError) as publish_blocked:
            ads.publish_ad(
                business_id=ids["business_id"],
                payment_method_id=ids["payment_method_id"],
                payment_method="zelle",
                delivery_method="pago_movil_ve",
                rate_bs_per_usd=Decimal("40.000000"),
                amount_min_usd=Decimal("20.00"),
                amount_max_usd=Decimal("50.00"),
                required_credits=1,
                created_by=ids["owner_id"],
            )
        assert publish_blocked.value.code == "BUSINESS_PUBLICATION_UNDER_REVIEW"

        with pytest.raises(ApiError) as order_blocked:
            orders.create_order(**_order_fields(ids, idempotency_key="hold-blocked-order"))
        assert order_blocked.value.code == "AD_NOT_AVAILABLE"

        with psycopg.connect(hold_database_url, row_factory=dict_row) as conn:
            state = conn.execute(
                """
                select
                    (select status from ads where id = %s) as ad_status,
                    (select count(*) from orders where ad_id = %s) as orders_count,
                    (select count(*) from business_capacity_reservations where business_id = %s) as reservations_count,
                    (select count(*) from notification_jobs where metadata_json ->> 'business_id' = %s) as jobs_count
                """,
                (
                    ids["order_ad_id"],
                    ids["order_ad_id"],
                    ids["business_id"],
                    ids["business_id"],
                ),
            ).fetchone()
            assert state == {
                "ad_status": "active",
                "orders_count": 0,
                "reservations_count": 0,
                "jobs_count": 0,
            }
    finally:
        _cleanup(hold_database_url, ids)


def test_postgres_order_waiting_on_hold_lock_fails_closed(
    hold_database_url: str,
) -> None:
    ids = _seed_case(hold_database_url, pause_active=False)
    support = PostgresSupportRepository(hold_database_url)
    ticket = support.create_ticket(**_ticket_fields(ids))
    capacity = PostgresBusinessCapacityRepository(hold_database_url)
    orders = PostgresOrderRepository(hold_database_url, capacity_repository=capacity)
    try:
        with psycopg.connect(hold_database_url) as hold_conn:
            hold_conn.execute(
                "select id from businesses where id = %s for update",
                (ids["business_id"],),
            )
            hold_conn.execute(
                """
                insert into business_publication_holds (
                    business_id, order_id, support_ticket_id,
                    status, reason_type, created_at
                )
                values (%s, %s, %s, 'active', 'structured_operation_report', now())
                """,
                (ids["business_id"], ids["completed_order_id"], ticket.id),
            )
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    orders.create_order,
                    **_order_fields(ids, idempotency_key="hold-lock-race"),
                )
                time.sleep(0.2)
                assert not future.done()
                hold_conn.commit()
                with pytest.raises(ApiError) as blocked:
                    future.result(timeout=5)
                assert blocked.value.code == "AD_NOT_AVAILABLE"

        with psycopg.connect(hold_database_url, row_factory=dict_row) as conn:
            state = conn.execute(
                """
                select
                    (select status from ads where id = %s) as ad_status,
                    (select count(*) from orders where ad_id = %s) as orders_count,
                    (select count(*) from business_capacity_reservations where business_id = %s) as reservations_count
                """,
                (ids["order_ad_id"], ids["order_ad_id"], ids["business_id"]),
            ).fetchone()
            assert state == {
                "ad_status": "active",
                "orders_count": 0,
                "reservations_count": 0,
            }
    finally:
        _cleanup(hold_database_url, ids)


def test_concurrent_postgres_release_has_one_durable_effect(
    hold_database_url: str,
) -> None:
    ids = _seed_case(hold_database_url)
    repository = PostgresSupportRepository(hold_database_url)
    _ticket, hold = _create_report(repository, ids)
    assert hold is not None

    def release_once(reason: str) -> str:
        try:
            released = repository.release_publication_hold(
                hold_id=hold.id,
                released_by=ids["admin_id"],
                release_reason=reason,
            )
            return f"released:{released.id}"
        except ApiError as exc:
            return exc.code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(release_once, ("First review", "Second review")))
        assert sum(result.startswith("released:") for result in results) == 1
        assert results.count("BUSINESS_PUBLICATION_HOLD_ALREADY_RELEASED") == 1
        with psycopg.connect(hold_database_url, row_factory=dict_row) as conn:
            stored = conn.execute(
                """
                select status, released_by, released_at is not null as has_released_at,
                       nullif(trim(release_reason), '') is not null as has_reason
                from business_publication_holds where id = %s
                """,
                (hold.id,),
            ).fetchone()
            stored["released_by"] = str(stored["released_by"])
            assert stored == {
                "status": "released",
                "released_by": ids["admin_id"],
                "has_released_at": True,
                "has_reason": True,
            }
    finally:
        _cleanup(hold_database_url, ids)
