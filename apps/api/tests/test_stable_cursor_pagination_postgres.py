from __future__ import annotations

import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import psycopg
import pytest

from app.core.errors import ApiError
from app.modules.admin.postgres_repository import PostgresAdminRepository
from app.modules.chat.postgres_repository import PostgresChatRepository
from app.modules.disputes.postgres_repository import PostgresDisputeRepository
from app.modules.orders.postgres_repository import PostgresOrderRepository
from app.modules.support.postgres_repository import PostgresSupportRepository
from app.shared.keyset_pagination import encode_keyset_cursor


POSTGRES_OPT_IN = "NODO_RUN_STABLE_CURSOR_POSTGRES"
POSTGRES_URL_ENV = "NODO_STABLE_CURSOR_POSTGRES_URL"
TIED_AT = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)


def _uuid(index: int) -> str:
    return f"00000000-0000-0000-0000-{index:012d}"


@pytest.fixture(scope="module")
def cursor_database_url() -> str:
    if os.environ.get(POSTGRES_OPT_IN) != "1":
        pytest.skip(f"set {POSTGRES_OPT_IN}=1 for disposable local PostgreSQL validation")
    database_url = os.environ.get(POSTGRES_URL_ENV, "")
    parsed = urlparse(database_url)
    database_name = parsed.path.removeprefix("/").lower()
    if parsed.hostname not in {"127.0.0.1", "localhost"} or not database_name.startswith("nodo_cursor_"):
        raise RuntimeError("stable cursor tests require a disposable localhost nodo_cursor_* database")
    with psycopg.connect(database_url) as conn:
        current_database = conn.execute("select current_database()").fetchone()[0]
        required_tables = conn.execute(
            """
            select table_name from information_schema.tables
            where table_schema = 'public'
              and table_name = any(%s)
            """,
            (["orders", "disputes", "support_tickets"],),
        ).fetchall()
    assert current_database.lower().startswith("nodo_cursor_")
    assert {row[0] for row in required_tables} == {"orders", "disputes", "support_tickets"}
    return database_url


def _collect_ids(page_loader) -> list[str]:  # type: ignore[no-untyped-def]
    ids: list[str] = []
    cursor = None
    for _ in range(10):
        page, cursor = page_loader(cursor)
        ids.extend(item.id if hasattr(item, "id") else item["id"] for item in page)
        if cursor is None:
            return ids
    raise AssertionError("pagination did not terminate")


def test_postgres_rejects_non_uuid_cursor_before_connect(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = PostgresSupportRepository("postgresql://unused")
    monkeypatch.setattr(
        repository,
        "_connect",
        lambda: pytest.fail("invalid cursor reached PostgreSQL"),
    )
    cursor = encode_keyset_cursor(TIED_AT, "not-a-uuid")

    with pytest.raises(ApiError) as exc_info:
        repository.list_tickets(
            requester_user_id=_uuid(100),
            business_id=None,
            statuses=None,
            scope=None,
            category=None,
            priority=None,
            assigned_support_user_id=None,
            cursor=cursor,
            limit=2,
        )

    assert exc_info.value.code == "PAGINATION_CURSOR_INVALID"
    assert exc_info.value.status_code == 400


def test_postgres_keyset_cursor_preserves_tied_support_orders_and_disputes(cursor_database_url: str) -> None:
    remitter_id = _uuid(100)
    owner_id = _uuid(101)
    business_id = _uuid(200)
    payment_method_id = _uuid(201)
    ad_id = _uuid(202)
    order_ids = [_uuid(index) for index in (301, 302, 303)]
    dispute_ids = [_uuid(index) for index in (401, 402, 403)]
    ticket_ids = [_uuid(index) for index in (501, 502, 503)]
    support_message_ids = [_uuid(index) for index in range(600, 725)]
    support_event_ids = [_uuid(index) for index in range(730, 785)]
    chat_message_ids = [_uuid(index) for index in range(800, 855)]
    with psycopg.connect(cursor_database_url) as conn:
        conn.execute("insert into users (id, role, status) values (%s, 'remitter', 'active'), (%s, 'business_owner', 'active')", (remitter_id, owner_id))
        conn.execute(
            """
            insert into businesses (id, owner_user_id, business_name, verification_status, approved_at)
            values (%s, %s, 'Cursor Business', 'approved', %s)
            """,
            (business_id, owner_id, TIED_AT),
        )
        conn.execute(
            """
            insert into business_payment_methods (
                id, business_id, method_type, account_value, account_masked,
                holder_name, verified_status, active
            ) values (%s, %s, 'zelle', 'cursor@example.invalid', '***', 'Cursor Owner', 'approved', true)
            """,
            (payment_method_id, business_id),
        )
        conn.execute(
            """
            insert into ads (
                id, business_id, payment_method_id, payment_method, delivery_method,
                rate_bs_per_usd, amount_min_usd, amount_max_usd, required_credits,
                status, activated_at, expires_at
            ) values (%s, %s, %s, 'zelle', 'pago_movil_ve', 40, 20, 100, 1,
                      'active', %s, %s + interval '1 day')
            """,
            (ad_id, business_id, payment_method_id, TIED_AT, TIED_AT),
        )
        for index, order_id in enumerate(order_ids, start=1):
            conn.execute(
                """
                insert into orders (
                    id, public_order_code, ad_id, business_id, remitter_user_id, status,
                    amount_usd, rate_snapshot, amount_bs_calculated, business_name_snapshot,
                    payment_method_snapshot, delivery_method_snapshot, min_amount_snapshot,
                    max_amount_snapshot, payment_instructions_snapshot, receiver_data_json,
                    payment_report_deadline_at, expires_at, created_at, updated_at
                ) values (
                    %s, %s, %s, %s, %s, 'waiting_payment', 20, 40, 800,
                    'Cursor Business', 'zelle', 'pago_movil_ve', 20, 100,
                    '{}'::jsonb, '{}'::jsonb, %s + interval '15 minutes',
                    %s + interval '30 minutes', %s, %s
                )
                """,
                (order_id, f"NODO-CURSOR-{index}", ad_id, business_id, remitter_id, TIED_AT, TIED_AT, TIED_AT, TIED_AT),
            )
        for dispute_id, order_id in zip(dispute_ids, order_ids, strict=True):
            conn.execute(
                """
                insert into disputes (
                    id, order_id, opened_by_user_id, opened_by_role, previous_order_status,
                    reason, status, created_at, updated_at
                ) values (%s, %s, %s, 'remitter', 'payment_reported', 'other', 'open', %s, %s)
                """,
                (dispute_id, order_id, remitter_id, TIED_AT, TIED_AT),
            )
        for ticket_id in ticket_ids:
            conn.execute(
                """
                insert into support_tickets (
                    id, requester_user_id, requester_role, requester_surface, scope,
                    category, status, priority, subject, created_at, updated_at
                ) values (%s, %s, 'remitter', 'client_mini_app', 'client_general',
                          'technical_issue', 'open', 'normal', 'Cursor ticket', %s, %s)
                """,
                (ticket_id, remitter_id, TIED_AT, TIED_AT),
            )
        for message_id in support_message_ids:
            conn.execute(
                """
                insert into support_messages (
                    id, ticket_id, sender_user_id, sender_role, body, visibility,
                    created_at, updated_at
                ) values (%s, %s, %s, 'remitter', 'Support cursor message',
                          'participants', %s, %s)
                """,
                (message_id, ticket_ids[0], remitter_id, TIED_AT, TIED_AT),
            )
        for event_id in support_event_ids:
            conn.execute(
                """
                insert into support_ticket_events (
                    id, ticket_id, actor_user_id, actor_role, event_type,
                    metadata_json, created_at
                ) values (%s, %s, %s, 'support', 'support_message_created',
                          '{}'::jsonb, %s)
                """,
                (event_id, ticket_ids[0], remitter_id, TIED_AT),
            )
        for message_id in chat_message_ids:
            conn.execute(
                """
                insert into messages (
                    id, order_id, sender_user_id, sender_role, body, visibility,
                    status, created_at, updated_at
                ) values (%s, %s, %s, 'remitter', 'Chat cursor message',
                          'parties', 'visible', %s, %s)
                """,
                (message_id, order_ids[0], remitter_id, TIED_AT, TIED_AT),
            )
        conn.commit()

    support = PostgresSupportRepository(cursor_database_url)
    orders = PostgresOrderRepository(cursor_database_url)
    admin = PostgresAdminRepository(cursor_database_url)
    disputes = PostgresDisputeRepository(cursor_database_url)
    chat = PostgresChatRepository(cursor_database_url)

    support_ids = _collect_ids(
        lambda cursor: support.list_tickets(
            requester_user_id=remitter_id,
            business_id=None,
            statuses=None,
            scope=None,
            category=None,
            priority=None,
            assigned_support_user_id=None,
            cursor=cursor,
            limit=2,
        )
    )
    order_ids_client = _collect_ids(
        lambda cursor: orders.list_for_remitter(remitter_user_id=remitter_id, status=None, cursor=cursor, limit=2)
    )
    order_ids_admin = _collect_ids(
        lambda cursor: admin.list_orders(status=None, business_id=None, remitter_user_id=remitter_id, cursor=cursor, limit=2)
    )
    listed_dispute_ids = _collect_ids(
        lambda cursor: disputes.list_disputes(status=None, cursor=cursor, limit=2)
    )
    listed_support_message_ids = _collect_ids(
        lambda cursor: support.list_messages_page(
            ticket_id=ticket_ids[0],
            cursor=cursor,
            limit=25,
            include_internal=False,
            viewer_user_id=remitter_id,
        )
    )
    listed_admin_support_message_ids = _collect_ids(
        lambda cursor: support.list_messages_page(
            ticket_id=ticket_ids[0],
            cursor=cursor,
            limit=25,
            include_internal=True,
            viewer_user_id=None,
        )
    )
    listed_support_event_ids = _collect_ids(
        lambda cursor: support.list_events_page(
            ticket_id=ticket_ids[0],
            cursor=cursor,
            limit=20,
        )
    )
    listed_chat_message_ids = _collect_ids(
        lambda cursor: chat.list_messages(order_id=order_ids[0], cursor=cursor, limit=20)
    )

    assert support_ids == list(reversed(ticket_ids))
    assert order_ids_client == list(reversed(order_ids))
    assert order_ids_admin == list(reversed(order_ids))
    assert listed_dispute_ids == list(reversed(dispute_ids))
    assert all(len(ids) == len(set(ids)) for ids in (support_ids, order_ids_client, order_ids_admin, listed_dispute_ids))
    assert set(listed_support_message_ids) == set(support_message_ids)
    assert len(listed_support_message_ids) == len(set(listed_support_message_ids))
    assert set(listed_admin_support_message_ids) == set(support_message_ids)
    assert len(listed_admin_support_message_ids) == len(set(listed_admin_support_message_ids))
    assert set(listed_support_event_ids) == set(support_event_ids)
    assert len(listed_support_event_ids) == len(set(listed_support_event_ids))
    assert set(listed_chat_message_ids) == set(chat_message_ids)
    assert len(listed_chat_message_ids) == len(set(listed_chat_message_ids))
