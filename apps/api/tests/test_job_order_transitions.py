from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from app.core.errors import ApiError
from app.modules.business_capacity.memory_repository import (
    InMemoryBusinessCapacityRepository,
)
from app.modules.businesses.models import BusinessRecord
from app.modules.disputes.memory_repository import InMemoryDisputeRepository
from app.modules.disputes.models import DisputeRecord
from app.modules.jobs.order_expiration_processor import OrderExpirationProcessor
from app.modules.jobs.worker_support import JobCounters
from app.modules.orders.memory_repository import InMemoryOrderRepository
from app.modules.orders.models import OrderRecord
from app.modules.orders.postgres_repository import PostgresOrderRepository
from app.shared.audit.audit_service import InMemoryAuditWriter
from app.shared.db import connection

NOW = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
DISPUTE_CASES = {
    "payment_reported": (
        "business_response_deadline_at",
        "business_no_payment_confirmation",
    ),
    "payment_confirmed": (
        "delivery_deadline_at",
        "business_confirmed_payment_but_not_delivered",
    ),
}


def make_lab(status="delivered"):
    business = BusinessRecord(
        id="business",
        owner_user_id="owner",
        business_name="Fictitious",
        rif=None,
        address=None,
        phone=None,
        verification_status="approved",
    )
    capacity = InMemoryBusinessCapacityRepository(
        default_declared_capacity_usd=Decimal(1000)
    )
    disputes = InMemoryDisputeRepository()
    audit = InMemoryAuditWriter()
    orders = InMemoryOrderRepository(
        capacity_repository=capacity,
        dispute_repository=disputes,
        audit_writer=audit,
    )
    order = OrderRecord(
        id="order",
        public_order_code="NODO-TEST",
        business_id=business.id,
        remitter_user_id="client",
        ad_id="ad",
        status=status,
        idempotency_key=None,
        amount_usd=Decimal(50),
        rate_snapshot=Decimal(40),
        amount_bs_calculated=Decimal(2000),
        business_name_snapshot="Fictitious",
        payment_method_snapshot="zelle",
        delivery_method_snapshot="pago_movil_ve",
        min_amount_snapshot=Decimal(20),
        max_amount_snapshot=Decimal(100),
        payment_instructions_snapshot={},
        receiver_data_json={},
        payment_report_deadline_at=NOW,
        expires_at=NOW,
        auto_complete_at=NOW,
        business_response_deadline_at=NOW,
        delivery_deadline_at=NOW,
    )
    orders.orders[order.id] = order
    capacity.reserve(
        order_id=order.id, business=business, amount_usd=order.amount_usd, reason="test"
    )
    notify = Mock(return_value=True)
    processor = OrderExpirationProcessor(
        order_repository=orders,
        ad_repository=Mock(),
        business_repository=SimpleNamespace(get_business=lambda _: business),
        dispute_repository=disputes,
        audit_writer=audit,
        notify=notify,
        state_event=Mock(),
        audit_notification=Mock(),
    )
    return SimpleNamespace(
        order=order,
        orders=orders,
        disputes=disputes,
        audit=audit,
        capacity=capacity,
        processor=processor,
        notify=notify,
    )


def process(lab, snapshot, *, dry_run=False):
    counters = JobCounters()
    arguments = {
        "now": NOW,
        "dry_run": dry_run,
        "request_id": "synthetic-job",
        "counters": counters,
    }
    if snapshot.status == "delivered":
        lab.processor._auto_complete_delivered_order(
            snapshot, open_dispute_order_ids=set(), **arguments
        )
    else:
        _, reason = DISPUTE_CASES[snapshot.status]
        lab.processor._open_dispute(
            snapshot, reason=reason, event_type=f"order_disputed_{reason}", **arguments
        )
    return counters


@pytest.mark.parametrize("original", ["delivered", *DISPUTE_CASES])
@pytest.mark.parametrize(
    "new_status", ["disputed", "completed", "cancelled", "payment_rejected"]
)
def test_stale_job_does_not_change_newer_order_or_side_effects(original, new_status):
    lab = make_lab(original)
    snapshot = deepcopy(lab.order)
    lab.orders.update_order_if_status(
        lab.order.id, expected_status=original, status=new_status
    )

    result = process(lab, snapshot)

    assert lab.order.status == new_status
    assert lab.capacity.get_reservation(lab.order.id).status == "reserved"
    assert not lab.disputes.disputes
    assert not lab.orders.events
    assert not lab.audit.events
    lab.notify.assert_not_called()
    assert (result.changed, result.skipped) == (0, 1)


@pytest.mark.parametrize("status", ["delivered", *DISPUTE_CASES])
@pytest.mark.parametrize("deadline", [None, NOW + timedelta(hours=1)])
def test_job_rechecks_current_deadline(status, deadline):
    lab = make_lab(status)
    snapshot = deepcopy(lab.order)
    field = "auto_complete_at" if status == "delivered" else DISPUTE_CASES[status][0]
    setattr(lab.order, field, deadline)

    result = process(lab, snapshot)

    assert lab.order.status == status
    assert not lab.disputes.disputes
    assert lab.capacity.get_reservation(lab.order.id).status == "reserved"
    assert not lab.audit.events
    lab.notify.assert_not_called()
    assert (result.changed, result.skipped) == (0, 1)


@pytest.mark.parametrize("dispute_status", ["open", "in_review"])
def test_completion_rechecks_dispute_after_batch_lookup(dispute_status):
    lab = make_lab()
    snapshot = deepcopy(lab.order)
    dispute = lab.disputes.create_dispute(
        order_id=lab.order.id,
        opened_by_user_id="client",
        opened_by_role="remitter",
        previous_order_status="delivered",
        reason="other",
        description="Fictitious",
    )
    lab.disputes.update_dispute(dispute, status=dispute_status)

    result = process(lab, snapshot)

    assert lab.order.status == "delivered"
    assert lab.capacity.get_reservation(lab.order.id).status == "reserved"
    assert not lab.audit.events
    lab.notify.assert_not_called()
    assert (result.changed, result.skipped) == (0, 1)


@pytest.mark.parametrize("status", ["delivered", *DISPUTE_CASES])
def test_concurrent_jobs_apply_transition_and_audit_once(status):
    lab = make_lab(status)
    snapshot = deepcopy(lab.order)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda _: process(lab, deepcopy(snapshot)), range(2))
        )

    assert sum(result.changed for result in results) == 1
    assert sum(result.skipped for result in results) == 1
    assert len(lab.orders.events) == 1
    if status == "delivered":
        assert lab.order.status == "completed"
        assert lab.order.completion_reason == "auto_completed_after_24h"
        assert lab.order.completed_at == NOW
        assert lab.capacity.get_reservation(lab.order.id).status == "consumed"
        assert lab.capacity.declared_capacity_usd(business_id="business") == Decimal(
            950
        )
        assert sorted(event.event_type for event in lab.audit.events) == [
            "business_capacity_consumed",
            "order_auto_completed_after_24h",
        ]
        assert lab.notify.call_count == 2
    else:
        assert lab.order.status == "disputed"
        assert len(lab.disputes.disputes) == len(lab.disputes.events) == 1
        dispute = next(iter(lab.disputes.disputes.values()))
        assert dispute.previous_order_status == status
        assert dispute.reason == DISPUTE_CASES[status][1]
        assert lab.capacity.get_reservation(lab.order.id).status == "reserved"
        assert [event.event_type for event in lab.audit.events] == [
            f"order_disputed_{dispute.reason}"
        ]
        assert lab.notify.call_count == 4


@pytest.mark.parametrize("status", ["delivered", *DISPUTE_CASES])
def test_dry_run_does_not_mutate_or_notify(status):
    lab = make_lab(status)
    result = process(lab, deepcopy(lab.order), dry_run=True)
    assert lab.order.status == status
    assert not lab.orders.events and not lab.disputes.disputes and not lab.audit.events
    assert lab.capacity.get_reservation(lab.order.id).status == "reserved"
    lab.notify.assert_not_called()
    assert result.changed == 1


@pytest.mark.parametrize(
    "original,new_status",
    [
        ("payment_reported", "payment_confirmed"),
        ("payment_confirmed", "delivered"),
    ],
)
def test_stale_deadline_does_not_escalate_a_later_stage(original, new_status):
    lab = make_lab(original)
    snapshot = deepcopy(lab.order)
    lab.orders.update_order_if_status(
        lab.order.id, expected_status=original, status=new_status
    )
    result = process(lab, snapshot)
    assert lab.order.status == new_status
    assert not lab.disputes.disputes and not lab.audit.events
    lab.notify.assert_not_called()
    assert (result.changed, result.skipped) == (0, 1)


def test_manual_completion_keeps_ownership_and_does_not_require_auto_deadline():
    lab = make_lab()
    lab.order.auto_complete_at = NOW + timedelta(hours=24)
    arguments = {
        "order_id": "order",
        "completed_at": NOW,
        "request_id": "manual",
        "event_metadata": {},
        "audit_metadata": {},
    }
    with pytest.raises(ApiError) as denied:
        lab.orders.confirm_received_atomically(
            remitter_user_id="different-client", **arguments
        )
    assert denied.value.code == "ORDER_NOT_FOUND"
    assert lab.capacity.get_reservation("order").status == "reserved"
    result = lab.orders.confirm_received_atomically(
        remitter_user_id="client", **arguments
    )
    assert result.completion_reason == "manual_confirmed"
    assert lab.capacity.declared_capacity_usd(business_id="business") == Decimal(950)
    event = lab.orders.events[0]
    assert (event.event_type, event.actor_user_id, event.actor_role) == (
        "order_completed",
        "client",
        "remitter",
    )


def test_failed_atomic_transition_does_not_notify(monkeypatch):
    lab = make_lab("payment_reported")
    monkeypatch.setattr(
        lab.orders,
        "open_overdue_dispute_atomically",
        Mock(side_effect=RuntimeError("synthetic")),
    )
    with pytest.raises(RuntimeError, match="synthetic"):
        process(lab, deepcopy(lab.order))
    lab.notify.assert_not_called()


def make_postgres_lab(
    monkeypatch, status, *, fault=None, existing_dispute=False, missing=False
):
    lab = make_lab(status)
    row = asdict(lab.order)
    row["paid_reported_at"] = NOW - timedelta(hours=24)
    conn = Mock(closed=False)
    pool = SimpleNamespace(acquire=lambda: conn, release=Mock())
    monkeypatch.setattr(connection, "_pool_for", lambda _: pool)
    capacity = Mock()
    capacity.transition_in_transaction.return_value = fault != "capacity"
    repository = PostgresOrderRepository(
        "synthetic-job-transaction", capacity_repository=capacity
    )

    def execute(sql, parameters):
        normalized = " ".join(sql.split())
        if fault and normalized.startswith(fault):
            raise RuntimeError("synthetic database failure")
        result = None
        if normalized.startswith("select * from orders"):
            assert "for update" in normalized
            result = None if missing else deepcopy(row)
        elif normalized.startswith(
            ("select id from disputes", "select 1 from disputes")
        ):
            assert "status in ('open', 'in_review')" in normalized
            result = {"id": "existing"} if existing_dispute else None
        elif normalized.startswith("insert into disputes"):
            result = asdict(
                DisputeRecord(
                    id="dispute",
                    order_id=parameters[0],
                    opened_by_user_id=parameters[1],
                    opened_by_role="remitter",
                    previous_order_status=parameters[2],
                    reason=parameters[3],
                    description=parameters[4],
                )
            )
        elif normalized.startswith("update orders"):
            if fault == "conditional_update":
                return SimpleNamespace(fetchone=lambda: None)
            result = deepcopy(row)
            if status == "delivered":
                assert "where id = %s and status = 'delivered'" in normalized
                result.update(
                    status="completed",
                    completion_reason=parameters[0],
                    completed_at=parameters[1],
                )
            else:
                assert "where id = %s and status = %s" in normalized
                assert parameters[2] == status
                result.update(status="disputed", dispute_reason=parameters[0])
        else:
            assert normalized.startswith(
                (
                    "update businesses",
                    "insert into dispute_events",
                    "insert into order_state_events",
                    "insert into audit_logs",
                )
            ), normalized
        return SimpleNamespace(fetchone=lambda: result)

    conn.execute.side_effect = execute
    lab.processor._orders = repository
    return SimpleNamespace(
        conn=conn,
        pool=pool,
        repository=repository,
        capacity=capacity,
        row=row,
        source=lab,
    )


@pytest.mark.parametrize("status", ["delivered", *DISPUTE_CASES])
@pytest.mark.parametrize(
    "guard", ["missing", "new_status", "no_deadline", "future_deadline", "dispute"]
)
def test_postgres_rechecks_locked_state_before_any_write(monkeypatch, status, guard):
    pg = make_postgres_lab(
        monkeypatch,
        status,
        missing=guard == "missing",
        existing_dispute=guard == "dispute",
    )
    field = "auto_complete_at" if status == "delivered" else DISPUTE_CASES[status][0]
    if guard == "new_status":
        pg.row["status"] = "disputed"
    elif guard == "no_deadline":
        pg.row[field] = None
    elif guard == "future_deadline":
        pg.row[field] = NOW + timedelta(seconds=1)
    result = process(pg.source, deepcopy(pg.source.order))
    assert (result.changed, result.skipped) == (0, 1)
    assert all(
        call.args[0].lstrip().startswith("select")
        for call in pg.conn.execute.call_args_list
    )
    pg.capacity.transition_in_transaction.assert_not_called()
    pg.source.notify.assert_not_called()
    pg.pool.release.assert_called_once_with(pg.conn)


@pytest.mark.parametrize("status", ["delivered", *DISPUTE_CASES])
def test_postgres_state_and_audit_share_one_transaction(monkeypatch, status):
    pg = make_postgres_lab(monkeypatch, status)
    result = process(pg.source, deepcopy(pg.source.order))
    assert (result.changed, result.skipped) == (1, 0)
    statements = [
        " ".join(call.args[0].split()) for call in pg.conn.execute.call_args_list
    ]
    assert statements[0] == "select * from orders where id = %s for update"
    assert sum(sql.startswith("update orders") for sql in statements) == 1
    assert (
        sum(sql.startswith("insert into order_state_events") for sql in statements) == 1
    )
    assert not any("credit_ledger" in sql or "update ads" in sql for sql in statements)
    calls = pg.conn.mock_calls
    first_commit = next(
        index for index, call in enumerate(calls) if call[0] == "commit"
    )
    assert not any(call[0] == "execute" for call in calls[first_commit + 1 :])
    pg.conn.rollback.assert_not_called()
    pg.pool.release.assert_called_once_with(pg.conn)
    if status == "delivered":
        pg.capacity.transition_in_transaction.assert_called_once_with(
            pg.conn,
            order_id="order",
            target_status="consumed",
            reason="auto_completed_after_24h",
        )
        assert sum(sql.startswith("update businesses") for sql in statements) == 1
        assert sum(sql.startswith("insert into audit_logs") for sql in statements) == 2
    else:
        pg.capacity.transition_in_transaction.assert_not_called()
        assert sum(sql.startswith("insert into disputes") for sql in statements) == 1
        assert (
            sum(sql.startswith("insert into dispute_events") for sql in statements) == 1
        )
        assert sum(sql.startswith("insert into audit_logs") for sql in statements) == 1


@pytest.mark.parametrize(
    "status,fault",
    [
        (status, fault)
        for status in ("delivered", *DISPUTE_CASES)
        for fault in (
            "conditional_update",
            "insert into order_state_events",
            "insert into audit_logs",
        )
    ]
    + [("delivered", "capacity"), ("delivered", "update businesses")]
    + [(status, "insert into dispute_events") for status in DISPUTE_CASES],
)
def test_postgres_failure_rolls_back_and_never_notifies(monkeypatch, status, fault):
    pg = make_postgres_lab(monkeypatch, status, fault=fault)
    with pytest.raises((ApiError, RuntimeError)):
        process(pg.source, deepcopy(pg.source.order))
    pg.conn.commit.assert_not_called()
    pg.conn.rollback.assert_called_once()
    pg.pool.release.assert_called_once_with(pg.conn)
    pg.source.notify.assert_not_called()
