from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.errors import ApiError
from app.modules.admin.memory_repository import InMemoryAdminRepository
from app.modules.admin_notifications.memory_repository import InMemoryAdminNotificationRepository
from app.modules.admin_notifications.models import AdminNotificationRecord
from app.modules.businesses.models import BusinessRecord
from app.modules.credits.memory_repository import InMemoryCreditRepository
from app.modules.credits.models import CreditPurchaseRecord
from app.modules.disputes.memory_repository import InMemoryDisputeRepository
from app.modules.disputes.models import DisputeRecord
from app.modules.jobs.memory_repository import InMemoryJobRepository
from app.modules.jobs.models import JobRunRecord
from app.modules.orders.memory_repository import InMemoryOrderRepository
from app.modules.orders.models import OrderRecord
from app.modules.support.memory_repository import InMemorySupportRepository
from app.modules.support.models import SupportTicketRecord
from app.modules.users.models import UserRecord
from app.shared.audit.audit_service import AuditEvent
from app.shared.keyset_pagination import decode_keyset_cursor, encode_keyset_cursor


TIED_AT = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)


def _uuid(index: int) -> str:
    return f"00000000-0000-0000-0000-{index:012d}"


def _support_ticket(index: int, *, updated_at: datetime = TIED_AT) -> SupportTicketRecord:
    return SupportTicketRecord(
        id=_uuid(index),
        requester_user_id=_uuid(100),
        requester_role="remitter",
        requester_surface="client_mini_app",
        scope="client_general",
        category="technical_issue",
        status="open",
        priority="normal",
        subject=f"Ticket {index}",
        created_at=updated_at,
        updated_at=updated_at,
    )


def _order(index: int, *, created_at: datetime = TIED_AT) -> OrderRecord:
    return OrderRecord(
        id=_uuid(index),
        public_order_code=f"NODO-{index:06d}",
        ad_id=_uuid(200),
        business_id=_uuid(300),
        remitter_user_id=_uuid(100),
        status="waiting_payment",
        idempotency_key=f"order-{index}",
        amount_usd=Decimal("10.00"),
        rate_snapshot=Decimal("40.00"),
        amount_bs_calculated=Decimal("400.00"),
        business_name_snapshot="Negocio cursor",
        payment_method_snapshot="zelle",
        delivery_method_snapshot="pago_movil_ve",
        min_amount_snapshot=Decimal("10.00"),
        max_amount_snapshot=Decimal("100.00"),
        payment_instructions_snapshot={},
        receiver_data_json={},
        payment_report_deadline_at=created_at + timedelta(minutes=15),
        expires_at=created_at + timedelta(minutes=30),
        created_at=created_at,
        updated_at=created_at,
    )


def _dispute(index: int, *, created_at: datetime = TIED_AT) -> DisputeRecord:
    return DisputeRecord(
        id=_uuid(index),
        order_id=_uuid(400 + index),
        opened_by_user_id=_uuid(100),
        opened_by_role="remitter",
        previous_order_status="payment_reported",
        reason="payment_not_received_or_incomplete",
        description=None,
        created_at=created_at,
        updated_at=created_at,
    )


def _business(index: int, *, created_at: datetime = TIED_AT) -> BusinessRecord:
    return BusinessRecord(
        id=_uuid(index),
        owner_user_id=_uuid(900),
        business_name=f"Business {index}",
        rif=None,
        address=None,
        phone=None,
        created_at=created_at,
        updated_at=created_at,
    )


def _user(index: int, *, created_at: datetime = TIED_AT) -> UserRecord:
    return UserRecord(
        id=_uuid(index),
        telegram_id=100000 + index,
        username=f"user{index}",
        first_name="Cursor",
        last_name=f"User {index}",
        created_at=created_at,
        updated_at=created_at,
    )


def _audit_event(index: int, *, created_at: datetime = TIED_AT) -> AuditEvent:
    return AuditEvent(
        id=_uuid(index),
        event_type="cursor_test",
        actor_user_id=_uuid(100),
        actor_role="super_admin",
        resource_type="admin_console",
        resource_id=_uuid(700),
        request_id=f"req-cursor-{index}",
        metadata_json={},
        created_at=created_at,
    )


def _credit_purchase(index: int, *, created_at: datetime = TIED_AT) -> CreditPurchaseRecord:
    return CreditPurchaseRecord(
        id=_uuid(index),
        business_id=_uuid(300),
        package_code="starter",
        credits_amount=5,
        price_usd=Decimal("10.00"),
        payment_method="stripe_checkout",
        status="pending_payment",
        created_at=created_at,
        updated_at=created_at,
    )


def _job_run(index: int, *, created_at: datetime = TIED_AT) -> JobRunRecord:
    return JobRunRecord(
        id=_uuid(index),
        job_type="cursor_job",
        status="finished",
        created_at=created_at,
        updated_at=created_at,
    )


def _admin_notification(index: int, *, last_seen_at: datetime = TIED_AT) -> AdminNotificationRecord:
    return AdminNotificationRecord(
        id=_uuid(index),
        notification_type="cursor_notification",
        priority="info",
        status="unread",
        source_surface="admin_web",
        resource_type="admin_console",
        resource_id=_uuid(800),
        business_id=None,
        actor_user_id=None,
        title=f"Notification {index}",
        summary="Cursor notification",
        action_route=None,
        dedupe_key=f"cursor-notification-{index}",
        created_at=last_seen_at,
        updated_at=last_seen_at,
        first_seen_at=last_seen_at,
        last_seen_at=last_seen_at,
    )


def _admin_repository(
    *,
    businesses: dict[str, BusinessRecord] | None = None,
    users: dict[str, UserRecord] | None = None,
    audit_events: list[AuditEvent] | None = None,
) -> InMemoryAdminRepository:
    return InMemoryAdminRepository(
        users=SimpleNamespace(_users_by_id=users or {}),
        businesses=SimpleNamespace(businesses=businesses or {}),
        orders=SimpleNamespace(orders={}),
        disputes=SimpleNamespace(disputes={}),
        credits=SimpleNamespace(purchases={}),
        audit_writer=SimpleNamespace(events=audit_events or []),
    )


def _collect_all(page_loader) -> tuple[list[str], list[str | None]]:  # type: ignore[no-untyped-def]
    ids: list[str] = []
    cursors: list[str | None] = []
    cursor = None
    for _ in range(10):
        page, cursor = page_loader(cursor)
        ids.extend(item.id if hasattr(item, "id") else item["id"] for item in page)
        cursors.append(cursor)
        if cursor is None:
            return ids, cursors
    raise AssertionError("pagination did not terminate")


def _support_page(repository: InMemorySupportRepository, cursor: str | None, limit: int = 2):
    return repository.list_tickets(
        requester_user_id=_uuid(100),
        business_id=None,
        statuses=None,
        scope=None,
        category=None,
        priority=None,
        assigned_support_user_id=None,
        cursor=cursor,
        limit=limit,
    )


def test_support_cursor_does_not_lose_tickets_with_tied_updated_at() -> None:
    repository = InMemorySupportRepository()
    repository.tickets = {ticket.id: ticket for ticket in (_support_ticket(1), _support_ticket(2), _support_ticket(3))}

    ids, cursors = _collect_all(lambda cursor: _support_page(repository, cursor))

    assert ids == [_uuid(3), _uuid(2), _uuid(1)]
    assert len(ids) == len(set(ids))
    assert cursors[-1] is None


def test_order_cursor_does_not_lose_orders_for_client_business_or_admin() -> None:
    orders = InMemoryOrderRepository()
    orders.orders = {order.id: order for order in (_order(1), _order(2), _order(3))}
    disputes = InMemoryDisputeRepository()
    admin = InMemoryAdminRepository(
        users=SimpleNamespace(users={}),
        businesses=SimpleNamespace(businesses={}),
        orders=orders,
        disputes=disputes,
        credits=SimpleNamespace(purchases={}),
        audit_writer=SimpleNamespace(events=[]),
    )
    loaders = (
        lambda cursor: orders.list_for_remitter(remitter_user_id=_uuid(100), status=None, cursor=cursor, limit=2),
        lambda cursor: orders.list_for_business(business_id=_uuid(300), status=None, cursor=cursor, limit=2),
        lambda cursor: admin.list_orders(status=None, business_id=None, remitter_user_id=None, cursor=cursor, limit=2),
    )

    for loader in loaders:
        ids, cursors = _collect_all(loader)
        assert ids == [_uuid(3), _uuid(2), _uuid(1)]
        assert len(ids) == len(set(ids))
        assert cursors[-1] is None


def test_dispute_cursor_does_not_lose_disputes_with_tied_created_at() -> None:
    repository = InMemoryDisputeRepository()
    repository.disputes = {dispute.id: dispute for dispute in (_dispute(1), _dispute(2), _dispute(3))}

    ids, cursors = _collect_all(lambda cursor: repository.list_disputes(status=None, cursor=cursor, limit=2))

    assert ids == [_uuid(3), _uuid(2), _uuid(1)]
    assert len(ids) == len(set(ids))
    assert cursors[-1] is None


def test_admin_business_cursor_does_not_lose_businesses_with_tied_created_at() -> None:
    repository = _admin_repository(
        businesses={business.id: business for business in (_business(1), _business(2), _business(3))}
    )

    ids, cursors = _collect_all(
        lambda cursor: repository.list_businesses(
            verification_status=None,
            risk_level=None,
            business_id=None,
            business_name=None,
            cursor=cursor,
            limit=2,
        )
    )

    assert ids == [_uuid(3), _uuid(2), _uuid(1)]
    assert len(ids) == len(set(ids))
    assert cursors[-1] is None


def test_admin_user_cursor_does_not_lose_users_with_tied_created_at() -> None:
    repository = _admin_repository(users={user.id: user for user in (_user(1), _user(2), _user(3))})

    ids, cursors = _collect_all(
        lambda cursor: repository.list_users(
            phone=None,
            telegram_id=None,
            username=None,
            role=None,
            status=None,
            cursor=cursor,
            limit=2,
            full_sensitive=False,
        )
    )

    assert ids == [_uuid(3), _uuid(2), _uuid(1)]
    assert len(ids) == len(set(ids))
    assert cursors[-1] is None


def test_admin_audit_cursor_does_not_lose_events_with_tied_created_at() -> None:
    repository = _admin_repository(audit_events=[_audit_event(1), _audit_event(2), _audit_event(3)])

    ids, cursors = _collect_all(
        lambda cursor: repository.list_audit_logs(
            event_type=None,
            actor_user_id=None,
            resource_type=None,
            resource_id=None,
            cursor=cursor,
            limit=2,
        )
    )

    assert ids == [_uuid(3), _uuid(2), _uuid(1)]
    assert len(ids) == len(set(ids))
    assert cursors[-1] is None


def test_admin_credit_cursor_does_not_lose_purchases_with_tied_created_at() -> None:
    repository = InMemoryCreditRepository(ad_repository=SimpleNamespace(ledger={}), business_repository=SimpleNamespace())
    repository.purchases.update({purchase.id: purchase for purchase in (_credit_purchase(1), _credit_purchase(2), _credit_purchase(3))})

    ids, cursors = _collect_all(lambda cursor: repository.list_purchases(status=None, business_id=None, cursor=cursor, limit=2))

    assert ids == [_uuid(3), _uuid(2), _uuid(1)]
    assert len(ids) == len(set(ids))
    assert cursors[-1] is None


def test_admin_job_cursor_does_not_lose_runs_with_tied_created_at() -> None:
    repository = InMemoryJobRepository()
    repository.job_runs = {run.id: run for run in (_job_run(1), _job_run(2), _job_run(3))}

    ids, cursors = _collect_all(lambda cursor: repository.list_job_runs(job_type=None, status=None, cursor=cursor, limit=2))

    assert ids == [_uuid(3), _uuid(2), _uuid(1)]
    assert len(ids) == len(set(ids))
    assert cursors[-1] is None


def test_admin_notification_cursor_does_not_lose_notifications_with_tied_last_seen_at() -> None:
    repository = InMemoryAdminNotificationRepository()
    repository.notifications = {
        notification.id: notification
        for notification in (_admin_notification(1), _admin_notification(2), _admin_notification(3))
    }

    ids, cursors = _collect_all(lambda cursor: repository.list_notifications(status=None, priority=None, cursor=cursor, limit=2))

    assert ids == [_uuid(3), _uuid(2), _uuid(1)]
    assert len(ids) == len(set(ids))
    assert cursors[-1] is None


def test_next_cursor_is_absent_when_final_page_exactly_matches_limit() -> None:
    repository = InMemorySupportRepository()
    repository.tickets = {ticket.id: ticket for ticket in (_support_ticket(1), _support_ticket(2), _support_ticket(3), _support_ticket(4))}

    first, first_cursor = _support_page(repository, None)
    second, second_cursor = _support_page(repository, first_cursor)

    assert [ticket.id for ticket in first + second] == [_uuid(4), _uuid(3), _uuid(2), _uuid(1)]
    assert first_cursor is not None
    assert second_cursor is None


@pytest.mark.parametrize(
    "repository_kind",
    [
        "support",
        "orders",
        "admin_orders",
        "disputes",
        "admin_businesses",
        "admin_users",
        "admin_audit",
        "admin_credits",
        "admin_jobs",
        "admin_notifications",
    ],
)
def test_invalid_cursor_fails_cleanly(repository_kind: str) -> None:
    support = InMemorySupportRepository()
    support.tickets[_uuid(1)] = _support_ticket(1)
    orders = InMemoryOrderRepository()
    orders.orders[_uuid(1)] = _order(1)
    disputes = InMemoryDisputeRepository()
    disputes.disputes[_uuid(1)] = _dispute(1)
    admin = _admin_repository()
    admin._orders = orders  # type: ignore[attr-defined]
    admin._disputes = disputes  # type: ignore[attr-defined]
    admin._businesses.businesses[_uuid(2)] = _business(2)  # type: ignore[attr-defined]
    admin._users._users_by_id[_uuid(2)] = _user(2)  # type: ignore[attr-defined]
    admin._audit.events.append(_audit_event(2))  # type: ignore[attr-defined]
    credits = InMemoryCreditRepository(ad_repository=SimpleNamespace(ledger={}), business_repository=SimpleNamespace())
    credits.purchases[_uuid(2)] = _credit_purchase(2)
    jobs = InMemoryJobRepository()
    jobs.job_runs[_uuid(2)] = _job_run(2)
    notifications = InMemoryAdminNotificationRepository()
    notifications.notifications[_uuid(2)] = _admin_notification(2)
    calls = {
        "support": lambda: _support_page(support, "not-a-cursor"),
        "orders": lambda: orders.list_for_remitter(remitter_user_id=_uuid(100), status=None, cursor="not-a-cursor", limit=2),
        "admin_orders": lambda: admin.list_orders(status=None, business_id=None, remitter_user_id=None, cursor="not-a-cursor", limit=2),
        "disputes": lambda: disputes.list_disputes(status=None, cursor="not-a-cursor", limit=2),
        "admin_businesses": lambda: admin.list_businesses(verification_status=None, risk_level=None, business_id=None, business_name=None, cursor="not-a-cursor", limit=2),
        "admin_users": lambda: admin.list_users(phone=None, telegram_id=None, username=None, role=None, status=None, cursor="not-a-cursor", limit=2, full_sensitive=False),
        "admin_audit": lambda: admin.list_audit_logs(event_type=None, actor_user_id=None, resource_type=None, resource_id=None, cursor="not-a-cursor", limit=2),
        "admin_credits": lambda: credits.list_purchases(status=None, business_id=None, cursor="not-a-cursor", limit=2),
        "admin_jobs": lambda: jobs.list_job_runs(job_type=None, status=None, cursor="not-a-cursor", limit=2),
        "admin_notifications": lambda: notifications.list_notifications(status=None, priority=None, cursor="not-a-cursor", limit=2),
    }

    with pytest.raises(ApiError) as exc_info:
        calls[repository_kind]()

    assert exc_info.value.code == "PAGINATION_CURSOR_INVALID"
    assert exc_info.value.status_code == 400


def test_structurally_valid_cursor_rejects_non_uuid_id() -> None:
    cursor = encode_keyset_cursor(TIED_AT, "not-a-uuid")

    with pytest.raises(ApiError) as exc_info:
        decode_keyset_cursor(cursor)

    assert exc_info.value.code == "PAGINATION_CURSOR_INVALID"
    assert exc_info.value.status_code == 400
