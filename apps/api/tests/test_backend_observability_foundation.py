from __future__ import annotations

import logging
import os

from fastapi.testclient import TestClient


def _set_env() -> None:
    os.environ["APP_ENV"] = "test"
    os.environ["APP_NAME"] = "NODO"
    os.environ["APP_VERSION"] = "0.0.0-slice-24a"
    os.environ["NODO_BUILD_ID"] = "pytest-build"
    os.environ["DATABASE_URL"] = "postgresql://user:password@127.0.0.1:1/nodo"
    os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"
    os.environ["API_CORS_ORIGINS"] = "http://localhost:3000"
    os.environ["OBSERVABILITY_REQUEST_LOGGING_ENABLED"] = "1"


_set_env()

from app.core.errors import ApiError  # noqa: E402
from app.main import create_app  # noqa: E402
from app.routes.telegram_bot import telegram_webhook_secret  # noqa: E402
from app.shared.logging_redaction import redact_mapping, redact_text  # noqa: E402


def _client() -> TestClient:
    _set_env()
    return TestClient(create_app())


def test_request_without_ids_receives_generated_ids() -> None:
    response = _client().get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["request_id"].startswith("req_")
    assert response.headers["X-Request-Id"] == response.json()["request_id"]
    assert response.headers["X-Correlation-Id"].startswith("corr_")
    assert response.headers["X-NODO-Operation-Id"].startswith("op_")
    assert response.headers["X-NODO-Surface"] == "unknown"


def test_request_with_valid_ids_propagates_them() -> None:
    headers = {
        "X-Request-Id": "req_valid_123",
        "X-Correlation-Id": "corr_valid_123",
        "X-NODO-Operation-Id": "op_valid_123",
        "X-NODO-Surface": "business_mini_app",
    }

    response = _client().get("/api/v1/health", headers=headers)

    assert response.status_code == 200
    assert response.json()["request_id"] == "req_valid_123"
    assert response.headers["X-Request-Id"] == "req_valid_123"
    assert response.headers["X-Correlation-Id"] == "corr_valid_123"
    assert response.headers["X-NODO-Operation-Id"] == "op_valid_123"
    assert response.headers["X-NODO-Surface"] == "business_mini_app"


def test_invalid_or_giant_ids_are_replaced() -> None:
    huge = "x" * 5000
    headers = {
        "X-Request-Id": huge,
        "X-Correlation-Id": "bad id with spaces",
        "X-NODO-Operation-Id": "../bad",
        "X-NODO-Surface": "admin web with spaces",
    }

    response = _client().get("/api/v1/health", headers=headers)

    assert response.status_code == 200
    assert response.json()["request_id"].startswith("req_")
    assert response.json()["request_id"] != huge
    assert response.headers["X-Correlation-Id"].startswith("corr_")
    assert response.headers["X-NODO-Operation-Id"].startswith("op_")
    assert response.headers["X-NODO-Surface"] == "unknown"


def test_unhandled_error_response_is_safe_and_carries_ids(caplog) -> None:  # type: ignore[no-untyped-def]
    _set_env()
    app = create_app()
    caplog.set_level(logging.ERROR)

    @app.get("/api/v1/test/boom")
    def boom() -> None:
        raise RuntimeError("database exploded with password=secret stack details")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/api/v1/test/boom",
        headers={
            "X-Request-Id": "req_boom",
            "X-Correlation-Id": "corr_boom",
            "X-NODO-Operation-Id": "op_boom",
        },
    )

    assert response.status_code == 500
    assert response.json()["request_id"] == "req_boom"
    assert response.headers["X-Request-Id"] == "req_boom"
    assert response.headers["X-Correlation-Id"] == "corr_boom"
    assert response.headers["X-NODO-Error-Code"] == "INTERNAL_ERROR"
    assert "password" not in response.text
    assert "stack" not in response.text.lower()
    assert "password=secret" not in caplog.text
    assert "database exploded" not in caplog.text
    records = [record for record in caplog.records if record.msg == "api_unhandled_error"]
    assert records
    assert records[-1].exception_class == "RuntimeError"
    assert records[-1].traceback_frames


def test_api_error_conflict_includes_safe_ids() -> None:
    _set_env()
    app = create_app()

    @app.post("/api/v1/test/idempotency-conflict")
    def conflict() -> None:
        raise ApiError("IDEMPOTENCY_CONFLICT", status_code=409)

    response = TestClient(app).post(
        "/api/v1/test/idempotency-conflict",
        headers={
            "X-Request-Id": "req_conflict",
            "X-Correlation-Id": "corr_conflict",
        },
    )

    assert response.status_code == 409
    assert response.json()["request_id"] == "req_conflict"
    assert response.headers["X-Request-Id"] == "req_conflict"
    assert response.headers["X-Correlation-Id"] == "corr_conflict"
    assert response.headers["X-NODO-Error-Code"] == "IDEMPOTENCY_CONFLICT"


def test_rate_limit_error_includes_safe_ids() -> None:
    _set_env()
    app = create_app()

    @app.get("/api/v1/test/rate-limited")
    def rate_limited() -> None:
        raise ApiError("RATE_LIMITED", status_code=429)

    response = TestClient(app).get(
        "/api/v1/test/rate-limited",
        headers={
            "X-Request-Id": "req_rate_limited",
            "X-Correlation-Id": "corr_rate_limited",
            "X-NODO-Operation-Id": "op_rate_limited",
        },
    )

    assert response.status_code == 429
    assert response.json()["request_id"] == "req_rate_limited"
    assert response.headers["X-Request-Id"] == "req_rate_limited"
    assert response.headers["X-Correlation-Id"] == "corr_rate_limited"
    assert response.headers["X-NODO-Operation-Id"] == "op_rate_limited"
    assert response.headers["X-NODO-Error-Code"] == "RATE_LIMITED"


def test_telegram_webhook_malformed_json_keeps_safe_ids() -> None:
    os.environ["BOT_TOKEN"] = "123456:testbot"
    secret = telegram_webhook_secret(os.environ["BOT_TOKEN"])
    response = _client().post(
        f"/api/v1/telegram/webhook/{secret}",
        headers={
            "Content-Type": "application/json",
            "X-Request-Id": "req_bad_telegram",
            "X-Correlation-Id": "corr_bad_telegram",
        },
        content="{not json",
    )

    assert response.status_code == 422
    assert response.json()["request_id"] == "req_bad_telegram"
    assert response.headers["X-Correlation-Id"] == "corr_bad_telegram"
    assert "123456:testbot" not in response.text


def test_log_redaction_masks_sensitive_values() -> None:
    message = (
        "Authorization: Bearer abc.def.ghi "
        "postgresql://user:password@db.example/nodo "
        "storage_path=private/path/file.pdf "
        "account_value=full-bank-account "
        "password=super-secret "
        "secret=hidden "
        "tx=0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa "
        "https://example.supabase.co/object/sign/bucket/file?token=secret&signature=abc"
    )

    redacted = redact_text(message)
    mapped = redact_mapping({"refresh_token": "secret-refresh", "account_value": "full-bank-account"})

    assert "abc.def.ghi" not in redacted
    assert "password=super-secret" not in redacted
    assert "private/path/file.pdf" not in redacted
    assert "full-bank-account" not in redacted
    assert "super-secret" not in redacted
    assert "secret=hidden" not in redacted
    assert "private/path/file.pdf" not in redact_mapping({"storage_path": "private/path/file.pdf"})["storage_path"]
    assert redact_mapping({"password": "super-secret", "secret": "hidden"}) == {"password": "[REDACTED]", "secret": "[REDACTED]"}
    assert "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" not in redacted
    assert "token=secret" not in redacted
    assert mapped["refresh_token"] == "[REDACTED]"
    assert mapped["account_value"] == "[REDACTED]"


def test_request_log_is_structured_and_redacted(caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO, logger="nodo.observability")
    response = _client().get(
        "/api/v1/health?access_token=secret",
        headers={
            "Authorization": "Bearer secret-token",
            "X-Request-Id": "req_log",
            "X-Correlation-Id": "corr_log",
            "X-NODO-Operation-Id": "op_log",
            "X-NODO-Surface": "client_mini_app",
        },
    )

    assert response.status_code == 200
    records = [record for record in caplog.records if record.name == "nodo.observability" and record.msg == "backend_request_completed"]
    assert records
    record = records[-1]
    assert record.request_id == "req_log"
    assert record.correlation_id == "corr_log"
    assert record.operation_id == "op_log"
    assert record.surface == "client_mini_app"
    assert record.route_template == "/api/v1/health"
    assert "access_token" not in record.route_template
    assert "secret-token" not in caplog.text


def test_observability_request_logging_can_be_disabled(caplog) -> None:  # type: ignore[no-untyped-def]
    _set_env()
    os.environ["OBSERVABILITY_REQUEST_LOGGING_ENABLED"] = "0"
    caplog.set_level(logging.INFO, logger="nodo.observability")

    response = TestClient(create_app()).get("/api/v1/health", headers={"X-Request-Id": "req_disabled"})

    assert response.status_code == 200
    assert "backend_request_completed" not in [record.msg for record in caplog.records if record.name == "nodo.observability"]


def test_response_headers_do_not_expose_sensitive_values() -> None:
    response = _client().get(
        "/api/v1/health",
        headers={
            "Authorization": "Bearer should-not-echo",
            "Cookie": "refresh_token=should-not-echo",
            "X-Request-Id": "req_headers",
        },
    )

    header_blob = "\n".join(f"{key}: {value}" for key, value in response.headers.items())
    assert "should-not-echo" not in header_blob
    assert "Authorization" not in header_blob
    assert "refresh_token" not in header_blob
