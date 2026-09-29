from concurrent.futures import ThreadPoolExecutor
from copy import copy, deepcopy
from dataclasses import asdict
from datetime import timedelta
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from app.core.errors import ApiError
from app.modules.disputes.models import DisputeRecord
from app.modules.disputes.schemas import DisputeCreateRequest
from app.modules.disputes.service import DisputeService
from app.modules.orders.postgres_repository import PostgresOrderRepository
from app.modules.orders.remitter_ops import OrderRemitterOps
from app.modules.orders.state_machine import now_utc
from app.modules.users.models import UserRecord
from app.shared.db import connection
from app.shared.idempotency.store import InMemoryIdempotencyStore
from test_job_order_transitions import make_lab


def participant_lab(status="payment_confirmed"):
    lab = make_lab(status)
    lab.order.id = str(uuid4())
    lab.orders.orders = {lab.order.id: lab.order}
    reservation = lab.capacity.reservations.pop("order")
    reservation.order_id = lab.order.id
    lab.capacity.reservations[lab.order.id] = reservation
    lab.order.payment_report_deadline_at = now_utc() + timedelta(minutes=15)
    lab.order.expires_at = lab.order.payment_report_deadline_at
    lab.user = UserRecord("client", None, None, None, None)
    lab.notifications = Mock()
    lab.service = DisputeService(
        settings=SimpleNamespace(
            business_rate_limit_max_attempts=100,
            business_rate_limit_window_seconds=60,
        ),
        repository=lab.disputes,
        order_repository=lab.orders,
        chat_repository=Mock(),
        business_repository=SimpleNamespace(
            get_business=lambda _: SimpleNamespace(owner_user_id="owner")
        ),
        ad_repository=Mock(),
        audit_writer=lab.audit,
        rate_limiter=SimpleNamespace(allow=lambda *a, **kw: True),
        idempotency_store=InMemoryIdempotencyStore(),
        notification_service=lab.notifications,
    )
    lab.remitter = OrderRemitterOps(
        repository=lab.orders,
        ad_repository=Mock(),
        audit_writer=lab.audit,
        idempotency_store=InMemoryIdempotencyStore(),
        rate_limit=lambda *a: None,
        materialize_order_expiration=lambda order, **kw: order,
        return_or_expire_ad=Mock(),
        clear_marketplace_cache=Mock(),
        rating_ops=Mock(),
    )
    return lab


def open_dispute(lab, key="open"):
    return lab.service.open_dispute(
        user=lab.user,
        order_id=lab.order.id,
        payload=DisputeCreateRequest(reason="other", description="Synthetic"),
        request_id=key,
        idempotency_key=key,
    )


def extend(lab, key="extend"):
    return lab.remitter.extend(
        user=lab.user,
        order_id=lab.order.id,
        payload=None,
        request_id=key,
        idempotency_key=key,
    )


def test_generic_dispute_creation_failure_preserves_order(monkeypatch):
    lab = participant_lab()
    before = deepcopy(lab.order)
    monkeypatch.setattr(
        lab.disputes, "create_dispute", Mock(side_effect=RuntimeError("synthetic"))
    )
    with pytest.raises(RuntimeError, match="synthetic"):
        open_dispute(lab)
    assert lab.order == before
    assert lab.disputes.disputes == {}
    assert lab.disputes.events == []
    assert lab.orders.events == []
    assert lab.audit.events == []
    lab.notifications.order_disputed_parties_admin.assert_not_called()


def test_concurrent_extensions_with_stale_reads_only_apply_once(monkeypatch):
    lab = participant_lab("waiting_payment")
    barrier = Barrier(2)
    snapshot = deepcopy(lab.order)

    def stale_read(_):
        barrier.wait(timeout=5)
        return deepcopy(snapshot)

    monkeypatch.setattr(lab.orders, "get_by_id", stale_read)

    def request(key):
        worker = copy(lab)
        worker.remitter = copy(lab.remitter)
        worker.remitter._idempotency = InMemoryIdempotencyStore()
        try:
            extend(worker, key)
            return "ok"
        except ApiError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(request, ["first", "second"]))
    assert sorted(results) == ["ORDER_EXTENSION_ALREADY_USED", "ok"]
    assert lab.order.extension_used is True
    assert (
        lab.order.payment_report_deadline_at
        == snapshot.payment_report_deadline_at + timedelta(minutes=15)
    )
    assert len(lab.orders.events) == len(lab.audit.events) == 1


@pytest.mark.parametrize(
    "status", ["payment_reported", "payment_rejected", "payment_confirmed", "delivered"]
)
def test_generic_dispute_is_idempotent_and_preserves_resources(status):
    lab = participant_lab(status)
    capacity_before = deepcopy(lab.capacity.reservations)
    result = open_dispute(lab)
    assert open_dispute(lab) == result
    assert lab.order.status == "disputed"
    assert result["dispute"]["previous_order_status"] == status
    assert len(lab.disputes.disputes) == 1
    assert (
        len(lab.orders.events) == len(lab.disputes.events) == len(lab.audit.events) == 1
    )
    assert lab.disputes.events[0].metadata_json == {
        "previous_order_status": status,
        "evidence_file_ids": [],
    }
    assert lab.audit.events[0].metadata_json["new_order_status"] == "disputed"
    lab.notifications.order_disputed_parties_admin.assert_called_once()
    assert lab.capacity.reservations == capacity_before


@pytest.mark.parametrize(
    "stage", ["create_dispute", "dispute_event", "order_event", "audit"]
)
def test_generic_dispute_rolls_back_failure_after_each_write(monkeypatch, stage):
    lab = participant_lab()
    before = deepcopy(lab.order)
    target, method = {
        "create_dispute": (lab.disputes, "create_dispute"),
        "dispute_event": (lab.disputes, "add_event"),
        "order_event": (lab.orders, "add_state_event"),
        "audit": (lab.audit, "write"),
    }[stage]
    original = getattr(target, method)

    def fail_after_write(**kwargs):
        original(**kwargs)
        raise RuntimeError("synthetic")

    monkeypatch.setattr(target, method, fail_after_write)
    with pytest.raises(RuntimeError, match="synthetic"):
        open_dispute(lab)
    assert lab.order == before
    assert lab.disputes.disputes == {}
    assert lab.orders.events == lab.disputes.events == lab.audit.events == []
    lab.notifications.order_disputed_parties_admin.assert_not_called()


@pytest.mark.parametrize("status", ["completed", "cancelled"])
def test_generic_dispute_rechecks_stale_state(monkeypatch, status):
    lab = participant_lab()
    snapshot = deepcopy(lab.order)
    lab.order.status = status
    monkeypatch.setattr(lab.orders, "get_by_id", lambda _: snapshot)
    with pytest.raises(ApiError) as caught:
        open_dispute(lab)
    assert caught.value.code == "ORDER_STATE_CONFLICT"
    assert lab.order.status == status
    assert lab.disputes.disputes == {}
    assert lab.audit.events == lab.orders.events == []


@pytest.mark.parametrize(
    "change,error",
    [
        ({"status": "payment_confirmed"}, "ORDER_STATUS_INVALID"),
        ({"status": "cancelled"}, "ORDER_STATUS_INVALID"),
        ({"extension_used": True}, "ORDER_EXTENSION_ALREADY_USED"),
        ({"paid_reported_at": "now"}, "ORDER_PAYMENT_ALREADY_REPORTED"),
        ({"payment_report_deadline_at": "expired"}, "ORDER_EXPIRED"),
        ({"remitter_user_id": "someone-else"}, "ORDER_NOT_FOUND"),
    ],
)
def test_extension_rechecks_current_order_after_stale_read(monkeypatch, change, error):
    lab = participant_lab("waiting_payment")
    snapshot = deepcopy(lab.order)
    for key, value in change.items():
        if value == "now":
            value = now_utc()
        elif value == "expired":
            value = now_utc() - timedelta(seconds=1)
        setattr(lab.order, key, value)
    before = deepcopy(lab.order)
    monkeypatch.setattr(lab.orders, "get_by_id", lambda _: snapshot)
    with pytest.raises(ApiError) as caught:
        extend(lab)
    assert caught.value.code == error
    assert lab.order == before
    assert lab.audit.events == lab.orders.events == []


@pytest.mark.parametrize("stage", ["order_event", "audit"])
def test_extension_failure_does_not_consume_one_time_use(monkeypatch, stage):
    lab = participant_lab("waiting_payment")
    before = deepcopy(lab.order)
    target, method = (
        (lab.orders, "add_state_event")
        if stage == "order_event"
        else (lab.audit, "write")
    )
    original = getattr(target, method)

    def fail_after_write(**kwargs):
        original(**kwargs)
        raise RuntimeError("synthetic")

    monkeypatch.setattr(target, method, fail_after_write)
    with pytest.raises(RuntimeError, match="synthetic"):
        extend(lab)
    assert lab.order == before
    assert lab.audit.events == lab.orders.events == []
    monkeypatch.setattr(target, method, original)
    result = extend(lab)
    assert extend(lab) == result
    assert len(lab.orders.events) == len(lab.audit.events) == 1


def postgres_lab(monkeypatch, operation, *, fault=None):
    lab = participant_lab(
        "waiting_payment" if operation == "extend" else "payment_confirmed"
    )
    row = asdict(lab.order)
    row["dispute_business_owner_id"] = "owner"
    conn = Mock(closed=False)
    pool = SimpleNamespace(acquire=lambda: conn, release=Mock())
    monkeypatch.setattr(connection, "_pool_for", lambda _: pool)
    repository = PostgresOrderRepository("synthetic-participant-transaction")

    def execute(sql, params):
        normalized = " ".join(sql.split())
        if fault and normalized.startswith(fault):
            raise RuntimeError("synthetic")
        result = None
        if normalized.startswith("select") and "from orders" in normalized:
            assert "for update" in normalized
            result = deepcopy(row)
        elif normalized.startswith("select id from disputes"):
            assert "status in ('open', 'in_review')" in normalized
        elif normalized.startswith("insert into disputes"):
            result = asdict(
                DisputeRecord(
                    id="dispute",
                    order_id=params[0],
                    opened_by_user_id=params[1],
                    opened_by_role=params[2],
                    previous_order_status=params[3],
                    reason=params[4],
                    description=params[5],
                )
            )
        elif normalized.startswith("update orders"):
            if fault == "conditional_update":
                return SimpleNamespace(fetchone=lambda: None)
            result = deepcopy(row)
            if operation == "extend":
                assert (
                    "status = 'waiting_payment' and extension_used = false"
                    in normalized
                )
                assert (
                    "paid_reported_at is null and payment_report_deadline_at > %s"
                    in normalized
                )
                result.update(
                    extension_used=True,
                    payment_report_extension_used_at=params[0],
                    payment_report_deadline_at=params[1],
                    expires_at=params[2],
                )
                assert params[1] == row["payment_report_deadline_at"] + timedelta(
                    minutes=15
                )
            else:
                assert "where id = %s and status = %s" in normalized
                assert params == ("other", row["id"], "payment_confirmed")
                result.update(status="disputed", dispute_reason="other")
        else:
            assert normalized.startswith(
                (
                    "insert into dispute_events",
                    "insert into order_state_events",
                    "insert into audit_logs",
                )
            )
        return SimpleNamespace(fetchone=lambda: result)

    conn.execute.side_effect = execute

    def run():
        if operation == "extend":
            return repository.extend_payment_deadline_atomically(
                order_id=lab.order.id,
                remitter_user_id="client",
                reason=None,
                request_id="synthetic",
            )
        return repository.open_participant_dispute_atomically(
            order_id=lab.order.id,
            expected_status="payment_confirmed",
            actor_user_id="client",
            actor_role="remitter",
            business_owner_user_id="owner",
            reason="other",
            description="Synthetic",
            evidence_file_ids=[],
            request_id="synthetic",
        )

    return SimpleNamespace(conn=conn, pool=pool, row=row, run=run)


@pytest.mark.parametrize("operation", ["dispute", "extend"])
def test_postgres_uses_one_commit_for_state_events_and_audit(monkeypatch, operation):
    pg = postgres_lab(monkeypatch, operation)
    pg.run()
    statements = [
        " ".join(call.args[0].split()) for call in pg.conn.execute.call_args_list
    ]
    assert sum(sql.startswith("update orders") for sql in statements) == 1
    assert (
        sum(sql.startswith("insert into order_state_events") for sql in statements) == 1
    )
    assert sum(sql.startswith("insert into audit_logs") for sql in statements) == 1
    assert sum(sql.startswith("insert into disputes") for sql in statements) == (
        operation == "dispute"
    )
    assert sum(sql.startswith("insert into dispute_events") for sql in statements) == (
        operation == "dispute"
    )
    assert not any(
        "credits_ledger" in sql or "update ads" in sql or "capacity" in sql
        for sql in statements
    )
    pg.conn.commit.assert_called_once()
    pg.conn.rollback.assert_not_called()
    assert pg.conn.mock_calls[-1][0] == "commit"
    pg.pool.release.assert_called_once_with(pg.conn)


@pytest.mark.parametrize(
    "operation,fault",
    [
        (op, fault)
        for op in ("dispute", "extend")
        for fault in (
            "conditional_update",
            "update orders",
            "insert into order_state_events",
            "insert into audit_logs",
        )
    ]
    + [
        ("dispute", fault)
        for fault in ("insert into disputes", "insert into dispute_events")
    ],
)
def test_postgres_failure_never_commits_partial_transition(
    monkeypatch, operation, fault
):
    pg = postgres_lab(monkeypatch, operation, fault=fault)
    with pytest.raises((ApiError, RuntimeError)):
        pg.run()
    pg.conn.commit.assert_not_called()
    pg.conn.rollback.assert_called_once()
    pg.pool.release.assert_called_once_with(pg.conn)


@pytest.mark.parametrize("operation", ["dispute", "extend"])
@pytest.mark.parametrize("guard", ["owner", "status"])
def test_postgres_rechecks_owner_and_state_before_writing(
    monkeypatch, operation, guard
):
    pg = postgres_lab(monkeypatch, operation)
    if guard == "owner":
        pg.row["remitter_user_id"] = "someone-else"
    else:
        pg.row["status"] = "completed"
    with pytest.raises(ApiError):
        pg.run()
    assert all(
        call.args[0].lstrip().startswith("select")
        for call in pg.conn.execute.call_args_list
    )
    pg.conn.commit.assert_not_called()


def test_concurrent_disputes_create_only_one_case_and_notification(monkeypatch):
    lab = participant_lab()
    barrier = Barrier(2)
    snapshot = deepcopy(lab.order)

    def stale_read(_):
        barrier.wait(timeout=5)
        return deepcopy(snapshot)

    monkeypatch.setattr(lab.orders, "get_by_id", stale_read)

    def request(key):
        worker = copy(lab)
        worker.service = copy(lab.service)
        worker.service._idempotency = InMemoryIdempotencyStore()
        try:
            open_dispute(worker, key)
            return "ok"
        except ApiError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(request, ["first", "second"]))
    assert sorted(results) == ["DISPUTE_ALREADY_OPEN", "ok"]
    assert lab.order.status == "disputed"
    assert len(lab.disputes.disputes) == 1
    assert (
        len(lab.orders.events) == len(lab.disputes.events) == len(lab.audit.events) == 1
    )
    lab.notifications.order_disputed_parties_admin.assert_called_once()


@pytest.mark.parametrize(
    "guard,error",
    [
        ("extension_used", "ORDER_EXTENSION_ALREADY_USED"),
        ("paid_reported_at", "ORDER_PAYMENT_ALREADY_REPORTED"),
        ("payment_report_deadline_at", "ORDER_EXPIRED"),
    ],
)
def test_postgres_extension_checks_all_locked_guards(monkeypatch, guard, error):
    pg = postgres_lab(monkeypatch, "extend")
    pg.row[guard] = (
        True if guard == "extension_used" else now_utc() - timedelta(seconds=1)
    )
    with pytest.raises(ApiError) as caught:
        pg.run()
    assert caught.value.code == error
    assert all(
        call.args[0].lstrip().startswith("select")
        for call in pg.conn.execute.call_args_list
    )
    pg.conn.commit.assert_not_called()
