from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from app.modules.jobs import worker as worker_module
from test_jobs_notifications import _client, _headers, _login

ENDPOINT = "/api/v1/admin/jobs/expire-and-escalate-orders/dry-run"
FROZEN_TIME = datetime(2026, 9, 29, 4, 0, tzinfo=timezone.utc)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(os, "environ", os.environ.copy())
    monkeypatch.setattr(worker_module, "utc_now", lambda: FROZEN_TIME)
    return _client()


def _actor(client, role="admin"):
    login = _login(client, 23001, "hygiene_fixture")
    client.app.state.user_repository.set_user_role(login["user"]["id"], role)
    return login


def _dry_run_events(client):
    return [
        event
        for event in client.app.state.audit_writer.events
        if event.event_type == "job_dry_run_executed"
    ]


@pytest.mark.parametrize("role", ["admin", "super_admin"])
@pytest.mark.parametrize(
    "current_time",
    [
        None,
        FROZEN_TIME,
        FROZEN_TIME.astimezone(timezone(timedelta(hours=-4))),
        FROZEN_TIME - timedelta(days=30),
        FROZEN_TIME + timedelta(days=30),
    ],
)
def test_dry_run_audits_effective_time_once_on_replay(client, current_time, role):
    actor = _actor(client, role)
    params = {"current_time": current_time.isoformat()} if current_time else {}
    response = client.post(
        ENDPOINT, headers=_headers(actor, "hygiene_time"), params=params
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["job_run"]["status"] == "skipped"
    assert result["job_run"]["started_at"] == (current_time or FROZEN_TIME).isoformat()
    events = _dry_run_events(client)
    assert len(events) == 1
    event = events[0]
    assert event.metadata_json == {
        "job_type": "expire_and_escalate_orders",
        "current_time": result["job_run"]["started_at"],
    }
    assert event.actor_user_id == actor["user"]["id"]
    assert event.actor_role == role
    assert event.resource_id == result["job_run"]["id"]
    assert event.request_id == "req_hygiene_time"

    replay = client.post(
        ENDPOINT, headers=_headers(actor, "hygiene_time"), params=params
    )
    assert replay.status_code == 200
    assert replay.json()["data"] == result
    assert _dry_run_events(client) == events
    assert len(client.app.state.job_repository.job_runs) == 1
    assert not client.app.state.job_repository.notification_jobs

    changed_time = (current_time or FROZEN_TIME) + timedelta(seconds=1)
    mismatch = client.post(
        ENDPOINT,
        headers=_headers(actor, "hygiene_time"),
        params={"current_time": changed_time.isoformat()},
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"
    assert _dry_run_events(client) == events
    assert len(client.app.state.job_repository.job_runs) == 1


@pytest.mark.parametrize("status", ["lock_not_acquired", "failed"])
def test_dry_run_audit_time_is_preserved_on_worker_failure(client, monkeypatch, status):
    actor = _actor(client)
    if status == "lock_not_acquired":
        assert client.app.state.job_lock_manager.acquire(
            "jobs:expire_and_escalate_orders", "synthetic_lock_owner", 300
        )
    else:

        def fail_processing(**kwargs):
            raise RuntimeError("synthetic_private_error_not_for_audit")

        monkeypatch.setattr(
            client.app.state.expire_and_escalate_orders_worker,
            "_process_all",
            fail_processing,
        )
    response = client.post(ENDPOINT, headers=_headers(actor, "hygiene_failure"))
    assert response.status_code == 200
    run = response.json()["data"]["job_run"]
    assert run["status"] == status
    events = _dry_run_events(client)
    assert len(events) == 1
    assert events[0].resource_id == run["id"]
    assert events[0].metadata_json == {
        "job_type": "expire_and_escalate_orders",
        "current_time": FROZEN_TIME.isoformat(),
    }
    assert "synthetic_private_error_not_for_audit" not in response.text
    assert not client.app.state.job_repository.notification_jobs


@pytest.mark.parametrize("role", ["support", "remitter", "business_owner"])
def test_dry_run_still_denies_other_roles_without_run_or_audit(client, role):
    actor = _actor(client, role)
    response = client.post(ENDPOINT, headers=_headers(actor, "hygiene_forbidden"))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert not _dry_run_events(client)
    assert not client.app.state.job_repository.job_runs


def test_dry_run_still_requires_idempotency_key(client):
    actor = _actor(client)
    headers = _headers(actor)
    del headers["Idempotency-Key"]
    response = client.post(ENDPOINT, headers=headers)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert not _dry_run_events(client)
    assert not client.app.state.job_repository.job_runs


@pytest.mark.parametrize(
    "order_id", ["not-a-uuid", "null", "00000000-0000-0000-0000-invalid"]
)
def test_invalid_payment_report_order_id_still_returns_not_found(client, order_id):
    actor = _actor(client, "remitter")
    events_before = list(client.app.state.audit_writer.events)
    response = client.post(
        f"/api/v1/orders/{order_id}/payment-report",
        headers=_headers(actor, "hygiene_invalid_order"),
        json={"payment_type": "zelle", "payment_amount": "50.00"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ORDER_NOT_FOUND"
    assert client.app.state.audit_writer.events == events_before


@pytest.mark.parametrize("template", [".env.example", ".env.staging.example"])
def test_backend_credential_examples_remain_empty_and_private(template):
    source = (
        Path(__file__)
        .resolve()
        .parents[3]
        .joinpath(template)
        .read_text(encoding="utf-8")
    )
    entries = {}
    for line in source.splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            assert key not in entries
            entries[key] = value
    for key in ("SUPABASE_SERVICE_ROLE_KEY", "BASE_RPC_API_KEY", "SUPABASE_URL"):
        assert key in entries
        assert entries[key] == ""
    assert "NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY" not in entries
    assert "NEXT_PUBLIC_BASE_RPC_API_KEY" not in entries
