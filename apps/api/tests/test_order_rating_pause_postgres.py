from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from app.modules.orders.ratings_repository import PostgresOrderRatingRepository


ROOT = Path(__file__).resolve().parents[3]
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
def rating_database_url() -> str:
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
    assert current_database.lower().startswith("nodo_rating_")
    assert pause_column is not None
    return database_url


def _migration(name: str) -> str:
    return (ROOT / "database" / "migrations" / name).read_text(encoding="utf-8")


def test_0050_down_up_preserves_existing_business_rows(rating_database_url: str) -> None:
    owner_id = str(uuid4())
    business_id = str(uuid4())
    with psycopg.connect(rating_database_url) as conn:
        conn.execute(
            "insert into users (id, role, status) values (%s, 'business_owner', 'active')",
            (owner_id,),
        )
        conn.execute(
            """
            insert into businesses (
                id, owner_user_id, business_name, verification_status, approved_at,
                ad_publication_paused_until
            )
            values (%s, %s, 'Migration Pause Business', 'approved', now(), now() + interval '15 minutes')
            """,
            (business_id, owner_id),
        )
        conn.commit()

        conn.execute(_migration("0050_business_ad_publication_pause.down.sql"))
        conn.commit()
        assert conn.execute("select 1 from businesses where id = %s", (business_id,)).fetchone() is not None
        assert conn.execute(
            """
            select 1 from information_schema.columns
            where table_schema = 'public'
              and table_name = 'businesses'
              and column_name = 'ad_publication_paused_until'
            """
        ).fetchone() is None

        conn.execute(_migration("0050_business_ad_publication_pause.up.sql"))
        conn.commit()
        restored = conn.execute(
            "select ad_publication_paused_until from businesses where id = %s",
            (business_id,),
        ).fetchone()
        assert restored is not None
        assert restored[0] is None

        conn.execute("delete from businesses where id = %s", (business_id,))
        conn.execute("delete from users where id = %s", (owner_id,))
        conn.commit()


def test_concurrent_postgres_ratings_preserve_greatest_publication_pause(
    rating_database_url: str,
) -> None:
    owner_id = str(uuid4())
    first_rater_id = str(uuid4())
    second_rater_id = str(uuid4())
    business_id = str(uuid4())
    payment_method_id = str(uuid4())
    ad_id = str(uuid4())
    first_order_id = str(uuid4())
    second_order_id = str(uuid4())
    user_ids = (owner_id, first_rater_id, second_rater_id)

    with psycopg.connect(rating_database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            cursor.executemany(
                "insert into users (id, role, status) values (%s, %s, 'active')",
                (
                    (owner_id, "business_owner"),
                    (first_rater_id, "remitter"),
                    (second_rater_id, "remitter"),
                ),
            )
        conn.execute(
            """
            insert into businesses (
                id, owner_user_id, business_name, verification_status, approved_at
            )
            values (%s, %s, 'Concurrent Pause Business', 'approved', now())
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
                    'active', now(), now() + interval '7 days')
            """,
            (ad_id, business_id, payment_method_id),
        )
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                insert into orders (
                    id, public_order_code, ad_id, business_id, remitter_user_id,
                    status, completion_reason, amount_usd, rate_snapshot,
                    amount_bs_calculated, business_name_snapshot,
                    payment_method_snapshot, delivery_method_snapshot,
                    min_amount_snapshot, max_amount_snapshot,
                    payment_instructions_snapshot, receiver_data_json,
                    payment_report_deadline_at, expires_at, payment_confirmed_at,
                    delivered_at, completed_at
                )
                values (
                    %s, %s, %s, %s, %s, 'completed', 'manual_confirmed', 50, 40,
                    2000, 'Concurrent Pause Business', 'zelle', 'pago_movil_ve',
                    20, 100, '{}'::jsonb, '{}'::jsonb, now() + interval '30 minutes',
                    now() + interval '30 minutes', now() - interval '10 minutes',
                    now() - interval '1 minute', now()
                )
                """,
                (
                    (first_order_id, f"NODO-{uuid4().hex[:8].upper()}", ad_id, business_id, first_rater_id),
                    (second_order_id, f"NODO-{uuid4().hex[:8].upper()}", ad_id, business_id, second_rater_id),
                ),
        )
        started_at = conn.execute("select clock_timestamp() as value").fetchone()["value"]
        conn.commit()

    repository = PostgresOrderRatingRepository(rating_database_url)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda args: repository.create_for_completed_order(
                    order_id=args[0],
                    rater_user_id=args[1],
                    stars=args[2],
                ),
                (
                    (first_order_id, first_rater_id, 1),
                    (second_order_id, second_rater_id, 5),
                ),
            )
        )

    assert sorted(result[0].stars for result in results) == [1, 5]
    with psycopg.connect(rating_database_url, row_factory=dict_row) as conn:
        finished_at = conn.execute("select clock_timestamp() as value").fetchone()["value"]
        stored = conn.execute(
            """
            select ad_publication_paused_until, ratings_count
            from businesses
            where id = %s
            """,
            (business_id,),
        ).fetchone()
        assert stored["ratings_count"] == 2
        assert started_at + timedelta(minutes=15) <= stored["ad_publication_paused_until"]
        assert stored["ad_publication_paused_until"] <= finished_at + timedelta(minutes=15)

        conn.execute("delete from ratings where order_id in (%s, %s)", (first_order_id, second_order_id))
        conn.execute("delete from orders where id in (%s, %s)", (first_order_id, second_order_id))
        conn.execute("delete from ads where id = %s", (ad_id,))
        conn.execute("delete from business_payment_methods where id = %s", (payment_method_id,))
        conn.execute("delete from businesses where id = %s", (business_id,))
        conn.execute("delete from users where id = any(%s)", (list(user_ids),))
        conn.commit()
