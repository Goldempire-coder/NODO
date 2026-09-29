from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event, Lock

import pytest
from app.core.config import EnvValidationError, load_settings
from app.core.errors import ApiError
from app.modules.credits.service import CreditService
from app.shared.idempotency.store import (
    InMemoryIdempotencyStore,
    canonical_payload_hash,
)
from app.shared.rate_limit import in_memory
from app.shared.rate_limit.request_identity import (
    client_ip_for_rate_limit,
    current_request_ip_hash,
)
from fastapi.testclient import TestClient
from test_auth_telegram import _set_env, _signed_init_data, create_app


def test_untrusted_forwarded_header_cannot_rotate_identity() -> None:
    for address in (b"198.51.100.1", b"198.51.100.2"):
        scope = {
            "client": ("203.0.113.20", 1234),
            "headers": [(b"x-forwarded-for", address)],
        }
        assert client_ip_for_rate_limit(scope) == "203.0.113.20"


def test_idle_rate_limit_keys_are_evicted_on_next_cleanup(monkeypatch) -> None:
    monkeypatch.setattr(in_memory.time, "time", lambda: 1000.0)
    limiter = in_memory.InMemoryRateLimiter()
    for index in range(1000):
        assert limiter.allow(f"synthetic:{index}", max_attempts=1, window_seconds=60)
    monkeypatch.setattr(in_memory.time, "time", lambda: 1061.0)
    assert limiter.allow("next", max_attempts=1, window_seconds=60)
    assert set(limiter._attempts) == {"next"}


def test_idempotency_different_keys_do_not_serialize_compute() -> None:
    store = InMemoryIdempotencyStore()
    first_started, release_first, second_finished = Event(), Event(), Event()

    def first_compute():
        first_started.set()
        assert release_first.wait(5)
        return {"value": "first"}

    def second_compute():
        second_finished.set()
        return {"value": "second"}

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            store.replay_or_store, "first", payload={}, compute=first_compute
        )
        try:
            assert first_started.wait(5)
            second = pool.submit(
                store.replay_or_store, "second", payload={}, compute=second_compute
            )
            assert second_finished.wait(1)
        finally:
            release_first.set()
        assert first.result(5) == {"value": "first"}
        assert second.result(5) == {"value": "second"}


def test_auth_clients_behind_explicit_trusted_proxy_have_separate_limits(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.10/32")
    monkeypatch.setenv("AUTH_RATE_LIMIT_MAX_ATTEMPTS", "100")
    _set_env(AUTH_RATE_LIMIT_MAX_ATTEMPTS="1")
    app = create_app()
    with TestClient(app, client=("10.0.0.10", 1234)) as client:
        for address in ("198.51.100.1", "198.51.100.2"):
            response = client.post(
                "/api/v1/auth/telegram",
                json={"init_data": _signed_init_data()},
                headers={"x-forwarded-for": address},
            )
            assert response.status_code == 200
        assert (
            client.post(
                "/api/v1/auth/telegram",
                json={"init_data": _signed_init_data()},
                headers={"x-forwarded-for": "198.51.100.1"},
            ).status_code
            == 429
        )
    assert current_request_ip_hash() == "unknown"
    sessions = app.state.user_repository._sessions_by_id.values()
    assert all(s.ip_hash == hashlib.sha256(b"10.0.0.10").hexdigest() for s in sessions)
    persisted = json.dumps(
        [vars(s) for s in sessions] + [vars(e) for e in app.state.audit_writer.events],
        default=str,
    )
    for address in ("198.51.100.1", "198.51.100.2"):
        assert address not in persisted
        assert hashlib.sha256(address.encode()).hexdigest() not in persisted


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ([b"192.0.2.99, 198.51.100.44, 10.0.0.11"], "198.51.100.44"),
        ([b"192.0.2.99", b"198.51.100.44, 10.0.0.11"], "198.51.100.44"),
        ([b"198.51.100.44:443"], "198.51.100.44"),
        ([b"[2001:db8:1::5]:443"], "2001:db8:1::5"),
        ([b"2001:db8:1::5"], "2001:db8:1::5"),
        ([b"198.51.100.44, malformed, 10.0.0.11"], "10.0.0.10"),
        ([b"198.51.100.44, "], "10.0.0.10"),
        ([b"198.51.100.44, [::1]garbage"], "10.0.0.10"),
        ([b"198.51.100.44, 10.0.0.11:garbage"], "10.0.0.10"),
        ([b"198.51.100.44, 10.0.0.11:70000"], "10.0.0.10"),
        ([b"198.51.100.44, fe80::1%private"], "10.0.0.10"),
        ([b"10.0.0.11, 10.0.0.12"], "10.0.0.10"),
        ([], "10.0.0.10"),
    ],
)
def test_trusted_proxy_chain_stops_at_untrusted_or_invalid_hop(
    headers, expected
) -> None:
    scope = {
        "client": ("10.0.0.10", 1234),
        "headers": [(b"x-forwarded-for", h) for h in headers],
    }
    assert client_ip_for_rate_limit(scope, trusted_proxies=("10.0.0.0/24",)) == expected


def test_no_peer_cannot_authorize_a_forwarded_header() -> None:
    scope = {"headers": [(b"x-forwarded-for", b"198.51.100.44")]}
    assert (
        client_ip_for_rate_limit(scope, trusted_proxies=("10.0.0.0/24",)) == "unknown"
    )


def test_trusted_ipv6_proxy_is_normalized() -> None:
    scope = {
        "client": ("2001:db8::10", 1234),
        "headers": [(b"x-forwarded-for", b"198.51.100.44")],
    }
    assert (
        client_ip_for_rate_limit(scope, trusted_proxies=("2001:db8::/64",))
        == "198.51.100.44"
    )


def _settings_env(**overrides):
    return {
        "APP_ENV": "test",
        "DATABASE_URL": "synthetic",
        "REDIS_URL": "synthetic",
        **overrides,
    }


@pytest.mark.parametrize(
    "value", ["*", "0.0.0.0/0", "::/0", "proxy.invalid", "10.0.0.1/24", "not-a-network"]
)
def test_invalid_or_universal_trusted_proxy_is_rejected_without_echo(value) -> None:
    with pytest.raises(EnvValidationError) as error:
        load_settings(_settings_env(TRUSTED_PROXIES=value))
    assert error.value.missing_keys == ["TRUSTED_PROXIES"]
    assert str(error.value) == "Missing required environment keys: TRUSTED_PROXIES"


def test_proxy_settings_default_is_empty_and_explicit_networks_are_canonical() -> None:
    assert load_settings(_settings_env()).trusted_proxies == ()
    assert load_settings(
        _settings_env(TRUSTED_PROXIES="10.0.0.10, 2001:db8::/64")
    ).trusted_proxies == ("10.0.0.10/32", "2001:db8::/64")


@pytest.mark.parametrize(
    ("endpoint", "body", "prefix"),
    [
        ("telegram", {"init_data": "synthetic-invalid"}, "auth:"),
        (
            "admin/login",
            {"username": "synthetic-admin", "password": "synthetic-password"},
            "auth:admin:ip:",
        ),
        ("refresh", {"refresh_token": "synthetic-refresh"}, "auth:refresh:ip:"),
        ("logout", {"refresh_token": "synthetic-refresh"}, "auth:logout:ip:"),
    ],
)
@pytest.mark.parametrize("trusted", [False, True])
def test_all_auth_endpoints_use_shared_ephemeral_identity(
    monkeypatch, endpoint, body, prefix, trusted
) -> None:
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.10" if trusted else "")
    monkeypatch.setenv("AUTH_RATE_LIMIT_MAX_ATTEMPTS", "100")
    _set_env(AUTH_RATE_LIMIT_MAX_ATTEMPTS="1")
    app = create_app()
    with TestClient(app, client=("10.0.0.10", 1234)) as client:
        for index, address in enumerate(("198.51.100.1", "198.51.100.2")):
            request_body = (
                {**body, "username": f"synthetic-admin-{index}"}
                if endpoint == "admin/login"
                else body
            )
            response = client.post(
                "/api/v1/auth/" + endpoint,
                json=request_body,
                headers={"x-forwarded-for": address},
            )
            assert response.status_code == (
                429 if index and not trusted else 200 if endpoint == "logout" else 401
            )
        repeated = client.post(
            "/api/v1/auth/" + endpoint,
            json=body,
            headers={"x-forwarded-for": "198.51.100.1"},
        )
        assert repeated.status_code == 429
    expected = ("198.51.100.1", "198.51.100.2") if trusted else ("10.0.0.10",)
    actual = {key for key in app.state.rate_limiter._attempts if key.startswith(prefix)}
    if endpoint == "admin/login":
        # Username limiting remains independent of the IP limiter.
        assert "auth:admin:user:synthetic-admin-0" in app.state.rate_limiter._attempts
    assert actual == {
        prefix + hashlib.sha256(ip.encode()).hexdigest() for ip in expected
    }
    assert current_request_ip_hash() == "unknown"


def test_rate_limit_cleanup_preserves_live_windows_and_boundary(monkeypatch) -> None:
    monkeypatch.setattr(in_memory.time, "time", lambda: 1000.0)
    limiter = in_memory.InMemoryRateLimiter()
    assert limiter.allow("short", max_attempts=1, window_seconds=60)
    assert limiter.allow("long", max_attempts=1, window_seconds=180)
    monkeypatch.setattr(in_memory.time, "time", lambda: 1060.0)
    assert limiter.allow("short", max_attempts=1, window_seconds=60)
    assert not limiter.allow("long", max_attempts=1, window_seconds=180)
    monkeypatch.setattr(in_memory.time, "time", lambda: 1180.0)
    assert limiter.allow("long", max_attempts=1, window_seconds=180)
    assert set(limiter._attempts) == set(limiter._expires_at) == {"long"}


def test_rate_limit_cleanup_does_not_reset_recent_attempts(monkeypatch) -> None:
    monkeypatch.setattr(in_memory.time, "time", lambda: 1000.0)
    limiter = in_memory.InMemoryRateLimiter()
    assert limiter.allow("active", max_attempts=2, window_seconds=60)
    monkeypatch.setattr(in_memory.time, "time", lambda: 1050.0)
    assert limiter.allow("active", max_attempts=2, window_seconds=60)
    monkeypatch.setattr(in_memory.time, "time", lambda: 1060.0)
    assert limiter.allow("active", max_attempts=2, window_seconds=60)
    assert not limiter.allow("active", max_attempts=2, window_seconds=60)
    assert list(limiter._attempts["active"]) == [1050.0, 1060.0]


def test_same_idempotency_key_computes_once_under_contention() -> None:
    store = InMemoryIdempotencyStore()
    ready = Barrier(8)
    calls = []
    counter_lock = Lock()
    started, release = Event(), Event()

    def compute():
        with counter_lock:
            calls.append(True)
        started.set()
        assert release.wait(5)
        return {"value": "once"}

    def request():
        ready.wait(5)
        return store.replay_or_store("same", payload={"value": 1}, compute=compute)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(request) for _ in range(8)]
        try:
            assert started.wait(5)
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                with store._lock:
                    users = store._key_locks["same"].users
                if users == 8:
                    break
                Event().wait(0.005)
            assert users == 8
            assert calls == [True]
        finally:
            release.set()
        responses = [future.result(5) for future in futures]
    assert responses == [{"value": "once"}] * 8
    assert len(calls) == 1
    assert store._key_locks == {}


def test_idempotency_conflict_failure_retry_ttl_and_profile(monkeypatch) -> None:
    store = InMemoryIdempotencyStore()
    profile = []
    with pytest.raises(ApiError) as missing:
        store.replay_or_store(
            None, payload={}, compute=lambda: pytest.fail("missing key")
        )
    assert missing.value.code == "IDEMPOTENCY_KEY_REQUIRED"

    def failed_compute():
        raise ValueError("synthetic failure")

    with pytest.raises(ValueError, match="synthetic failure"):
        store.replay_or_store("retry", payload={}, compute=failed_compute)
    assert store.get("retry") is None
    assert store._key_locks == {}
    assert store.replay_or_store(
        "retry", payload={}, compute=lambda: {"ok": True}, profile=profile
    ) == {"ok": True}
    assert [item["stage"] for item in profile] == [
        "idempotency:get_existing",
        "idempotency:store_response",
    ]
    with pytest.raises(ApiError) as conflict:
        store.replay_or_store(
            "retry",
            payload={"different": True},
            compute=lambda: pytest.fail("conflict"),
        )
    assert conflict.value.code == "IDEMPOTENCY_PAYLOAD_MISMATCH"
    monkeypatch.setattr("app.shared.idempotency.store.time.time", lambda: 1000.0)
    store.put(
        "ttl",
        payload_hash=canonical_payload_hash({}),
        response={"old": True},
        ttl_seconds=1,
    )
    monkeypatch.setattr("app.shared.idempotency.store.time.time", lambda: 1001.0)
    assert store.replay_or_store("ttl", payload={}, compute=lambda: {"new": True}) == {
        "new": True
    }
    assert store._key_locks == {}


def test_idempotency_waiter_with_different_payload_cannot_compute() -> None:
    store = InMemoryIdempotencyStore()
    started, release, waiting = Event(), Event(), Event()

    def compute():
        started.set()
        assert release.wait(5)
        return {"first": True}

    def conflicting_request():
        waiting.set()
        with pytest.raises(ApiError) as conflict:
            store.replay_or_store(
                "same", payload={"other": True}, compute=lambda: pytest.fail("conflict")
            )
        assert conflict.value.code == "IDEMPOTENCY_PAYLOAD_MISMATCH"

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(store.replay_or_store, "same", payload={}, compute=compute)
        try:
            assert started.wait(5)
            second = pool.submit(conflicting_request)
            assert waiting.wait(5)
        finally:
            release.set()
        assert first.result(5) == {"first": True}
        second.result(5)
    assert store._key_locks == {}


def test_idempotency_reentrant_other_key_keeps_existing_semantics() -> None:
    store = InMemoryIdempotencyStore()
    result = store.replay_or_store(
        "outer",
        payload={},
        compute=lambda: store.replay_or_store(
            "inner", payload={}, compute=lambda: {"ok": True}
        ),
    )
    assert result == {"ok": True}
    assert store.get("outer").response == store.get("inner").response
    assert store._key_locks == {}


def test_container_startup_preserves_tcp_peer_for_application_trust_boundary() -> None:
    dockerfile = (Path(__file__).resolve().parents[3] / "Dockerfile").read_text()
    command = json.loads(
        next(line[4:] for line in dockerfile.splitlines() if line.startswith("CMD "))
    )
    assert "--no-proxy-headers" in command[-1].split()


@pytest.mark.parametrize("trusted", [False, True])
def test_credit_and_auth_limits_share_identity_without_purchases(
    monkeypatch, trusted
) -> None:
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.10" if trusted else "")
    _set_env()
    app = create_app()
    service = CreditService.__new__(CreditService)
    service._settings = app.state.settings
    service._rate_limiter = app.state.rate_limiter

    @app.get("/synthetic-limits-only")
    def synthetic_limits():
        service._contract_rate_limit("synthetic-user", "synthetic-business")
        return {"ok": True}

    with TestClient(app, client=("10.0.0.10", 1234)) as client:
        for address in ("198.51.100.1", "198.51.100.2"):
            headers = {"x-forwarded-for": address}
            assert (
                client.get("/synthetic-limits-only", headers=headers).status_code == 200
            )
            assert (
                client.post(
                    "/api/v1/auth/telegram",
                    headers=headers,
                    json={"init_data": "invalid"},
                ).status_code
                == 401
            )
    keys = set(app.state.rate_limiter._attempts)
    credit_prefix = "credits:base_usdc_contract_payment:ip:"
    credit_identities = {
        key.removeprefix(credit_prefix) for key in keys if key.startswith(credit_prefix)
    }
    auth_identities = {
        key.removeprefix("auth:") for key in keys if key.startswith("auth:")
    }
    assert credit_identities == auth_identities
    assert len(credit_identities) == (2 if trusted else 1)
    assert current_request_ip_hash() == "unknown"
