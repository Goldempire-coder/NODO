from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi.testclient import TestClient


def _set_env(*, enabled: bool = False, max_batch: int = 20, max_event_bytes: int = 2048) -> None:
    os.environ["APP_ENV"] = "test"
    os.environ["APP_NAME"] = "NODO"
    os.environ["APP_VERSION"] = "0.0.0-slice-34T"
    os.environ["NODO_BUILD_ID"] = "pytest-build"
    os.environ["DATABASE_URL"] = "postgresql://user:password@127.0.0.1:1/nodo"
    os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"
    os.environ["JWT_SECRET"] = "test-access-secret"
    os.environ["JWT_REFRESH_SECRET"] = "test-refresh-secret"
    os.environ["API_CORS_ORIGINS"] = "http://localhost:3000"
    os.environ["OBSERVABILITY_INGEST_ENABLED"] = "1" if enabled else "0"
    os.environ["OBSERVABILITY_MAX_EVENTS_PER_BATCH"] = str(max_batch)
    os.environ["OBSERVABILITY_MAX_EVENT_BYTES"] = str(max_event_bytes)


_set_env()

from app.auth.jwt import create_access_token  # noqa: E402
from app.main import create_app  # noqa: E402


def _authenticated_client(*, enabled: bool = False, max_batch: int = 20, max_event_bytes: int = 2048) -> tuple[TestClient, str, str]:
    _set_env(enabled=enabled, max_batch=max_batch, max_event_bytes=max_event_bytes)
    app = create_app()
    user, _ = app.state.user_repository.upsert_telegram_user(
        telegram_id=6808095582,
        username="observability_test",
        first_name="Obs",
        last_name=None,
    )
    token, _, _ = create_access_token(
        user_id=user.id,
        role=user.role,
        status=user.status,
        secret=os.environ["JWT_SECRET"],
        ttl_seconds=900,
    )
    return TestClient(app), token, user.id


def _payload(*, metadata: dict | None = None, event_id: str = "evt_1") -> dict:
    return {
        "session_id": "sess_test_1",
        "app_version": "test",
        "build_id": "pytest",
        "events": [
            {
                "event_id": event_id,
                "event_type": "api_failure",
                "severity": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": "req_frontend_1",
                "correlation_id": "corr_frontend_1",
                "operation_id": "op_frontend_1",
                "screen": "buy-credits",
                "previous_screen": "credits-dashboard",
                "action": "POST",
                "method": "POST",
                "route_template": "/api/v1/business/credits/base-payment",
                "status_code": 503,
                "duration_ms": 321.4,
                "error_code": "ONCHAIN_RPC_UNAVAILABLE",
                "resource_refs": {"credit_purchase_id": "purchase_1"},
                "metadata": metadata or {"online": True, "response_started": True},
            }
        ],
    }


def _headers(token: str, *, surface: str = "business_mini_app") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Request-Id": "req_observability_ingest",
        "X-Correlation-Id": "corr_observability_ingest",
        "X-NODO-Operation-Id": "op_observability_ingest",
        "X-NODO-Surface": surface,
    }


def test_frontend_observability_ingest_is_disabled_by_default() -> None:
    client, token, _ = _authenticated_client(enabled=False)

    response = client.post("/api/v1/observability/events", headers=_headers(token), json=_payload())

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "OBSERVABILITY_DISABLED"


def test_frontend_observability_ingest_requires_auth() -> None:
    client, _, _ = _authenticated_client(enabled=True)

    response = client.post("/api/v1/observability/events", headers={"X-NODO-Surface": "business_mini_app"}, json=_payload())

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_frontend_observability_ingest_logs_redacted_event(caplog) -> None:  # type: ignore[no-untyped-def]
    client, token, user_id = _authenticated_client(enabled=True)
    caplog.set_level(logging.INFO, logger="nodo.frontend_observability")

    response = client.post(
        "/api/v1/observability/events",
        headers=_headers(token),
        json=_payload(
            metadata={
                "token": "must-not-appear",
                "pin": "1234",
                "wallet": "0x1111111111111111111111111111111111111111",
                "zelle": "owner@example.com",
                "account_value": "full-account",
                "storage_path": "private/file.pdf",
                "safe_counter": 3,
            }
        ),
    )

    assert response.status_code == 200
    assert response.json()["data"] == {"accepted": 1}
    records = [record for record in caplog.records if record.name == "nodo.frontend_observability" and record.msg == "frontend_observability_event"]
    assert records
    record = records[-1]
    assert record.actor_user_hash != user_id
    assert not hasattr(record, "telegram_id")
    assert record.surface == "business_mini_app"
    assert record.route_template == "/api/v1/business/credits/base-payment"
    assert record.metadata["token"] == "[REDACTED]"
    assert record.metadata["pin"] == "[REDACTED]"
    assert record.metadata["wallet"] == "[REDACTED]"
    assert record.metadata["zelle"] == "[REDACTED]"
    assert record.metadata["account_value"] == "[REDACTED]"
    assert record.metadata["storage_path"] == "[REDACTED]"
    assert record.metadata["safe_counter"] == 3


def test_frontend_observability_ingest_rejects_unknown_surface() -> None:
    client, token, _ = _authenticated_client(enabled=True)

    response = client.post("/api/v1/observability/events", headers=_headers(token, surface="unknown"), json=_payload())

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "OBSERVABILITY_ACCESS_DENIED"


def test_frontend_observability_ingest_rejects_batches_above_configured_limit() -> None:
    client, token, _ = _authenticated_client(enabled=True, max_batch=1)
    payload = _payload()
    payload["events"].append({**payload["events"][0], "event_id": "evt_2"})

    response = client.post("/api/v1/observability/events", headers=_headers(token), json=payload)

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "OBSERVABILITY_BATCH_TOO_LARGE"


def test_frontend_observability_ingest_rejects_oversized_events() -> None:
    client, token, _ = _authenticated_client(enabled=True, max_event_bytes=250)

    response = client.post(
        "/api/v1/observability/events",
        headers=_headers(token),
        json=_payload(metadata={"safe_debug": "x" * 1000}),
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "OBSERVABILITY_EVENT_TOO_LARGE"
