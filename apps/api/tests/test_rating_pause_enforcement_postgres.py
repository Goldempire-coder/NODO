from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from app.core.errors import ApiError
from app.modules.ads.postgres_repository import PostgresAdRepository
from app.modules.business_capacity.postgres_repository import PostgresBusinessCapacityRepository
from app.modules.orders.postgres_repository import PostgresOrderRepository


POSTGRES_OPT_IN = "NODO_RUN_RATING_POSTGRES"
POSTGRES_URL_ENV = "NODO_RATING_POSTGRES_URL"


def _require_disposable_local_database() -> str:
    if os.environ.get(POSTGRES_OPT_IN) != "1":
        pytest.skip(f"set {POSTGRES_OPT_IN}=1 for disposable local PostgreSQL validation")
    database_url = os.environ.get(POSTGRES_URL_ENV, "")
    parsed = urlparse(database_url)
    database_name = parsed.path.removeprefix("/").lower()
    if parsed.hostname not in {"127.0.0.1", "localhost"} or not database_name.startswith("nodo_rating_"):
        raise RuntimeError("rating PostgreSQL tests require a disposable localhost nodo_rating_* database")
    return database_url


@pytest.fixture(scope="module")
def enforcement_database_url() -> str:
    database_url = _require_disposable_local_database()
    with psycopg.connect(database_url) as conn:
        pause_column = conn.execute(
            """
            select 1
            from information_schema.columns
            where table_schema = 'public'
              and table_name = 'businesses'
              and column_name = 'ad_publication_paused_until'
            """
        ).fetchone()
    assert pause_column is not None
    return database_url


def _seed_publication_case(database_url: str) -> dict[str, str]:
    ids = {
        "owner_id": str(uuid4()),
        "remitter_id": str(uuid4()),
        "business_id": str(uuid4()),
        "payment_method_id": str(uuid4()),
        "ad_id": str(uuid4()),
    }
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "insert into users (id, role, status) values (%s, 'business_owner', 'active')",
            (ids["owner_id"],),
        )
        conn.execute(
            "insert into users (id, role, status) values (%s, 'remitter', 'active')",
            (ids["remitter_id"],),
        )
        conn.execute(
            """
            insert into businesses (
                id, owner_user_id, business_name, verification_status, approved_at,
                min_order_amount_usd, max_order_amount_usd, daily_limit_usd,
                active_order_limit, is_accepting_orders, ad_publication_paused_until
            )
            values (%s, %s, 'Pause Enforcement Business', 'approved', now(),
                    20, 100, 1000, 1, true, now() + interval '15 minutes')
            """,
            (ids["business_id"], ids["owner_id"]),
        )
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
            insert into business_payment_methods (
                id, business_id, method_type, network, account_value, account_masked,
                holder_name, verified_status, active
            )
            values (%s, %s, 'zelle', null, 'local@example.test', 'l***@example.test',
                    'Local Holder', 'approved', true)
            """,
            (ids["payment_method_id"], ids["business_id"]),
        )
        conn.execute(
            """
            insert into ads (
                id, business_id, payment_method_id, payment_method, delivery_method,
                rate_bs_per_usd, amount_min_usd, amount_max_usd, required_credits,
                status, activated_at, expires_at
            )
            values (%s, %s, %s, 'zelle', 'pago_movil_ve', 40, 20, 100, 1,
                    'active', now(), now() + interval '7 days')
            """,
            (ids["ad_id"], ids["business_id"], ids["payment_method_id"]),
        )
        conn.commit()
    return ids


def _order_fields(ids: dict[str, str], *, idempotency_key: str) -> dict[str, object]:
    deadline = datetime.now(timezone.utc) + timedelta(minutes=30)
    return {
        "ad_id": ids["ad_id"],
        "business_id": ids["business_id"],
        "remitter_user_id": ids["remitter_id"],
        "status": "waiting_payment",
        "idempotency_key": idempotency_key,
        "amount_usd": Decimal("50.00"),
        "rate_snapshot": Decimal("40.000000"),
        "amount_bs_calculated": Decimal("2000.00"),
        "business_name_snapshot": "Pause Enforcement Business",
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


def _cleanup_publication_case(database_url: str, ids: dict[str, str]) -> None:
    with psycopg.connect(database_url) as conn:
        conn.execute("delete from notification_jobs where metadata_json ->> 'business_id' = %s", (ids["business_id"],))
        conn.execute("delete from business_capacity_reservations where business_id = %s", (ids["business_id"],))
        conn.execute("delete from order_state_events where order_id in (select id from orders where business_id = %s)", (ids["business_id"],))
        conn.execute("delete from audit_logs where resource_id in (select id from orders where business_id = %s)", (ids["business_id"],))
        conn.execute("delete from orders where business_id = %s", (ids["business_id"],))
        conn.execute("delete from credits_ledger where business_id = %s", (ids["business_id"],))
        conn.execute("delete from credit_wallets where business_id = %s", (ids["business_id"],))
        conn.execute("delete from ads where business_id = %s", (ids["business_id"],))
        conn.execute("delete from business_payment_methods where business_id = %s", (ids["business_id"],))
        conn.execute("delete from business_capacity where business_id = %s", (ids["business_id"],))
        conn.execute("delete from businesses where id = %s", (ids["business_id"],))
        conn.execute("delete from users where id in (%s, %s)", (ids["owner_id"], ids["remitter_id"]))
        conn.commit()


def test_postgres_marketplace_and_ad_publish_use_database_pause(
    enforcement_database_url: str,
) -> None:
    ids = _seed_publication_case(enforcement_database_url)
    repository = PostgresAdRepository(enforcement_database_url)
    try:
        rows, _cursor = repository.list_marketplace_ads_with_businesses(
            amount_usd=Decimal("50.00"),
            payment_method=None,
            delivery_method=None,
            cursor=None,
            limit=20,
        )
        assert rows == []

        with pytest.raises(ApiError) as blocked:
            repository.publish_ad(
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
        assert blocked.value.code == "BUSINESS_PUBLICATION_TEMPORARILY_UNAVAILABLE"

        with psycopg.connect(enforcement_database_url, row_factory=dict_row) as conn:
            counts = conn.execute(
                """
                select
                    (select count(*) from ads where business_id = %s) as ads_count,
                    (select count(*) from credits_ledger where business_id = %s) as ledger_count
                """,
                (ids["business_id"], ids["business_id"]),
            ).fetchone()
            assert counts == {"ads_count": 1, "ledger_count": 0}

            conn.execute(
                "update businesses set ad_publication_paused_until = now() where id = %s",
                (ids["business_id"],),
            )
            conn.commit()

        rows_after, _cursor = repository.list_marketplace_ads_with_businesses(
            amount_usd=Decimal("50.00"),
            payment_method=None,
            delivery_method=None,
            cursor=None,
            limit=20,
        )
        assert [ad.id for ad, _business in rows_after] == [ids["ad_id"]]
    finally:
        _cleanup_publication_case(enforcement_database_url, ids)


def test_postgres_order_transaction_rejects_pause_without_partial_effects(
    enforcement_database_url: str,
) -> None:
    ids = _seed_publication_case(enforcement_database_url)
    capacity = PostgresBusinessCapacityRepository(enforcement_database_url)
    repository = PostgresOrderRepository(
        enforcement_database_url,
        capacity_repository=capacity,
    )
    try:
        with pytest.raises(ApiError) as blocked:
            repository.create_order(**_order_fields(ids, idempotency_key="paused-order"))
        assert blocked.value.code == "AD_NOT_AVAILABLE"

        with psycopg.connect(enforcement_database_url, row_factory=dict_row) as conn:
            state = conn.execute(
                """
                select
                    (select status from ads where id = %s) as ad_status,
                    (select count(*) from orders where business_id = %s) as orders_count,
                    (select count(*) from business_capacity_reservations where business_id = %s) as reservations_count,
                    (select count(*) from notification_jobs where metadata_json ->> 'business_id' = %s) as jobs_count
                """,
                (ids["ad_id"], ids["business_id"], ids["business_id"], ids["business_id"]),
            ).fetchone()
            assert state == {
                "ad_status": "active",
                "orders_count": 0,
                "reservations_count": 0,
                "jobs_count": 0,
            }
    finally:
        _cleanup_publication_case(enforcement_database_url, ids)


def test_postgres_order_waiting_on_rating_pause_lock_fails_closed(
    enforcement_database_url: str,
) -> None:
    ids = _seed_publication_case(enforcement_database_url)
    capacity = PostgresBusinessCapacityRepository(enforcement_database_url)
    repository = PostgresOrderRepository(
        enforcement_database_url,
        capacity_repository=capacity,
    )
    try:
        with psycopg.connect(enforcement_database_url) as rating_conn:
            rating_conn.execute(
                "select id from businesses where id = %s for update",
                (ids["business_id"],),
            )
            rating_conn.execute(
                "update businesses set ad_publication_paused_until = now() + interval '15 minutes' where id = %s",
                (ids["business_id"],),
            )

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    repository.create_order,
                    **_order_fields(ids, idempotency_key="pause-lock-race"),
                )
                time.sleep(0.2)
                assert not future.done()
                rating_conn.commit()
                with pytest.raises(ApiError) as blocked:
                    future.result(timeout=5)
                assert blocked.value.code == "AD_NOT_AVAILABLE"

        with psycopg.connect(enforcement_database_url, row_factory=dict_row) as conn:
            state = conn.execute(
                """
                select
                    (select status from ads where id = %s) as ad_status,
                    (select count(*) from orders where business_id = %s) as orders_count,
                    (select count(*) from business_capacity_reservations where business_id = %s) as reservations_count
                """,
                (ids["ad_id"], ids["business_id"], ids["business_id"]),
            ).fetchone()
            assert state == {
                "ad_status": "active",
                "orders_count": 0,
                "reservations_count": 0,
            }
    finally:
        _cleanup_publication_case(enforcement_database_url, ids)
