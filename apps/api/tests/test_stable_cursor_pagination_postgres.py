from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlparse

import psycopg
import pytest

from app.core.errors import ApiError
from app.modules.admin.postgres_repository import PostgresAdminRepository
from app.modules.admin_notifications.postgres_repository import PostgresAdminNotificationRepository
from app.modules.ads.postgres_repository import PostgresAdRepository
from app.modules.chat.postgres_repository import PostgresChatRepository
from app.modules.credits.postgres_repository import PostgresCreditRepository
from app.modules.disputes.postgres_repository import PostgresDisputeRepository
from app.modules.jobs.postgres_repository import PostgresJobRepository
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
            ([
                "orders",
                "disputes",
                "support_tickets",
                "businesses",
                "users",
                "audit_logs",
                "credit_purchases",
                "job_runs",
                "admin_notifications",
            ],),
        ).fetchall()
    assert current_database.lower().startswith("nodo_cursor_")
    assert {row[0] for row in required_tables} == {
        "orders",
        "disputes",
        "support_tickets",
        "businesses",
        "users",
        "audit_logs",
        "credit_purchases",
        "job_runs",
        "admin_notifications",
    }
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


def _truncate_cursor_test_data(conn) -> None:  # type: ignore[no-untyped-def]
    conn.execute(
        """
        truncate table
            admin_notifications,
            credit_purchases,
            job_runs,
            audit_logs,
            messages,
            support_ticket_events,
            support_messages,
            support_tickets,
            disputes,
            orders,
            ads,
            business_capacity,
            business_payment_methods,
            businesses,
            users
        cascade
        """
    )


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


@pytest.mark.parametrize(
    ("repository_factory", "invoke"),
    [
        (
            PostgresAdminRepository,
            lambda repository, cursor: repository.list_businesses(
                verification_status=None,
                risk_level=None,
                business_id=None,
                business_name=None,
                cursor=cursor,
                limit=2,
            ),
        ),
        (
            PostgresAdminRepository,
            lambda repository, cursor: repository.list_users(
                phone=None,
                telegram_id=None,
                username=None,
                role=None,
                status=None,
                cursor=cursor,
                limit=2,
                full_sensitive=False,
            ),
        ),
        (
            PostgresAdminRepository,
            lambda repository, cursor: repository.list_audit_logs(
                event_type=None,
                actor_user_id=None,
                resource_type=None,
                resource_id=None,
                cursor=cursor,
                limit=2,
            ),
        ),
        (
            PostgresCreditRepository,
            lambda repository, cursor: repository.list_purchases(
                status=None,
                business_id=None,
                cursor=cursor,
                limit=2,
            ),
        ),
        (
            PostgresJobRepository,
            lambda repository, cursor: repository.list_job_runs(
                job_type=None,
                status=None,
                cursor=cursor,
                limit=2,
            ),
        ),
        (
            PostgresAdminNotificationRepository,
            lambda repository, cursor: repository.list_notifications(
                status=None,
                priority=None,
                cursor=cursor,
                limit=2,
            ),
        ),
    ],
)
def test_postgres_admin_cursor_rejects_non_uuid_before_connect(
    monkeypatch: pytest.MonkeyPatch,
    repository_factory,
    invoke,
) -> None:
    repository = repository_factory("postgresql://unused")
    monkeypatch.setattr(
        repository,
        "_connect",
        lambda: pytest.fail("invalid cursor reached PostgreSQL"),
    )
    cursor = encode_keyset_cursor(TIED_AT, "not-a-uuid")

    with pytest.raises(ApiError) as exc_info:
        invoke(repository, cursor)

    assert exc_info.value.code == "PAGINATION_CURSOR_INVALID"
    assert exc_info.value.status_code == 400


def test_postgres_keyset_cursor_preserves_tied_admin_lists(cursor_database_url: str) -> None:
    admin_user_ids = [_uuid(index) for index in (2101, 2102, 2103)]
    business_owner_ids = [_uuid(index) for index in (2201, 2202, 2203)]
    business_ids = [_uuid(index) for index in (2301, 2302, 2303)]
    audit_ids = [_uuid(index) for index in (2401, 2402, 2403)]
    credit_owner_id = _uuid(2500)
    credit_business_id = _uuid(2501)
    credit_purchase_ids = [_uuid(index) for index in (2601, 2602, 2603)]
    job_run_ids = [_uuid(index) for index in (2701, 2702, 2703)]
    notification_ids = [_uuid(index) for index in (2801, 2802, 2803)]

    with psycopg.connect(cursor_database_url) as conn:
        _truncate_cursor_test_data(conn)
        for index, user_id in enumerate(admin_user_ids, start=1):
            conn.execute(
                """
                insert into users (
                    id, telegram_id, username, first_name, role, status, created_at, updated_at
                ) values (%s, %s, %s, 'Cursor', 'support', 'active', %s, %s)
                on conflict (id) do nothing
                """,
                (user_id, 500000 + index, f"admin_cursor_support_{index}", TIED_AT, TIED_AT),
            )
        for index, (owner_id, business_id) in enumerate(zip(business_owner_ids, business_ids, strict=True), start=1):
            conn.execute(
                """
                insert into users (
                    id, telegram_id, username, role, status, created_at, updated_at
                ) values (%s, %s, %s, 'business_owner', 'active', %s, %s)
                on conflict (id) do nothing
                """,
                (owner_id, 501000 + index, f"admin_cursor_owner_{index}", TIED_AT, TIED_AT),
            )
            conn.execute(
                """
                insert into businesses (
                    id, owner_user_id, business_name, verification_status,
                    risk_level, trust_level, approved_at, created_at, updated_at
                ) values (%s, %s, %s, 'approved', 'normal', 'basic', %s, %s, %s)
                on conflict (id) do nothing
                """,
                (business_id, owner_id, f"Admin Cursor Business {index}", TIED_AT, TIED_AT, TIED_AT),
            )
        conn.execute(
            """
            insert into users (
                id, telegram_id, username, role, status, created_at, updated_at
            ) values (%s, 502000, 'admin_cursor_credit_owner', 'business_owner', 'active', %s, %s)
            on conflict (id) do nothing
            """,
            (credit_owner_id, TIED_AT, TIED_AT),
        )
        conn.execute(
            """
            insert into businesses (
                id, owner_user_id, business_name, verification_status,
                risk_level, trust_level, approved_at, created_at, updated_at
            ) values (%s, %s, 'Admin Cursor Credit Business', 'approved',
                      'normal', 'basic', %s, %s, %s)
            on conflict (id) do nothing
            """,
            (credit_business_id, credit_owner_id, TIED_AT, TIED_AT, TIED_AT),
        )
        for index, audit_id in enumerate(audit_ids, start=1):
            conn.execute(
                """
                insert into audit_logs (
                    id, actor_user_id, actor_role, event_type, resource_type,
                    resource_id, request_id, metadata_json, created_at
                ) values (%s, %s, 'super_admin', 'admin_cursor_event',
                          'admin_cursor', %s, %s, '{}'::jsonb, %s)
                on conflict (id) do nothing
                """,
                (audit_id, admin_user_ids[0], business_ids[0], f"req-admin-cursor-{index}", TIED_AT),
            )
        for index, purchase_id in enumerate(credit_purchase_ids, start=1):
            conn.execute(
                """
                insert into credit_purchases (
                    id, business_id, package_code, credits_amount, price_usd,
                    payment_method, status, idempotency_key,
                    stripe_checkout_session_id, created_at, updated_at
                ) values (%s, %s, 'starter', 5, 10.00, 'stripe_checkout',
                          'created', %s, %s, %s, %s)
                on conflict (id) do nothing
                """,
                (
                    purchase_id,
                    credit_business_id,
                    f"admin-cursor-credit-{index}",
                    f"cs_admin_cursor_{index}",
                    TIED_AT,
                    TIED_AT,
                ),
            )
        for index, run_id in enumerate(job_run_ids, start=1):
            conn.execute(
                """
                insert into job_runs (
                    id, job_type, status, lock_acquired, attempts,
                    metadata_json, created_at, updated_at
                ) values (%s, 'expire_and_escalate_orders', 'started',
                          false, 0, '{}'::jsonb, %s, %s)
                on conflict (id) do nothing
                """,
                (run_id, TIED_AT, TIED_AT),
            )
        for index, notification_id in enumerate(notification_ids, start=1):
            conn.execute(
                """
                insert into admin_notifications (
                    id, notification_type, priority, status, source_surface,
                    resource_type, title, summary, dedupe_key, metadata_json,
                    first_seen_at, last_seen_at, created_at, updated_at
                ) values (%s, 'admin_cursor_notice', 'attention', 'unread',
                          'admin_web', 'admin_cursor', %s, 'Cursor summary',
                          %s, '{}'::jsonb, %s, %s, %s, %s)
                on conflict (id) do nothing
                """,
                (
                    notification_id,
                    f"Cursor notification {index}",
                    f"admin-cursor-notification-{index}",
                    TIED_AT,
                    TIED_AT,
                    TIED_AT,
                    TIED_AT,
                ),
            )
        conn.commit()

    admin = PostgresAdminRepository(cursor_database_url)
    credits = PostgresCreditRepository(cursor_database_url)
    jobs = PostgresJobRepository(cursor_database_url)
    notifications = PostgresAdminNotificationRepository(cursor_database_url)

    listed_business_ids = _collect_ids(
        lambda cursor: admin.list_businesses(
            verification_status="approved",
            risk_level=None,
            business_id=None,
            business_name="Admin Cursor Business",
            cursor=cursor,
            limit=2,
        )
    )
    listed_user_ids = _collect_ids(
        lambda cursor: admin.list_users(
            phone=None,
            telegram_id=None,
            username="admin_cursor_support",
            role="support",
            status="active",
            cursor=cursor,
            limit=2,
            full_sensitive=False,
        )
    )
    listed_audit_ids = _collect_ids(
        lambda cursor: admin.list_audit_logs(
            event_type="admin_cursor_event",
            actor_user_id=None,
            resource_type="admin_cursor",
            resource_id=None,
            cursor=cursor,
            limit=2,
        )
    )
    listed_credit_ids = _collect_ids(
        lambda cursor: credits.list_purchases(
            status="created",
            business_id=credit_business_id,
            cursor=cursor,
            limit=2,
        )
    )
    listed_job_ids = _collect_ids(
        lambda cursor: jobs.list_job_runs(
            job_type="expire_and_escalate_orders",
            status="started",
            cursor=cursor,
            limit=2,
        )
    )
    listed_notification_ids = _collect_ids(
        lambda cursor: notifications.list_notifications(
            status="unread",
            priority="attention",
            cursor=cursor,
            limit=2,
        )
    )

    assert listed_business_ids == list(reversed(business_ids))
    assert listed_user_ids == list(reversed(admin_user_ids))
    assert listed_audit_ids == list(reversed(audit_ids))
    assert listed_credit_ids == list(reversed(credit_purchase_ids))
    assert listed_job_ids == list(reversed(job_run_ids))
    assert listed_notification_ids == list(reversed(notification_ids))
    assert all(
        len(ids) == len(set(ids)) == 3
        for ids in (
            listed_business_ids,
            listed_user_ids,
            listed_audit_ids,
            listed_credit_ids,
            listed_job_ids,
            listed_notification_ids,
        )
    )


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
        _truncate_cursor_test_data(conn)
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


def test_postgres_marketplace_cursor_preserves_tied_rate_date_and_method_filters(
    cursor_database_url: str,
) -> None:
    owner_ids = [_uuid(index) for index in range(1100, 1106)]
    business_ids = [_uuid(index) for index in range(1200, 1206)]
    payment_method_ids = [_uuid(index) for index in range(1300, 1306)]
    ad_ids = [_uuid(index) for index in range(1400, 1406)]
    methods = ["zelle", "zelle", "zelle", "usdt_trc20", "usdt_trc20", "usdt_trc20"]

    with psycopg.connect(cursor_database_url) as conn:
        _truncate_cursor_test_data(conn)
        for owner_id, business_id, payment_method_id, ad_id, method in zip(
            owner_ids,
            business_ids,
            payment_method_ids,
            ad_ids,
            methods,
            strict=True,
        ):
            conn.execute(
                "insert into users (id, role, status) values (%s, 'business_owner', 'active')",
                (owner_id,),
            )
            conn.execute(
                """
                insert into businesses (
                    id, owner_user_id, business_name, verification_status,
                    max_order_amount_usd, daily_limit_usd, approved_at
                ) values (%s, %s, %s, 'approved', 1000, 1000, %s)
                """,
                (business_id, owner_id, f"Marketplace Cursor {ad_id[-4:]}", TIED_AT),
            )
            conn.execute(
                """
                insert into business_payment_methods (
                    id, business_id, method_type, network, account_value,
                    account_masked, holder_name, verified_status, active
                ) values (%s, %s, %s, %s, %s, 'masked', 'Cursor Owner', 'approved', true)
                """,
                (
                    payment_method_id,
                    business_id,
                    method,
                    None if method == "zelle" else "TRC20",
                    f"cursor-{ad_id}@example.invalid",
                ),
            )
            conn.execute(
                """
                insert into business_capacity (business_id, declared_available_capacity_usd)
                values (%s, 1000)
                """,
                (business_id,),
            )
            conn.execute(
                """
                insert into ads (
                    id, business_id, payment_method_id, payment_method, delivery_method,
                    rate_bs_per_usd, amount_min_usd, amount_max_usd, required_credits,
                    status, activated_at, expires_at, created_at, updated_at
                ) values (%s, %s, %s, %s, 'pago_movil_ve', 41.25, 20, 100, 1,
                          'active', %s, now() + interval '1 day', %s, %s)
                """,
                (ad_id, business_id, payment_method_id, method, TIED_AT, TIED_AT, TIED_AT),
            )
        conn.commit()

    repository = PostgresAdRepository(cursor_database_url)
    for method in {"zelle", "usdt_trc20"}:
        expected_ids = sorted(
            [ad_id for ad_id, ad_method in zip(ad_ids, methods, strict=True) if ad_method == method],
            reverse=True,
        )

        def load_page(cursor: str | None):
            rows, next_cursor = repository.list_marketplace_ads_with_businesses(
                amount_usd=Decimal("50.00"),
                payment_method=method,
                delivery_method="pago_movil_ve",
                cursor=cursor,
                limit=2,
            )
            return [ad for ad, _business in rows], next_cursor

        listed_ids = _collect_ids(load_page)
        assert listed_ids == expected_ids
        assert len(listed_ids) == len(set(listed_ids)) == 3
