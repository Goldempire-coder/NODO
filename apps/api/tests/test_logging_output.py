from __future__ import annotations

import io
import json
import logging
import math
import socket

import pytest
from app.core.logging import SecretRedactionFilter, configure_logging, get_logger


@pytest.fixture(autouse=True)
def isolated_logging(monkeypatch):  # type: ignore[no-untyped-def]
    root = logging.getLogger()
    monkeypatch.setattr(root, "handlers", [])
    monkeypatch.setattr(root, "filters", [])
    monkeypatch.setattr(root, "level", logging.NOTSET)
    for name in ("httpx", "httpcore", "nodo.output_test", "third_party"):
        logger = logging.getLogger(name)
        monkeypatch.setattr(logger, "handlers", [])
        monkeypatch.setattr(logger, "filters", [])
        monkeypatch.setattr(logger, "level", logging.NOTSET)
        monkeypatch.setattr(logger, "propagate", True)

    original_connect = socket.socket.connect

    def local_pipe_only(sock, address):  # type: ignore[no-untyped-def]
        # Windows asyncio uses a loopback socketpair for its internal wakeup pipe.
        if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}:
            return original_connect(sock, address)
        raise AssertionError("Logging tests must not use external connections")

    def forbid_network(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("Logging tests must not use the network")

    monkeypatch.setattr(socket.socket, "connect", local_pipe_only)
    monkeypatch.setattr(socket, "create_connection", forbid_network)


@pytest.fixture
def console():  # type: ignore[no-untyped-def]
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logging.getLogger().addHandler(handler)
    configure_logging("staging")
    return stream, handler


def test_console_emits_operational_fields_as_one_json_line(console) -> None:  # type: ignore[no-untyped-def]
    stream, _handler = console
    fields = {
        "event": "backend_request_completed",
        "request_id": "req_output",
        "correlation_id": "corr_output",
        "operation_id": "op_output",
        "surface": "client_mini_app",
        "method": "GET",
        "route_template": "/api/v1/orders/{order_id}",
        "status": 503,
        "duration_ms": 12.75,
        "error_code": "UPSTREAM_UNAVAILABLE",
    }
    get_logger("nodo.output_test").info("backend_request_completed", extra=fields)

    lines = stream.getvalue().splitlines()
    assert len(lines) == 1
    output = json.loads(lines[0])
    assert output.items() >= fields.items()
    assert output["level"] == "INFO"
    assert output["logger"] == "nodo.output_test"
    assert output["timestamp"].endswith("+00:00")


def test_console_excludes_private_extras_and_redacts_allowed_fields(console) -> None:  # type: ignore[no-untyped-def]
    stream, _handler = console
    private = {
        "authorization": "Bearer synthetic-access-token",
        "cookie": "synthetic-cookie",
        "body": {"text": "synthetic-private-conversation"},
        "headers": {"X-Private": "synthetic-private-header"},
        "wallet": "0x" + "b" * 40,
        "bank_account": "synthetic-bank-account",
        "email": "synthetic-person@example.invalid",
        "password": "synthetic-password",
        "error": "synthetic-raw-exception",
        "metadata": {"secret": "synthetic-nested-secret"},
        "user_id": "synthetic-user-id",
        "traceback_frames": [{"file": "synthetic-private-path"}],
    }
    get_logger("nodo.output_test").warning(
        "notification_job_retryable_failed",
        extra={
            **private,
            "request_id": "req_retry",
            "error_code": "secret=synthetic-error-token",
            "attempts": 2,
        },
    )

    text = stream.getvalue()
    output = json.loads(text)
    assert output["request_id"] == "req_retry"
    assert output["attempts"] == 2
    assert "synthetic-" not in text
    assert "0x" + "b" * 40 not in text
    assert not set(private).intersection(output)


def test_exception_details_and_free_text_are_not_serialized(console) -> None:  # type: ignore[no-untyped-def]
    stream, _handler = console
    try:
        raise RuntimeError("synthetic-private-exception")
    except RuntimeError:
        get_logger("nodo.output_test").exception(
            "api_unhandled_error",
            extra={"request_id": "req_exception", "exception_class": "RuntimeError"},
            stack_info=True,
        )
    logging.getLogger("third_party").warning("Private body: %s", "synthetic-private-body")
    logging.getLogger("third_party").warning("synthetic_private_body", extra={"event": "synthetic_private_event"})

    text = stream.getvalue()
    first, second, third = [json.loads(line) for line in text.splitlines()]
    assert first["event"] == "api_unhandled_error"
    assert first["exception_class"] == "RuntimeError"
    assert second["event"] == "unstructured_log"
    assert third["event"] == "unstructured_log"
    assert "synthetic-private" not in text
    assert "synthetic_private" not in text
    assert "Traceback" not in text
    assert "Stack (" not in text


@pytest.mark.parametrize("value, expected", [
    ("0x" + "b" * 40, "[REDACTED]"),
    ("0x" + "a" * 64, "0xaaaa...aaaa"),
    ("T" + "B" * 33, "[REDACTED]"),
    ("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJzeW50aGV0aWMifQ.c3ludGhldGlj", "[REDACTED]"),
])
def test_allowed_labels_do_not_export_wallets_tokens_or_full_hashes(console, value: str, expected: str) -> None:  # type: ignore[no-untyped-def]
    stream, _handler = console
    get_logger("nodo.output_test").warning("diagnostic_event", extra={"request_id": value})
    output = json.loads(stream.getvalue())
    assert value not in stream.getvalue()
    assert output["request_id"] == expected


@pytest.mark.parametrize("status", [301, 307, 308, 404, 405])
def test_unmatched_or_redirect_routes_do_not_expose_raw_paths(console, status: int) -> None:  # type: ignore[no-untyped-def]
    stream, _handler = console
    get_logger("nodo.output_test").info(
        "backend_request_completed",
        extra={"status": status, "route_template": "/synthetic-private-path"},
    )
    output = json.loads(stream.getvalue())
    assert "route_template" not in output
    assert "synthetic-private-path" not in stream.getvalue()


def test_invalid_values_cannot_break_or_expand_the_json_record(console) -> None:  # type: ignore[no-untyped-def]
    stream, _handler = console
    get_logger("nodo.output_test").info(
        "backend_request_completed",
        extra={
            "event": {"body": "synthetic-private-event"},
            "request_id": ["synthetic-private-id"],
            "duration_ms": math.nan,
            "status": object(),
            "attempts": math.inf,
            "error_code": "E" * 10000,
            "route_template": "/api/v1/health?token=synthetic-token",
        },
    )
    text = stream.getvalue()
    output = json.loads(text)
    assert output["event"] == "backend_request_completed"
    assert "request_id" not in output
    assert "duration_ms" not in output
    assert "status" not in output
    assert "attempts" not in output
    assert "route_template" not in output
    assert len(output.get("error_code", "")) <= 128
    assert "synthetic-" not in text
    assert len(text) < 1024


def test_configuration_preserves_handlers_and_does_not_duplicate_filters(console) -> None:  # type: ignore[no-untyped-def]
    stream, handler = console
    existing_handlers = list(logging.getLogger().handlers)
    configure_logging("staging")
    configure_logging("staging")
    logger = get_logger("nodo.output_test")
    get_logger("nodo.output_test")
    logger.warning("diagnostic_event")

    assert logging.getLogger().handlers == existing_handlers
    assert len(stream.getvalue().splitlines()) == 1
    for target in (logging.getLogger(), handler, logger):
        assert sum(isinstance(item, SecretRedactionFilter) for item in target.filters) == 1
    assert json.loads(stream.getvalue())["event"] == "diagnostic_event"


@pytest.mark.parametrize("environment, expected_level", [("test", logging.WARNING), ("staging", logging.INFO)])
def test_fresh_process_configuration_uses_json_and_preserves_levels(monkeypatch, environment: str, expected_level: int) -> None:  # type: ignore[no-untyped-def]
    stream = io.StringIO()
    monkeypatch.setattr(logging.getLogger(), "handlers", [])
    monkeypatch.setattr("sys.stderr", stream)
    configure_logging(environment)
    get_logger("nodo.output_test").warning("diagnostic_event")

    assert logging.getLogger().level == expected_level
    assert json.loads(stream.getvalue())["event"] == "diagnostic_event"


def test_request_middleware_writes_safe_fields_to_console(console, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app.shared.observability import ObservabilityMiddleware
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    stream, _handler = console
    monkeypatch.setenv("OBSERVABILITY_REQUEST_LOGGING_ENABLED", "1")
    logger = logging.getLogger("nodo.observability")
    monkeypatch.setattr(logger, "level", logging.INFO)
    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware)

    @app.get("/sample/{item_id}")
    def sample(item_id: str) -> dict[str, bool]:
        return {"ok": True}

    response = TestClient(app).get(
        "/sample/synthetic-private-id?token=synthetic-query-token",
        headers={"Authorization": "Bearer synthetic-header-token", "X-Request-Id": "req_middleware"},
    )
    assert response.status_code == 200
    records = [json.loads(line) for line in stream.getvalue().splitlines()]
    completed = [item for item in records if item["event"] == "backend_request_completed"]
    assert len(completed) == 1
    assert completed[0]["request_id"] == "req_middleware"
    assert completed[0]["route_template"] == "/sample/{item_id}"
    assert completed[0]["status"] == 200
    assert completed[0]["duration_ms"] >= 0
    assert "synthetic-" not in stream.getvalue()
