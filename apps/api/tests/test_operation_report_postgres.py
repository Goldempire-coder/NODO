from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest

from app.core.errors import ApiError
from app.modules.support.postgres_repository import PostgresSupportRepository


ROOT = Path(__file__).resolve().parents[3]
POSTGRES_OPT_IN = "NODO_RUN_OPERATION_REPORT_POSTGRES"
POSTGRES_URL_ENV = "NODO_OPERATION_REPORT_POSTGRES_URL"


def _migration(name: str) -> str:
    return (ROOT / "database" / "migrations" / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def operation_report_database_url() -> str:
    if os.environ.get(POSTGRES_OPT_IN) != "1":
        pytest.skip(f"set {POSTGRES_OPT_IN}=1 for disposable local PostgreSQL validation")
    database_url = os.environ.get(POSTGRES_URL_ENV, "")
    parsed = urlparse(database_url)
    database_name = parsed.path.removeprefix("/").lower()
    if parsed.hostname not in {"127.0.0.1", "localhost"} or not database_name.startswith("nodo_operation_report_"):
        raise RuntimeError("operation report PostgreSQL tests require a disposable localhost nodo_operation_report_* database")
    with psycopg.connect(database_url) as conn:
        column = conn.execute(
            """
            select 1 from information_schema.columns
            where table_schema = 'public'
              and table_name = 'support_tickets'
              and column_name = 'report_kind'
            """
        ).fetchone()
    assert column is not None
    return database_url


def _ticket_fields(*, user_id: str, order_id: str | None, business_id: str | None, report_kind: str | None) -> dict:
    return {
        "requester_user_id": user_id,
        "requester_role": "remitter",
        "requester_surface": "client_mini_app",
        "scope": "client_order" if order_id else "client_general",
        "category": "order_help",
        "status": "open",
        "priority": "normal",
        "subject": "Local operation report",
        "report_kind": report_kind,
        "business_id": business_id,
        "order_id": order_id,
        "ad_id": None,
        "credit_purchase_id": None,
        "dispute_id": None,
        "assigned_support_user_id": None,
        "last_message_at": None,
        "escalated_at": None,
        "resolved_at": None,
        "closed_at": None,
    }


def test_0051_down_up_preserves_generic_support_ticket(operation_report_database_url: str) -> None:
    user_id = str(uuid4())
    ticket_id = str(uuid4())
    with psycopg.connect(operation_report_database_url) as conn:
        conn.execute("insert into users (id, role, status) values (%s, 'remitter', 'active')", (user_id,))
        conn.execute(
            """
            insert into support_tickets (
                id, requester_user_id, requester_role, requester_surface,
                scope, category, status, priority, subject
            )
            values (%s, %s, 'remitter', 'client_mini_app',
                    'client_general', 'order_help', 'open', 'normal', 'Generic ticket')
            """,
            (ticket_id, user_id),
        )
        conn.commit()

        conn.execute(_migration("0051_structured_operation_reports.down.sql"))
        conn.commit()
        assert conn.execute("select 1 from support_tickets where id = %s", (ticket_id,)).fetchone() is not None

        conn.execute(_migration("0051_structured_operation_reports.up.sql"))
        conn.commit()
        restored = conn.execute("select report_kind from support_tickets where id = %s", (ticket_id,)).fetchone()
        assert restored is not None
        assert restored[0] is None

        conn.execute("delete from support_tickets where id = %s", (ticket_id,))
        conn.execute("delete from users where id = %s", (user_id,))
        conn.commit()


def test_postgres_operation_report_has_durable_active_order_uniqueness(
    operation_report_database_url: str,
) -> None:
    owner_id = str(uuid4())
    remitter_id = str(uuid4())
    business_id = str(uuid4())
    payment_method_id = str(uuid4())
    ad_id = str(uuid4())
    order_id = str(uuid4())
    with psycopg.connect(operation_report_database_url) as conn:
        with conn.cursor() as cursor:
            cursor.executemany(
                "insert into users (id, role, status) values (%s, %s, 'active')",
                ((owner_id, "business_owner"), (remitter_id, "remitter")),
            )
        conn.execute(
            """
            insert into businesses (id, owner_user_id, business_name, verification_status, approved_at)
            values (%s, %s, 'Operation Report Business', 'approved', now())
            """,
            (business_id, owner_id),
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
                    2000, 'Operation Report Business', 'zelle', 'pago_movil_ve',
                    20, 100, '{}'::jsonb, '{}'::jsonb,
                    now() + interval '30 minutes', now() + interval '30 minutes', now())
            """,
            (order_id, f"NODO-{uuid4().hex[:8].upper()}", ad_id, business_id, remitter_id),
        )
        conn.commit()

    repository = PostgresSupportRepository(operation_report_database_url)
    first, hold = repository.create_operation_report(
        ticket_fields=_ticket_fields(
            user_id=remitter_id,
            order_id=order_id,
            business_id=business_id,
            report_kind="structured_operation_report",
        ),
        message_body="Local structured operation report",
        event_metadata={"report_kind": "structured_operation_report"},
    )
    assert hold is None
    assert first.report_kind == "structured_operation_report"
    assert repository.get_active_operation_report_for_order(order_id).id == first.id

    with pytest.raises(ApiError) as duplicate:
        repository.create_ticket(
            **_ticket_fields(
                user_id=remitter_id,
                order_id=order_id,
                business_id=business_id,
                report_kind="structured_operation_report",
            )
        )
    assert duplicate.value.code == "OPERATION_REPORT_DUPLICATE"

    repository.update_ticket(first, status="resolved", resolved_at=None)
    second = repository.create_ticket(
        **_ticket_fields(
            user_id=remitter_id,
            order_id=order_id,
            business_id=business_id,
            report_kind="structured_operation_report",
        )
    )
    assert second.id != first.id

    with psycopg.connect(operation_report_database_url) as conn:
        conn.execute(
            "delete from support_ticket_events where ticket_id in (select id from support_tickets where order_id = %s)",
            (order_id,),
        )
        conn.execute(
            "delete from support_messages where ticket_id in (select id from support_tickets where order_id = %s)",
            (order_id,),
        )
        conn.execute("delete from support_tickets where order_id = %s", (order_id,))
        conn.execute("delete from orders where id = %s", (order_id,))
        conn.execute("delete from ads where id = %s", (ad_id,))
        conn.execute("delete from business_payment_methods where id = %s", (payment_method_id,))
        conn.execute("delete from businesses where id = %s", (business_id,))
        conn.execute("delete from users where id in (%s, %s)", (owner_id, remitter_id))
        conn.commit()
