from __future__ import annotations

import importlib
import json
import os
import socket
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse

import pytest


ROOT = Path(__file__).resolve().parents[3]
HARNESS = ROOT / "scripts" / "p2p_load_concurrency_47p1.py"
DOCUMENT = (
    ROOT
    / "control_plane"
    / "09_SLICES"
    / "slice_47P_performance_cost_load_readiness"
    / "CONCURRENCY_47P1.md"
)


def _harness_source() -> str:
    assert HARNESS.exists(), "47P1 requires a dedicated local concurrency harness"
    return HARNESS.read_text(encoding="utf-8")


def _import_script_module(name: str):  # type: ignore[no-untyped-def]
    scripts_path = str(ROOT / "scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    return importlib.import_module(name)


def _local_47p1_services_available() -> bool:
    common = _import_script_module("local_hardening_common")
    env = common.load_env_file(ROOT / ".env.local.example")
    for key, default_port in (("DATABASE_URL", 5432), ("REDIS_URL", 6379)):
        parsed = urlparse(env[key])
        try:
            with socket.create_connection(
                (parsed.hostname or "127.0.0.1", parsed.port or default_port),
                timeout=0.5,
            ):
                pass
        except OSError:
            return False
    return True


def test_47p1_local_evidence_redacts_sensitive_keys_by_pattern() -> None:
    module = _import_script_module("local_hardening_common")
    sensitive_values = {
        "BUSINESS_INTAKE_BOT_TOKEN": "synthetic-token-value",
        "SOME_API_KEY": "synthetic-api-key-value",
        "telegram_bot_token": "synthetic-telegram-value",
        "JWT_REFRESH_SECRET": "synthetic-refresh-value",
        "POSTGRES_PASSWORD": "synthetic-password-value",
    }

    result = module.redacted({**sensitive_values, "APP_ENV": "local"})

    assert result["APP_ENV"] == "local"
    assert all(result[key] == "[REDACTED]" for key in sensitive_values)
    serialized = json.dumps(result)
    assert all(value not in serialized for value in sensitive_values.values())


def test_47p1_local_smoke_executes_product_gates_and_writes_safe_evidence(
    tmp_path: Path,
) -> None:
    if os.environ.get("NODO_RUN_47P1_LOCAL_INTEGRATION") != "1":
        pytest.skip("set NODO_RUN_47P1_LOCAL_INTEGRATION=1 for local services")
    if not _local_47p1_services_available():
        pytest.skip("local PostgreSQL and Redis are unavailable")

    output_path = tmp_path / "smoke.json"
    ndjson_path = tmp_path / "smoke.ndjson"
    run_id = f"47p1_pytest_smoke_{uuid.uuid4().hex[:12]}"
    completed = subprocess.run(
        [
            sys.executable,
            str(HARNESS),
            "--smoke",
            "--env-file",
            str(ROOT / ".env.local.example"),
            "--levels",
            "50,100",
            "--run-id",
            run_id,
            "--output",
            str(output_path),
            "--ndjson-output",
            str(ndjson_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )

    assert completed.returncode == 0, (
        f"47P1 smoke exited with code {completed.returncode}"
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    records = [
        json.loads(line)
        for line in ndjson_path.read_text(encoding="utf-8").splitlines()
        if line
    ]

    assert payload["exit_code"] == 0
    assert payload["mode"] == "smoke_product_gates"
    assert payload["summary"]["product_gates_passed"] is True
    assert payload["summary"]["invariant_violations"] == []
    assert {record["scenario"] for record in records} == {
        "same_ad_contention_c50",
        "same_ad_contention_c100",
    }
    assert payload["scenarios"] == records
    _import_script_module("p2p_load_concurrency_47p1").assert_safe_report(payload)

    serialized = json.dumps(payload).lower()
    for forbidden in (
        "business_intake_bot_token",
        "database_url",
        "redis_url",
        "storage_path",
        "signed_url",
        "receiver_phone",
    ):
        assert forbidden not in serialized


def test_47p1_harness_has_local_guards_levels_and_evidence_outputs() -> None:
    source = _harness_source()

    for required in (
        "assert_local_database_url",
        "PRODUCT_GATE_LEVELS",
        "50",
        "100",
        "250",
        "LOCAL_RESOURCE_LIMIT",
        "INFRA_PROBE",
        ".local/47p1",
        "write_ndjson",
    ):
        assert required in source

    assert "nodo-staging" not in source
    assert "nodo-api-production" not in source
    assert "READY_FOR_REAL_USE" not in source


def test_47p1_harness_covers_every_required_integrity_scenario() -> None:
    source = _harness_source()

    for scenario in (
        "same_ad_contention",
        "active_order_limit",
        "shared_capacity_orders",
        "concurrent_ad_publication",
        "payment_vs_cancel",
        "payment_vs_expiration",
        "double_payment_confirmation",
        "double_delivery",
        "double_completion",
        "chat_burst",
        "receiver_details",
    ):
        assert scenario in source

    for invariant in (
        "AD_NOT_AVAILABLE",
        "ORDER_RECEIVER_DETAILS_REQUIRED",
        "ORDER_RECEIVER_DETAILS_INVALID",
        "order_state_events",
        "business_capacity_reservations",
        "notification_jobs",
        "audit_logs",
    ):
        assert invariant in source


def test_47p1_report_schema_is_aggregate_and_does_not_persist_private_payloads() -> None:
    source = _harness_source()

    for metric in (
        "requested_concurrency",
        "effective_concurrency",
        "status_counts",
        "expected_errors",
        "unexpected_errors",
        "p50_ms",
        "p95_ms",
        "p99_ms",
        "postgres_counts",
        "reservation_counts",
        "invariant_violations",
        "resource_usage",
    ):
        assert metric in source

    assert "assert_safe_report" in source


def test_47p1_summary_and_level_classification_are_deterministic() -> None:
    scripts_path = str(ROOT / "scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    module = importlib.import_module("p2p_load_concurrency_47p1")

    attempts = [
        module.AttemptResult(status_code=201, error_code=None, latency_ms=10.0),
        module.AttemptResult(
            status_code=409,
            error_code="AD_NOT_AVAILABLE",
            latency_ms=20.0,
        ),
        module.AttemptResult(
            status_code=409,
            error_code="AD_NOT_AVAILABLE",
            latency_ms=30.0,
        ),
    ]
    summary = module.summarize_attempts(
        attempts,
        requested_concurrency=3,
        effective_concurrency=3,
        expected_error_codes={"AD_NOT_AVAILABLE"},
        duration_seconds=0.05,
    )

    assert summary["status_counts"] == {"201": 1, "409": 2}
    assert summary["expected_errors"] == 2
    assert summary["unexpected_errors"] == 0
    assert summary["p50_ms"] == 20.0
    assert module.level_kind(50) == "PRODUCT_GATE"
    assert module.level_kind(100) == "PRODUCT_GATE"
    assert module.level_kind(250) == "INFRA_PROBE"

    for forbidden in (
        "response_body",
        "storage_path",
        "signed_url",
        "account_value",
        "receiver_phone",
    ):
        try:
            module.assert_safe_report({forbidden: "sensitive"})
        except ValueError:
            pass
        else:
            raise AssertionError(f"safe report accepted forbidden field: {forbidden}")


def test_47p1_document_records_commands_results_and_evidence_boundaries() -> None:
    assert DOCUMENT.exists(), "47P1 requires an evidence-backed concurrency report"
    document = DOCUMENT.read_text(encoding="utf-8")

    for required in (
        "PostgreSQL local desechable",
        "c50",
        "c100",
        "c250",
        "PRODUCT_GATE",
        "INFRA_PROBE",
        "LOCAL_RESOURCE_LIMIT",
        "NOT_TESTED",
        ".local/47p1/",
        "No deploy",
    ):
        assert required in document
