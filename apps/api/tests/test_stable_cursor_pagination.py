from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.errors import ApiError
from app.modules.admin.memory_repository import InMemoryAdminRepository
from app.modules.disputes.memory_repository import InMemoryDisputeRepository
from app.modules.disputes.models import DisputeRecord
from app.modules.orders.memory_repository import InMemoryOrderRepository
from app.modules.orders.models import OrderRecord
from app.modules.support.memory_repository import InMemorySupportRepository
from app.modules.support.models import SupportTicketRecord
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


def test_next_cursor_is_absent_when_final_page_exactly_matches_limit() -> None:
    repository = InMemorySupportRepository()
    repository.tickets = {ticket.id: ticket for ticket in (_support_ticket(1), _support_ticket(2), _support_ticket(3), _support_ticket(4))}

    first, first_cursor = _support_page(repository, None)
    second, second_cursor = _support_page(repository, first_cursor)

    assert [ticket.id for ticket in first + second] == [_uuid(4), _uuid(3), _uuid(2), _uuid(1)]
    assert first_cursor is not None
    assert second_cursor is None


@pytest.mark.parametrize("repository_kind", ["support", "orders", "admin_orders", "disputes"])
def test_invalid_cursor_fails_cleanly(repository_kind: str) -> None:
    support = InMemorySupportRepository()
    support.tickets[_uuid(1)] = _support_ticket(1)
    orders = InMemoryOrderRepository()
    orders.orders[_uuid(1)] = _order(1)
    disputes = InMemoryDisputeRepository()
    disputes.disputes[_uuid(1)] = _dispute(1)
    admin = InMemoryAdminRepository(
        users=SimpleNamespace(users={}),
        businesses=SimpleNamespace(businesses={}),
        orders=orders,
        disputes=disputes,
        credits=SimpleNamespace(purchases={}),
        audit_writer=SimpleNamespace(events=[]),
    )
    calls = {
        "support": lambda: _support_page(support, "not-a-cursor"),
        "orders": lambda: orders.list_for_remitter(remitter_user_id=_uuid(100), status=None, cursor="not-a-cursor", limit=2),
        "admin_orders": lambda: admin.list_orders(status=None, business_id=None, remitter_user_id=None, cursor="not-a-cursor", limit=2),
        "disputes": lambda: disputes.list_disputes(status=None, cursor="not-a-cursor", limit=2),
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
