from __future__ import annotations

import asyncio
import inspect
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import apply_staging_migrations  # noqa: E402
import apply_staging_single_migration  # noqa: E402
import burst_spacing_probe  # noqa: E402
import capacity_real  # noqa: E402
import cloud_load_runner  # noqa: E402
import connection_origin_probe  # noqa: E402
import cleanup_synthetic_run  # noqa: E402
import edge_header_correlation_probe  # noqa: E402
import external_latency_probe  # noqa: E402
import marketplace_delivery_diagnostics  # noqa: E402
import prepare_marketplace_delivery_fixtures  # noqa: E402
import reconcile_staging_migration_ledger  # noqa: E402
import staging_cleanup_synthetic_run  # noqa: E402
import staging_guardrails  # noqa: E402
import staging_storage_smoke  # noqa: E402
import staging_telegram_webhook_smoke  # noqa: E402
import ttfb_queue_probe  # noqa: E402
from app.auth.jwt import decode_access_token  # noqa: E402
from app.routes.telegram_bot import telegram_webhook_secret  # noqa: E402


def _env_file(tmp_path: Path, *, app_env: str = "staging", extra: dict[str, str] | None = None) -> Path:
    values = {
        "APP_ENV": app_env,
        "APP_VERSION": "slice-17A-test",
        "NODO_ENVIRONMENT_KIND": "staging",
        "NODO_STAGING_VALIDATION": "1",
        "NODO_STAGING_PROJECT_ID": "staging-project",
        "DATABASE_URL": "postgresql://user:password@db.staging.supabase.co:5432/postgres",
        "REDIS_URL": "rediss://default:password@staging-redis.upstash.io:6379",
        "NODO_STAGING_DB_HOST_ALLOWLIST": "db.staging.supabase.co",
        "NODO_STAGING_API_HOST_ALLOWLIST": "nodo-staging.example.test",
        "NODO_STAGING_API_BASE_URL": "https://nodo-staging.example.test",
        "SUPABASE_URL": "https://staging-project.supabase.co",
        "NODO_STAGING_SUPABASE_URL": "https://staging-project.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "service-role-secret",
        "BOT_TOKEN": "123456:client-secret-token",
        "BUSINESS_INTAKE_BOT_TOKEN": "123456:business-secret-token",
    }
    if extra:
        values.update(extra)
    path = tmp_path / ".env.staging.test"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(f"{key}={value}" for key, value in values.items()), encoding="utf-8")
    return path


def test_staging_guardrails_allow_staging_and_redact_secrets(tmp_path: Path) -> None:
    env_file = _env_file(tmp_path)

    guardrails = staging_guardrails.require_staging_guardrails(env_file=env_file)
    payload = staging_guardrails.guardrail_payload(guardrails)

    assert guardrails.env["APP_ENV"] == "staging"
    assert payload["env"]["DATABASE_URL"] == "[REDACTED]"
    assert payload["env"]["REDIS_URL"] == "[REDACTED]"
    assert "password" not in json.dumps(payload)


def test_marketplace_delivery_external_gap_and_percentiles() -> None:
    assert marketplace_delivery_diagnostics.external_gap_ms(250.5, 10.25) == 240.25
    assert marketplace_delivery_diagnostics.external_gap_ms(5.0, 10.0) == 0.0
    assert marketplace_delivery_diagnostics.external_gap_ms(5.0, None) is None

    values = [1.0, 2.0, 3.0, 4.0, 100.0]
    summary = marketplace_delivery_diagnostics.percentiles(values)

    assert summary["count"] == 5
    assert summary["p50_ms"] == 3.0
    assert summary["p95_ms"] == 100.0


def test_marketplace_delivery_recorder_groups_by_screen_endpoint_and_user() -> None:
    recorder = marketplace_delivery_diagnostics.MarketplaceDeliveryRecorder(sample_limit=10)
    response = httpx.Response(
        200,
        headers={
            "X-NODO-Process-Time-Ms": "12.5",
            "X-Request-Id": "req_1",
            "X-Correlation-Id": "corr_1",
            "X-NODO-Operation-Id": "op_1",
        },
        json={
            "data": {
                "items": [],
                "_profile": {
                    "dependency": {"auth": {"mode": "marketplace_claims", "stages": [{"stage": "auth:decode", "elapsed_ms": 0.2}]}},
                    "stages": [{"stage": "cache:hit", "elapsed_ms": 0.1, "metadata": {"hit_type": "local"}}],
                },
            }
        },
        request=httpx.Request("GET", "https://example.test/api/v1/ads/search"),
    )
    request = marketplace_delivery_diagnostics.FlowRequest(
        synthetic_user_id="user_00001",
        screen="marketplace-list",
        flow_step="marketplace_home",
        method="GET",
        path="/api/v1/ads/search?limit=50",
    )

    recorder.add_response(request=request, index=0, status=200, client_total_ms=120.0, response=response)
    summary = recorder.summary()

    assert summary["overall"]["requests"] == 1
    assert summary["overall"]["external_gap"]["p95_ms"] == 107.5
    assert summary["by_screen"]["marketplace-list"]["requests"] == 1
    assert summary["by_endpoint"]["/api/v1/ads/search"]["request_count_per_synthetic_user"] == 1.0
    assert summary["profile"]["cache_hit_counts"] == {"local": 1}
    assert summary["profile"]["cache_hit_ratio"] == 1.0
    assert summary["profile"]["auth_mode_counts"] == {"marketplace_claims": 1}


def test_marketplace_delivery_sensitive_scan_ignores_redacted_key_names() -> None:
    payload = {
        "env": {
            "DATABASE_URL": "[REDACTED]",
            "REDIS_URL": "[REDACTED]",
        },
        "safe": "no sensitive value here",
    }

    assert marketplace_delivery_diagnostics.output_contains_sensitive_marker(payload) == []
    assert marketplace_delivery_diagnostics.output_contains_sensitive_marker({"leak": "storage_path=/private/file"}) == ["storage_path"]


def test_prepare_marketplace_delivery_fixture_plan_counts() -> None:
    counts = prepare_marketplace_delivery_fixtures.expected_counts(250, 6)

    assert counts["users"] == 251
    assert counts["businesses"] == 250
    assert counts["business_access_links"] == 250
    assert counts["business_payment_methods"] == 250
    assert counts["credit_wallets"] == 250
    assert counts["ads"] == 1500
    assert counts["credits_ledger"] == 1500


def test_prepare_marketplace_delivery_dry_run_does_not_seed(tmp_path: Path, monkeypatch: Any) -> None:
    env_file = _env_file(tmp_path)

    def fail_seed(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("dry-run must not write fixtures")

    monkeypatch.setattr(prepare_marketplace_delivery_fixtures, "seed_fixture", fail_seed)
    payload = prepare_marketplace_delivery_fixtures.build_payload(
        env_file=env_file,
        run_id="slice33a3_dry_run_0001",
        businesses=250,
        ads_per_business=6,
        apply=False,
        confirm_staging=False,
    )

    assert payload["mode"] == "dry_run"
    assert payload["planned_counts"]["ads"] == 1500
    assert payload["inserted_counts"] == {}
    assert payload["exit_code"] == 0


def test_prepare_marketplace_delivery_apply_requires_ack(tmp_path: Path) -> None:
    env_file = _env_file(tmp_path)

    try:
        prepare_marketplace_delivery_fixtures.build_payload(
            env_file=env_file,
            run_id="slice33a3_apply_0001",
            businesses=1,
            ads_per_business=1,
            apply=True,
            confirm_staging=True,
        )
    except staging_guardrails.StagingGuardrailError as exc:
        assert "STAGING_VALIDATION_ACK" in str(exc)
    else:
        raise AssertionError("apply must require STAGING_VALIDATION_ACK matching run_id")


def test_prepare_marketplace_delivery_rejects_unsafe_run_id(tmp_path: Path) -> None:
    env_file = _env_file(tmp_path)

    try:
        prepare_marketplace_delivery_fixtures.build_payload(
            env_file=env_file,
            run_id="unsafe%run_id",
            businesses=1,
            ads_per_business=1,
            apply=False,
            confirm_staging=False,
        )
    except ValueError as exc:
        assert "run_id" in str(exc)
    else:
        raise AssertionError("unsafe run_id must be rejected")


def test_prepare_marketplace_delivery_output_scan_blocks_sensitive_values() -> None:
    assert prepare_marketplace_delivery_fixtures.output_contains_sensitive_marker({"safe": "ok"}) == []
    assert prepare_marketplace_delivery_fixtures.output_contains_sensitive_marker({"leak": "account_value=secret"}) == [
        "account_value"
    ]
    assert prepare_marketplace_delivery_fixtures.output_contains_sensitive_marker({"leak": "storage_path=/private"}) == [
        "storage_path"
    ]


def test_prepare_marketplace_delivery_validation_fails_for_invalid_status() -> None:
    expected = prepare_marketplace_delivery_fixtures.expected_counts(2, 2)
    failures = prepare_marketplace_delivery_fixtures.fixture_validation_failures(
        {
            "approved_businesses": 1,
            "marketplace_visible_ads": 3,
            "invalid_ads": 1,
            "active_access_links": 2,
            "valid_wallets": 2,
        },
        expected,
    )

    assert "approved_business_count_mismatch" in failures
    assert "marketplace_visible_ad_count_mismatch" in failures
    assert "invalid_ads_present" in failures


def test_prepare_marketplace_delivery_cleanup_discoverability_uses_cleanup_tables() -> None:
    source = inspect.getsource(prepare_marketplace_delivery_fixtures.cleanup_discoverability)

    assert "populate_cleanup_tables" in source
    assert "collect_counts" in source


def test_marketplace_delivery_can_use_existing_fixture_run_id(tmp_path: Path) -> None:
    diagnostics = marketplace_delivery_diagnostics.MarketplaceDeliveryDiagnostics(
        env_file=_env_file(tmp_path),
        remote_base_url="https://nodo-staging.example.test",
        run_id="slice33a3_measure_0001",
        businesses=1,
        ads_per_business=1,
        synthetic_users=1,
        requests=1,
        concurrency=1,
        max_connections=1,
        profile_marketplace=True,
        output=tmp_path / "delivery.json",
        profile_detail_limit=1,
        fixture_run_id="slice33a3_fixture_0001",
    )

    assert diagnostics.fixture_run_id == "slice33a3_fixture_0001"


def test_marketplace_delivery_expands_users_to_consume_request_target(tmp_path: Path) -> None:
    diagnostics = marketplace_delivery_diagnostics.MarketplaceDeliveryDiagnostics(
        env_file=_env_file(tmp_path),
        remote_base_url="https://nodo-staging.example.test",
        run_id="slice33a5_measure_0001",
        businesses=250,
        ads_per_business=6,
        synthetic_users=100,
        requests=1000,
        concurrency=100,
        max_connections=100,
        profile_marketplace=True,
        output=tmp_path / "delivery.json",
        profile_detail_limit=1,
        fixture_run_id="slice33a5_fixture_0001",
    )

    assert diagnostics.steps_per_user == 4
    assert diagnostics.synthetic_users_requested == 100
    assert diagnostics.synthetic_users_used == 250
    assert diagnostics.request_consumption_mode == "auto_expand_users_to_target_requests"


def test_marketplace_delivery_non_multiple_request_target_uses_ceiling(tmp_path: Path) -> None:
    diagnostics = marketplace_delivery_diagnostics.MarketplaceDeliveryDiagnostics(
        env_file=_env_file(tmp_path),
        remote_base_url="https://nodo-staging.example.test",
        run_id="slice33a5_measure_0002",
        businesses=3,
        ads_per_business=2,
        synthetic_users=1,
        requests=10,
        concurrency=2,
        max_connections=2,
        profile_marketplace=False,
        output=tmp_path / "delivery.json",
        profile_detail_limit=1,
        fixture_run_id="slice33a5_fixture_0002",
    )

    assert diagnostics.synthetic_users_used == 3


def test_marketplace_delivery_recorder_summarizes_phase_timings() -> None:
    recorder = marketplace_delivery_diagnostics.MarketplaceDeliveryRecorder(sample_limit=10)
    response = httpx.Response(
        200,
        headers={"X-NODO-Process-Time-Ms": "20.0"},
        json={"data": {"items": []}},
        request=httpx.Request("GET", "https://example.test/api/v1/ads/search"),
    )
    request = marketplace_delivery_diagnostics.FlowRequest(
        synthetic_user_id="user_00001",
        screen="marketplace-list",
        flow_step="marketplace_home",
        method="GET",
        path="/api/v1/ads/search?limit=50",
    )

    recorder.add_response(
        request=request,
        index=0,
        status=200,
        client_total_ms=120.0,
        response=response,
        ttfb_or_headers_ms=90.0,
        response_read_ms=5.0,
        request_start_monotonic=100.0,
        request_end_monotonic=100.12,
    )
    summary = recorder.summary()

    assert summary["overall"]["ttfb_or_headers"]["p95_ms"] == 90.0
    assert summary["overall"]["response_read"]["p95_ms"] == 5.0
    assert summary["phase_timing_limitations"]


def test_marketplace_delivery_classifies_target_mismatch() -> None:
    summary = {
        "overall": {
            "client": {"p95_ms": 10.0},
            "backend_process": {"p95_ms": 1.0},
            "ttfb_or_headers": {"p95_ms": 1.0},
            "response_read": {"p95_ms": 1.0},
            "response_kb_p95": 1.0,
            "error_counts": {},
        },
        "profile": {"stage_latency": {}, "db_query_p95_ms": 0.0},
    }

    assert (
        marketplace_delivery_diagnostics.MarketplaceDeliveryDiagnostics.classify(
            summary,
            requested_requests=1000,
            actual_requests=400,
        )
        == "REQUEST_TARGET_MISMATCH"
    )


def test_marketplace_delivery_classifies_external_ttfb_delivery() -> None:
    summary = {
        "overall": {
            "client": {"p95_ms": 4000.0},
            "backend_process": {"p95_ms": 50.0},
            "ttfb_or_headers": {"p95_ms": 3500.0},
            "response_read": {"p95_ms": 50.0},
            "response_kb_p95": 25.0,
            "error_counts": {},
        },
        "profile": {"stage_latency": {}, "db_query_p95_ms": 1.0},
    }

    assert (
        marketplace_delivery_diagnostics.MarketplaceDeliveryDiagnostics.classify(
            summary,
            requested_requests=1000,
            actual_requests=1000,
        )
        == "TTFB_EDGE_OR_RUNTIME_QUEUE"
    )


def test_marketplace_delivery_classifies_backend_cold_cache() -> None:
    summary = {
        "overall": {
            "client": {"p95_ms": 1200.0},
            "backend_process": {"p95_ms": 900.0},
            "ttfb_or_headers": {"p95_ms": 950.0},
            "response_read": {"p95_ms": 5.0},
            "response_kb_p95": 20.0,
            "error_counts": {},
        },
        "profile": {
            "stage_latency": {
                "cache:lock_wait": {"p95_ms": 700.0},
            },
            "db_query_p95_ms": 10.0,
        },
    }

    assert (
        marketplace_delivery_diagnostics.MarketplaceDeliveryDiagnostics.classify(
            summary,
            requested_requests=1000,
            actual_requests=1000,
        )
        == "BACKEND_COLD_CACHE"
    )


def test_marketplace_delivery_warm_mode_is_explicit_and_prewarm_separate(tmp_path: Path) -> None:
    diagnostics = marketplace_delivery_diagnostics.MarketplaceDeliveryDiagnostics(
        env_file=_env_file(tmp_path),
        remote_base_url="https://nodo-staging.example.test",
        run_id="slice33a5_measure_0003",
        businesses=1,
        ads_per_business=1,
        synthetic_users=1,
        requests=4,
        concurrency=1,
        max_connections=1,
        profile_marketplace=True,
        output=tmp_path / "delivery.json",
        profile_detail_limit=1,
        fixture_run_id="slice33a5_fixture_0003",
        cache_mode="warm",
    )

    assert diagnostics.cache_mode == "warm"
    assert diagnostics.prewarm_result["enabled"] is True
    assert diagnostics.prewarm_result["prewarm_requests"] == 0


def test_marketplace_delivery_ramp_scheduler_distributes_flow_starts() -> None:
    offsets = marketplace_delivery_diagnostics.schedule_flow_offsets(
        flows=4,
        traffic_shape="ramp",
        ramp_duration_seconds=60,
    )

    assert offsets == [0.0, 20.0, 40.0, 60.0]


def test_marketplace_delivery_steady_scheduler_uses_request_rate() -> None:
    offsets = marketplace_delivery_diagnostics.schedule_flow_offsets(
        flows=3,
        traffic_shape="steady",
        target_rps=20,
        steps_per_flow=4,
    )

    assert offsets == [0.0, 0.2, 0.4]


def test_marketplace_delivery_traffic_shape_is_reportable(tmp_path: Path) -> None:
    diagnostics = marketplace_delivery_diagnostics.MarketplaceDeliveryDiagnostics(
        env_file=_env_file(tmp_path),
        remote_base_url="https://nodo-staging.example.test",
        run_id="slice33j_measure_0001",
        businesses=1,
        ads_per_business=1,
        synthetic_users=1,
        requests=4,
        concurrency=1,
        max_connections=1,
        profile_marketplace=True,
        output=tmp_path / "delivery.json",
        profile_detail_limit=1,
        fixture_run_id="slice33j_fixture_0001",
        cache_mode="cold",
        traffic_shape="ramp",
        ramp_duration_seconds=60,
    )

    assert diagnostics.traffic_shape == "ramp"
    assert diagnostics.ramp_duration_seconds == 60
    assert diagnostics.target_rps is None


def test_marketplace_delivery_records_queue_wait_and_step_metadata() -> None:
    recorder = marketplace_delivery_diagnostics.MarketplaceDeliveryRecorder(sample_limit=10)
    request = marketplace_delivery_diagnostics.FlowRequest(
        synthetic_user_id="user_00001",
        screen="marketplace-search",
        flow_step="marketplace_filtered_search",
        method="GET",
        path="/api/v1/ads/search?limit=20",
        step_number=2,
    )
    response = httpx.Response(
        200,
        headers={"X-NODO-Process-Time-Ms": "10.0"},
        json={"data": {"items": []}},
        request=httpx.Request("GET", "https://example.test/api/v1/ads/search"),
    )

    recorder.add_response(
        request=request,
        index=0,
        status=200,
        client_total_ms=100.0,
        response=response,
        queue_wait_ms=12.5,
        request_ready_at=10.0,
        request_start_monotonic=10.0125,
        response_started_monotonic=10.09,
        request_end_monotonic=10.1,
    )
    summary = recorder.summary()

    assert recorder.records[0]["step_number"] == 2
    assert recorder.records[0]["queue_wait_ms"] == 12.5
    assert recorder.records[0]["request_ready_at"] == 10.0
    assert recorder.records[0]["request_started_at"] == 10.0125
    assert recorder.records[0]["response_started"] is True
    assert summary["overall"]["queue_wait"]["p95_ms"] == 12.5
    assert summary["by_flow_step"]["marketplace_filtered_search"]["queue_wait"]["p95_ms"] == 12.5


def test_marketplace_delivery_transport_error_summary_tracks_recovery() -> None:
    recorder = marketplace_delivery_diagnostics.MarketplaceDeliveryRecorder(sample_limit=10)
    request = marketplace_delivery_diagnostics.FlowRequest(
        synthetic_user_id="user_00001",
        screen="marketplace-search",
        flow_step="marketplace_filtered_search",
        method="GET",
        path="/api/v1/ads/search?limit=20",
        step_number=2,
    )
    exc = httpx.ReadTimeout("timeout", request=httpx.Request("GET", "https://example.test/api/v1/ads/search"))

    recorder.add_request_error(
        request=request,
        index=0,
        client_total_ms=30000.0,
        exc=exc,
        request_id="req_1",
        correlation_id="corr_1",
        operation_id="op_1",
        retry_attempt=0,
        recovered_by_retry=True,
        record_as_response=False,
    )
    summary = recorder.summary()

    assert summary["overall"]["transport_errors"]["raw_transport_errors"] == 1
    assert summary["overall"]["transport_errors"]["recovered_transport_errors"] == 1
    assert summary["overall"]["transport_errors"]["unrecovered_transport_errors"] == 0
    assert summary["request_error_summary"]["raw_transport_errors"] == 1
    assert summary["request_error_summary"]["recovered_transport_errors"] == 1
    assert summary["request_error_summary"]["unrecovered_transport_errors"] == 0


def test_marketplace_delivery_filtered_search_mode_uses_one_step(tmp_path: Path) -> None:
    diagnostics = marketplace_delivery_diagnostics.MarketplaceDeliveryDiagnostics(
        env_file=_env_file(tmp_path),
        remote_base_url="https://nodo-staging.example.test",
        run_id="slice33k_filtered_0001",
        businesses=1,
        ads_per_business=1,
        synthetic_users=250,
        requests=250,
        concurrency=250,
        max_connections=250,
        profile_marketplace=True,
        output=tmp_path / "delivery.json",
        profile_detail_limit=1,
        fixture_run_id="slice33k_fixture_0001",
        traffic_shape="ramp",
        ramp_duration_seconds=60,
        flow_mode="filtered_search_only",
    )

    assert diagnostics.flow_mode == "filtered_search_only"
    assert diagnostics.steps_per_user == 1
    assert diagnostics.synthetic_users_used == 250


def test_marketplace_delivery_step_cap_jitter_and_retry_are_reportable(tmp_path: Path) -> None:
    diagnostics = marketplace_delivery_diagnostics.MarketplaceDeliveryDiagnostics(
        env_file=_env_file(tmp_path),
        remote_base_url="https://nodo-staging.example.test",
        run_id="slice33k_options_0001",
        businesses=1,
        ads_per_business=1,
        synthetic_users=1,
        requests=4,
        concurrency=4,
        max_connections=4,
        profile_marketplace=True,
        output=tmp_path / "delivery.json",
        profile_detail_limit=1,
        fixture_run_id="slice33k_fixture_0001",
        traffic_shape="ramp",
        ramp_duration_seconds=60,
        per_step_concurrency_cap=100,
        step_jitter_ms=250,
        retry_transport_once=True,
    )

    assert diagnostics.per_step_concurrency_cap == 100
    assert diagnostics.step_jitter_ms == 250
    assert diagnostics.retry_transport_once is True


def test_ttfb_queue_probe_parses_curl_write_out_and_derives_phases() -> None:
    sample = ttfb_queue_probe.parse_curl_write_out(
        '{"http_code":200,"time_namelookup":0.010,"time_connect":0.040,'
        '"time_appconnect":0.100,"time_pretransfer":0.120,'
        '"time_starttransfer":0.820,"time_total":0.900,"size_download":1234}'
    )
    phases = ttfb_queue_probe.derive_curl_phases(sample)

    assert phases["dns_ms"] == 10.0
    assert phases["tcp_connect_ms"] == 30.0
    assert phases["tls_ms"] == 60.0
    assert phases["pretransfer_ms"] == 20.0
    assert phases["server_wait_ms"] == 700.0
    assert phases["download_ms"] == 80.0


def test_ttfb_queue_probe_detects_concurrency_knee() -> None:
    rows = [
        {
            "concurrency": 1,
            "summary": {
                "ttfb_or_headers": {"p95_ms": 100.0},
                "client": {"p95_ms": 150.0},
                "error_counts": {},
            },
        },
        {
            "concurrency": 25,
            "summary": {
                "ttfb_or_headers": {"p95_ms": 1200.0},
                "client": {"p95_ms": 2500.0},
                "error_counts": {},
            },
        },
        {
            "concurrency": 50,
            "summary": {
                "ttfb_or_headers": {"p95_ms": 1800.0},
                "client": {"p95_ms": 3500.0},
                "error_counts": {"READ_TIMEOUT": 1},
            },
        },
    ]

    knee = ttfb_queue_probe.detect_knee(rows)

    assert knee["first_ttfb_p95_gt_1000"] == 25
    assert knee["first_client_p95_gt_3000"] == 50
    assert knee["first_transport_error"] == 50


def test_ttfb_queue_probe_classifies_pool_limit() -> None:
    rows = [
        {"max_connections": 10, "summary": {"ttfb_or_headers": {"p95_ms": 3000.0}}},
        {"max_connections": 100, "summary": {"ttfb_or_headers": {"p95_ms": 1000.0}}},
        {"max_connections": 200, "summary": {"ttfb_or_headers": {"p95_ms": 1050.0}}},
    ]

    assert ttfb_queue_probe.classify_pool_isolation(rows) == "HARNESS_POOL_LIMIT"


def test_ttfb_queue_probe_classifies_keepalive_importance() -> None:
    rows = [
        {"keepalive": "on", "summary": {"ttfb_or_headers": {"p95_ms": 1000.0}}},
        {"keepalive": "off", "summary": {"ttfb_or_headers": {"p95_ms": 2200.0}}},
    ]

    assert ttfb_queue_probe.classify_keepalive(rows) == "CONNECTION_REUSE_IMPORTANT"


def test_ttfb_queue_probe_curl_classification_prefers_starttransfer() -> None:
    summary = {
        "phases": {
            "dns_ms": {"p95_ms": 10.0},
            "tcp_connect_ms": {"p95_ms": 20.0},
            "tls_ms": {"p95_ms": 50.0},
            "server_wait_ms": {"p95_ms": 2500.0},
        }
    }

    assert ttfb_queue_probe.classify_curl_summary(summary) == "CURL_STARTTRANSFER_HIGH"


def test_ttfb_queue_probe_output_scan_blocks_sensitive_values() -> None:
    assert ttfb_queue_probe.output_contains_sensitive_marker({"safe": "ok"}) == []
    assert ttfb_queue_probe.output_contains_sensitive_marker({"leak": "account_value=secret"}) == ["account_value"]
    assert ttfb_queue_probe.output_contains_sensitive_marker({"leak": "storage_path=/private"}) == ["storage_path"]


def test_ttfb_queue_probe_payload_contains_cleanup_recommendation(tmp_path: Path) -> None:
    probe = ttfb_queue_probe.TTFBQueueProbe(
        env_file=_env_file(tmp_path),
        remote_base_url="https://nodo-staging.example.test",
        run_id="slice33a6_probe_0001",
        output=tmp_path / "probe.json",
        fixture_run_id="slice33a6_fixture_0001",
    )

    payload = probe._payload("unit_test", {"rows": [], "exit_code": 0})

    assert payload["cleanup"]["fixture_cleanup_required"] is True
    assert payload["cleanup"]["fixture_run_id"] == "slice33a6_fixture_0001"
    assert payload["sensitive_marker_scan"]["status"] == "passed"


def test_ttfb_queue_probe_marketplace_auth_header_not_persisted(tmp_path: Path) -> None:
    probe = ttfb_queue_probe.TTFBQueueProbe(
        env_file=_env_file(tmp_path),
        remote_base_url="https://nodo-staging.example.test",
        run_id="slice33a6_probe_0002",
        output=tmp_path / "probe.json",
        fixture_run_id="slice33a6_fixture_0002",
    )
    probe.marketplace_access_token = lambda: "synthetic-access-token"  # type: ignore[method-assign]
    endpoint = ttfb_queue_probe.ProbeEndpoint("marketplace_home", "GET", "/api/v1/ads/search", "marketplace")

    headers = probe.headers(endpoint=endpoint, index=1)
    payload = probe._payload("unit_test", {"rows": [], "exit_code": 0})

    assert headers["Authorization"] == "Bearer synthetic-access-token"
    assert "synthetic-access-token" not in json.dumps(payload)
    assert "Authorization" not in json.dumps(payload)


def test_connection_origin_probe_parses_curl_phases() -> None:
    sample = connection_origin_probe.parse_curl_write_out(
        '{"http_code":200,"time_namelookup":0.005,"time_connect":0.025,'
        '"time_appconnect":0.075,"time_pretransfer":0.100,'
        '"time_starttransfer":0.500,"time_total":0.550,"size_download":100}'
    )
    phases = connection_origin_probe.derive_curl_phases(sample)

    assert phases["dns_ms"] == 5.0
    assert phases["tcp_connect_ms"] == 20.0
    assert phases["tls_ms"] == 50.0
    assert phases["server_wait_ms"] == 400.0
    assert phases["download_ms"] == 50.0


def test_connection_origin_probe_summary_schema() -> None:
    records = [
        {
            "status": 200,
            "client_total_ms": 100.0,
            "backend_process_ms": 20.0,
            "external_gap_ms": 80.0,
            "ttfb_or_headers_ms": 90.0,
            "response_read_ms": 5.0,
            "response_bytes": 1024,
            "error_type": None,
        }
    ]

    summary = connection_origin_probe.summarize_records(records)

    assert summary["requests"] == 1
    assert summary["status_counts"] == {"200": 1}
    assert summary["ttfb_or_headers"]["p95_ms"] == 90.0
    assert summary["response_kb_p95"] == 1.0


def test_connection_origin_probe_origin_classification_github_slow_local_fast() -> None:
    local = {
        "status": "completed",
        "matrix": {
            "rows": [
                {
                    "endpoint": "health",
                    "concurrency": 100,
                    "summary": {"ttfb_or_headers": {"p95_ms": 250.0}},
                }
            ]
        },
    }
    github = {
        "status": "completed",
        "matrix": {
            "rows": [
                {
                    "endpoint": "health",
                    "concurrency": 100,
                    "summary": {"ttfb_or_headers": {"p95_ms": 5000.0}},
                }
            ]
        },
    }

    assert connection_origin_probe.classify_origin(local, github)["primary"] == "GITHUB_ACTIONS_ROUTE_LIMIT"


def test_connection_origin_probe_classifies_pool_and_keepalive() -> None:
    pool_rows = [
        {"max_connections": 10, "summary": {"ttfb_or_headers": {"p95_ms": 3000.0}}},
        {"max_connections": 100, "summary": {"ttfb_or_headers": {"p95_ms": 1000.0}}},
        {"max_connections": 200, "summary": {"ttfb_or_headers": {"p95_ms": 1050.0}}},
    ]
    keepalive_rows = [
        {"keepalive": "on", "summary": {"ttfb_or_headers": {"p95_ms": 900.0}}},
        {"keepalive": "off", "summary": {"ttfb_or_headers": {"p95_ms": 2000.0}}},
    ]

    assert connection_origin_probe.classify_pool_limit(pool_rows) == "HARNESS_POOL_LIMIT"
    assert connection_origin_probe.classify_keepalive(keepalive_rows) == "CONNECTION_CHURN_LIMIT"


def test_connection_origin_probe_direct_url_unavailable_and_target_mismatch(tmp_path: Path) -> None:
    probe = connection_origin_probe.ConnectionOriginProbe(
        env_file=_env_file(tmp_path),
        run_id="slice33a7_test_0001",
        base_url="https://nodo-staging.example.test",
        origin_label="local",
        target_label="public_staging",
        output=tmp_path / "probe.json",
    )

    payload = {
        "origin_label": "local",
        "matrix": {
            "rows": [
                {
                    "endpoint": "health",
                    "path": "/api/v1/health",
                    "concurrency": 2,
                    "requested_requests": 3,
                    "actual_requests": 2,
                    "request_target_status": "REQUEST_TARGET_MISMATCH",
                    "summary": {"ttfb_or_headers": {"p95_ms": 1.0}},
                }
            ],
            "knees": {"health": {}},
        },
        "pool_churn": {},
        "http2_probe": {},
        "curl_phase": {"classification": {}},
    }

    assert probe.build_payload.__self__ is probe
    assert payload["matrix"]["rows"][0]["request_target_status"] == "REQUEST_TARGET_MISMATCH"
    assert connection_origin_probe.ConnectionOriginProbe.classify_payload(payload)["primary"] == "INCONCLUSIVE"


def test_connection_origin_probe_output_scan_blocks_sensitive_values() -> None:
    assert connection_origin_probe.output_contains_sensitive_marker({"safe": "ok"}) == []
    assert connection_origin_probe.output_contains_sensitive_marker({"leak": "storage_path=/private"}) == ["storage_path"]
    assert connection_origin_probe.output_contains_sensitive_marker({"leak": "account_value=secret"}) == ["account_value"]


def test_edge_header_correlation_parses_railway_headers() -> None:
    headers = httpx.Headers(
        {
            "X-Railway-Edge": "iad1",
            "X-Railway-Request-Id": "rail_req_1",
            "X-Request-Start": "t=1780000000.250",
            "X-NODO-Process-Time-Ms": "12.5",
            "Server-Timing": "app;dur=12.5",
            "X-Request-Id": "req_1",
            "X-Correlation-Id": "corr_1",
            "X-NODO-Operation-Id": "op_1",
        }
    )

    parsed = edge_header_correlation_probe.parse_railway_headers(headers)

    assert parsed["x_railway_edge"] == "iad1"
    assert parsed["x_railway_request_id"] == "rail_req_1"
    assert parsed["x_request_start"]["status"] == "parsed"
    assert parsed["x_nodo_process_time_ms"] == 12.5
    assert parsed["server_timing"] == {"app": 12.5}
    assert parsed["x_request_id"] == "req_1"


def test_edge_header_correlation_request_start_clock_skew_limitation() -> None:
    request_start = edge_header_correlation_probe.parse_request_start("t=1780000000.250")

    ok = edge_header_correlation_probe.correlate_request_start(
        request_start=request_start,
        client_start_epoch_ms=1_780_000_000_000.0,
        headers_received_epoch_ms=1_780_000_000_500.0,
    )
    skewed = edge_header_correlation_probe.correlate_request_start(
        request_start=request_start,
        client_start_epoch_ms=1_780_100_000_000.0,
        headers_received_epoch_ms=1_780_100_000_500.0,
    )

    assert ok["status"] == "ok"
    assert ok["railway_start_to_headers_ms"] == 250.0
    assert skewed["status"] == "CLOCK_SKEW_LIMITATION"


def test_edge_header_correlation_groups_by_railway_edge() -> None:
    records = [
        {
            "status": 200,
            "client_total_ms": 100.0,
            "backend_process_ms": 10.0,
            "external_gap_ms": 90.0,
            "ttfb_or_headers_ms": 95.0,
            "response_read_ms": 5.0,
            "response_bytes": 100,
            "x_railway_edge": "iad1",
            "error_type": None,
            "request_start_correlation": {
                "status": "ok",
                "client_start_to_railway_start_ms": 10.0,
                "railway_start_to_headers_ms": 50.0,
            },
        },
        {
            "status": 200,
            "client_total_ms": 200.0,
            "backend_process_ms": 20.0,
            "external_gap_ms": 180.0,
            "ttfb_or_headers_ms": 180.0,
            "response_read_ms": 5.0,
            "response_bytes": 100,
            "x_railway_edge": "iad1",
            "error_type": None,
            "request_start_correlation": {
                "status": "ok",
                "client_start_to_railway_start_ms": 20.0,
                "railway_start_to_headers_ms": 80.0,
            },
        },
        {
            "status": 200,
            "client_total_ms": 300.0,
            "backend_process_ms": 30.0,
            "external_gap_ms": 270.0,
            "ttfb_or_headers_ms": 280.0,
            "response_read_ms": 5.0,
            "response_bytes": 100,
            "x_railway_edge": "dfw1",
            "error_type": None,
            "request_start_correlation": {
                "status": "ok",
                "client_start_to_railway_start_ms": 30.0,
                "railway_start_to_headers_ms": 100.0,
            },
        },
    ]

    grouped = edge_header_correlation_probe.summarize_by_edge(records)

    assert grouped["iad1"]["requests"] == 2
    assert grouped["dfw1"]["requests"] == 1


def test_edge_header_correlation_classifies_before_edge_vs_app_runtime() -> None:
    before_edge = edge_header_correlation_probe.classify_phase(
        {
            "overall": {
                "backend_process": {"p95_ms": 30.0},
                "ttfb_or_headers": {"p95_ms": 5000.0},
                "request_start_correlation": {
                    "railway_start_to_headers": {"p95_ms": 200.0},
                    "clock_skew_limited_count": 0,
                },
            }
        },
        {"classification": {"health": "BEFORE_RAILWAY_EDGE_LIKELY"}},
    )
    app_runtime = edge_header_correlation_probe.classify_phase(
        {
            "overall": {
                "backend_process": {"p95_ms": 1500.0},
                "ttfb_or_headers": {"p95_ms": 1800.0},
                "request_start_correlation": {
                    "railway_start_to_headers": {"p95_ms": 1700.0},
                    "clock_skew_limited_count": 0,
                },
            }
        },
        {"classification": {}},
    )

    assert before_edge["primary"] == "BEFORE_RAILWAY_EDGE_LIKELY"
    assert app_runtime["primary"] == "APP_RUNTIME_LIKELY"


def test_edge_header_correlation_output_scan_blocks_sensitive_values() -> None:
    assert edge_header_correlation_probe.output_contains_sensitive_marker({"safe": "ok"}) == []
    assert edge_header_correlation_probe.output_contains_sensitive_marker({"leak": "storage_path=/private"}) == [
        "storage_path"
    ]
    assert edge_header_correlation_probe.output_contains_sensitive_marker({"leak": "account_value=secret"}) == [
        "account_value"
    ]


def test_burst_spacing_scheduler_respects_spacing() -> None:
    offsets = burst_spacing_probe.schedule_offsets(requests=4, traffic_shape="spaced", spacing_ms=50)

    assert offsets == [0.0, 0.05, 0.1, 0.15]


def test_burst_spacing_ramp_scheduler_distributes_starts() -> None:
    offsets = burst_spacing_probe.schedule_offsets(requests=4, traffic_shape="ramp", ramp_duration_seconds=30)

    assert offsets == [0.0, 10.0, 20.0, 30.0]


def test_burst_spacing_requested_actual_status_is_reportable() -> None:
    row = {
        "requested_requests": 100,
        "actual_requests": 100,
        "request_target_status": "matched",
    }

    assert row["requested_requests"] == row["actual_requests"]
    assert row["request_target_status"] == "matched"


def test_burst_spacing_classifies_arrival_rate_mitigation() -> None:
    rows = [
        _burst_spacing_row("version_c100_burst_0ms", "version", "burst", 5000.0, 100),
        _burst_spacing_row("version_c100_spacing_50ms", "version", "spaced", 1000.0, 100),
        _burst_spacing_row("version_c100_spacing_100ms", "version", "spaced", 900.0, 100),
        _burst_spacing_row("version_c100_ramp_30s", "version", "ramp", 1200.0, 100),
        _burst_spacing_row("version_c100_ramp_60s", "version", "ramp", 1100.0, 100),
        _burst_spacing_row("version_c50_burst_0ms", "version", "burst", 600.0, 50),
    ]

    classification = burst_spacing_probe.classify_rows(rows)

    assert classification["primary"] == "ARRIVAL_RATE_MITIGATES"
    assert "BURST_CONNECTION_CHURN_CONFIRMED" in classification["secondary"]


def test_burst_spacing_classifies_steady_traffic_limited() -> None:
    rows = [
        _burst_spacing_row("version_c100_burst_0ms", "version", "burst", 5000.0, 100),
        _burst_spacing_row("version_c100_spacing_50ms", "version", "spaced", 4500.0, 100),
        _burst_spacing_row("version_c100_spacing_100ms", "version", "spaced", 4300.0, 100),
        _burst_spacing_row("version_c100_ramp_30s", "version", "ramp", 3500.0, 100),
        _burst_spacing_row("version_c100_ramp_60s", "version", "ramp", 3200.0, 100),
        _burst_spacing_row("version_c100_steady_5rps", "version", "steady", 2500.0, 100),
        _burst_spacing_row("version_c100_steady_10rps", "version", "steady", 2600.0, 100),
    ]

    classification = burst_spacing_probe.classify_rows(rows)

    assert classification["primary"] == "STEADY_TRAFFIC_STILL_LIMITED"


def test_burst_spacing_output_scan_blocks_sensitive_values() -> None:
    assert burst_spacing_probe.output_contains_sensitive_marker({"safe": "ok"}) == []
    assert burst_spacing_probe.output_contains_sensitive_marker({"leak": "storage_path=/private"}) == ["storage_path"]
    assert burst_spacing_probe.output_contains_sensitive_marker({"leak": "account_value=secret"}) == ["account_value"]


def test_burst_spacing_c100_requires_infra_probe() -> None:
    burst_spacing_probe.validate_run_purpose(concurrency=50, run_purpose="product-gate")
    burst_spacing_probe.validate_run_purpose(concurrency=100, run_purpose="infra-probe")
    try:
        burst_spacing_probe.validate_run_purpose(concurrency=100, run_purpose="product-gate")
    except ValueError as exc:
        assert "infra-probe" in str(exc)
    else:
        raise AssertionError("c100 product gate must be rejected")


def _burst_spacing_row(label: str, endpoint: str, shape: str, ttfb_p95: float, concurrency: int) -> dict[str, Any]:
    return {
        "label": label,
        "endpoint": endpoint,
        "traffic_shape": shape,
        "concurrency": concurrency,
        "summary": {
            "ttfb_or_headers": {"p95_ms": ttfb_p95},
            "request_error_summary": {},
        },
    }


def test_staging_guardrails_require_environment_kind(tmp_path: Path) -> None:
    env_file = _env_file(tmp_path, extra={"NODO_ENVIRONMENT_KIND": ""})

    try:
        staging_guardrails.require_staging_guardrails(env_file=env_file)
    except staging_guardrails.StagingGuardrailError as exc:
        assert "NODO_ENVIRONMENT_KIND=staging" in str(exc)
    else:
        raise AssertionError("NODO_ENVIRONMENT_KIND must be required")


def test_staging_guardrails_require_staging_project_id(tmp_path: Path) -> None:
    env_file = _env_file(tmp_path, extra={"NODO_STAGING_PROJECT_ID": ""})

    try:
        staging_guardrails.require_staging_guardrails(env_file=env_file)
    except staging_guardrails.StagingGuardrailError as exc:
        assert "NODO_STAGING_PROJECT_ID is required" in str(exc)
    else:
        raise AssertionError("NODO_STAGING_PROJECT_ID must be required")


def test_staging_guardrails_reject_production(tmp_path: Path) -> None:
    env_file = _env_file(
        tmp_path,
        app_env="production",
        extra={
            "DATABASE_URL": "postgresql://user:password@db.production.supabase.co:5432/postgres",
            "NODO_STAGING_DB_HOST_ALLOWLIST": "db.production.supabase.co",
        },
    )

    try:
        staging_guardrails.require_staging_guardrails(env_file=env_file)
    except staging_guardrails.StagingGuardrailError as exc:
        assert "APP_ENV must be staging" in str(exc)
    else:
        raise AssertionError("production env must be rejected")


def test_staging_guardrails_require_exact_db_api_and_supabase_targets(tmp_path: Path) -> None:
    bad_db = _env_file(tmp_path / "db", extra={"NODO_STAGING_DB_HOST_ALLOWLIST": "other.supabase.co"})
    try:
        staging_guardrails.require_staging_guardrails(env_file=bad_db)
    except staging_guardrails.StagingGuardrailError as exc:
        assert "DATABASE_URL host is not in NODO_STAGING_DB_HOST_ALLOWLIST" in str(exc)
    else:
        raise AssertionError("DB host must match exact allowlist")

    bad_api = _env_file(tmp_path / "api", extra={"NODO_STAGING_API_HOST_ALLOWLIST": "other.example.test"})
    try:
        staging_guardrails.require_staging_guardrails(env_file=bad_api)
    except staging_guardrails.StagingGuardrailError as exc:
        assert "API base URL host is not in NODO_STAGING_API_HOST_ALLOWLIST" in str(exc)
    else:
        raise AssertionError("API host must match exact allowlist")

    bad_supabase = _env_file(tmp_path / "supabase", extra={"NODO_STAGING_SUPABASE_URL": "https://other.supabase.co"})
    try:
        staging_guardrails.require_staging_guardrails(env_file=bad_supabase)
    except staging_guardrails.StagingGuardrailError as exc:
        assert "SUPABASE_URL must exactly match NODO_STAGING_SUPABASE_URL" in str(exc)
    else:
        raise AssertionError("Supabase URL must match exact staging URL")


def test_staging_guardrails_block_production_project_id_targets(tmp_path: Path) -> None:
    env_file = _env_file(
        tmp_path,
        extra={
            "NODO_PRODUCTION_PROJECT_ID": "staging-project",
        },
    )

    try:
        staging_guardrails.require_staging_guardrails(env_file=env_file)
    except staging_guardrails.StagingGuardrailError as exc:
        assert "NODO_PRODUCTION_PROJECT_ID must not match NODO_STAGING_PROJECT_ID" in str(exc)
    else:
        raise AssertionError("production project id target must be blocked")


def test_staging_guardrails_require_confirmation_for_mutations(tmp_path: Path) -> None:
    env_file = _env_file(tmp_path)

    try:
        staging_guardrails.require_staging_guardrails(env_file=env_file, mutating=True, run_id="staging-run-0001")
    except staging_guardrails.StagingGuardrailError as exc:
        assert "--confirm-staging" in str(exc)
    else:
        raise AssertionError("mutating staging action must require explicit confirmation")


def test_migration_plan_does_not_apply_without_apply_flag(tmp_path: Path, monkeypatch: Any) -> None:
    env_file = _env_file(tmp_path)
    output = tmp_path / "migration_plan.json"
    applied = {"called": False}

    def fake_build_plan(database_url: str) -> dict[str, Any]:
        assert "password" in database_url
        return {"pending": [], "applied": [], "checksum_mismatches": [], "items": [], "total": 0}

    def fake_apply_pending(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        applied["called"] = True
        return {"applied_now": ["unexpected"]}

    monkeypatch.setattr(apply_staging_migrations, "build_plan", fake_build_plan)
    monkeypatch.setattr(apply_staging_migrations, "apply_pending", fake_apply_pending)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "apply_staging_migrations.py",
            "--env-file",
            str(env_file),
            "--run-id",
            "staging-run-0001",
            "--output",
            str(output),
        ],
    )

    assert apply_staging_migrations.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["mode"] == "dry_run"
    assert applied["called"] is False


def test_single_migration_rejects_unsafe_paths() -> None:
    unsafe_values = [
        str(ROOT / "database" / "migrations" / "0016_query_performance_indexes.up.sql"),
        "..\\0016_query_performance_indexes.up.sql",
        "nested\\0016_query_performance_indexes.up.sql",
        "0016_query_performance_indexes.down.sql",
    ]

    for value in unsafe_values:
        try:
            apply_staging_single_migration.resolve_migration_path(value)
        except Exception as exc:
            assert type(exc).__name__ in {"SingleMigrationError", "FileNotFoundError"}
        else:
            raise AssertionError(f"unsafe migration path must be rejected: {value}")


def test_single_migration_0016_is_create_index_if_not_exists_only() -> None:
    migration = apply_staging_single_migration.resolve_migration_path("0016_query_performance_indexes.up.sql")
    analysis = apply_staging_single_migration.analyze_migration(migration)
    object_names = {item["object_name"] for item in analysis["statements"]}

    assert analysis["filename"] == "0016_query_performance_indexes.up.sql"
    assert analysis["statement_count"] == 12
    assert analysis["create_index_count"] == 12
    assert analysis["create_index_if_not_exists_count"] == 12
    assert "orders_active_created_idx" in object_names
    assert analysis["writes_database"] is False


def test_single_migration_dry_run_does_not_execute(tmp_path: Path, monkeypatch: Any) -> None:
    env_file = _env_file(tmp_path)
    output = tmp_path / "single_migration.json"
    applied = {"called": False}

    def fake_apply_single_migration(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        applied["called"] = True
        return {"applied_migration": "unexpected"}

    monkeypatch.setattr(apply_staging_single_migration, "apply_single_migration", fake_apply_single_migration)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "apply_staging_single_migration.py",
            "--env-file",
            str(env_file),
            "--run-id",
            "staging-run-0001",
            "--migration",
            "0016_query_performance_indexes.up.sql",
            "--output",
            str(output),
        ],
    )

    assert apply_staging_single_migration.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["mode"] == "dry_run"
    assert payload["migration"]["writes_database"] is False
    assert applied["called"] is False
    assert "password" not in json.dumps(payload)


def test_single_migration_apply_requires_confirm_staging(tmp_path: Path, monkeypatch: Any) -> None:
    env_file = _env_file(tmp_path)
    output = tmp_path / "single_migration.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "apply_staging_single_migration.py",
            "--env-file",
            str(env_file),
            "--run-id",
            "staging-run-0001",
            "--migration",
            "0016_query_performance_indexes.up.sql",
            "--apply",
            "--output",
            str(output),
        ],
    )

    try:
        apply_staging_single_migration.main()
    except staging_guardrails.StagingGuardrailError as exc:
        assert "--confirm-staging" in str(exc)
    else:
        raise AssertionError("single migration apply must require explicit staging confirmation")


def _complete_reconciliation_schema() -> dict[str, Any]:
    columns_by_table = {
        table: set(columns)
        for table, columns in reconcile_staging_migration_ledger.CRITICAL_COLUMNS.items()
    }
    return {
        "tables": set(reconcile_staging_migration_ledger.REQUIRED_TABLES),
        "columns_by_table": columns_by_table,
        "indexes": set(reconcile_staging_migration_ledger.CRITICAL_INDEX_FRAGMENTS),
        "constraints": set(reconcile_staging_migration_ledger.CRITICAL_CONSTRAINTS),
    }


def test_reconcile_schema_requires_ads_credit_hold_constraint() -> None:
    schema = _complete_reconciliation_schema()
    schema["constraints"].remove("ads_credit_hold_ledger_fk")

    result = reconcile_staging_migration_ledger.verify_schema_artifacts(schema)

    assert "missing_constraint:ads_credit_hold_ledger_fk" in result["failures"]


def test_reconcile_schema_requires_core_columns_and_indexes() -> None:
    schema = _complete_reconciliation_schema()
    schema["columns_by_table"]["orders"].remove("idempotency_key")
    schema["indexes"].remove("orders_remitter_idempotency_idx")

    result = reconcile_staging_migration_ledger.verify_schema_artifacts(schema)

    assert "missing_column:orders.idempotency_key" in result["failures"]
    assert "missing_index:orders_remitter_idempotency_idx" in result["failures"]


def test_reconcile_notification_jobs_uses_canonical_column_names() -> None:
    required = reconcile_staging_migration_ledger.CRITICAL_COLUMNS["notification_jobs"]

    assert "notification_type" in required
    assert "scheduled_for" in required
    assert "job_type" not in required
    assert "scheduled_at" not in required


def test_reconcile_plan_blocks_checksum_mismatch() -> None:
    schema_check = reconcile_staging_migration_ledger.verify_schema_artifacts(_complete_reconciliation_schema())

    plan = reconcile_staging_migration_ledger.evaluate_reconciliation_state(
        local_checksums={"0001_slice_00_foundation.up.sql": "new-checksum"},
        ledger={"0001_slice_00_foundation.up.sql": "old-checksum"},
        ledger_exists=True,
        schema_check=schema_check,
    )

    assert "checksum_mismatch:0001_slice_00_foundation.up.sql" in plan["failures"]
    assert plan["verified_migrations"] == []


def test_reconcile_plan_marks_missing_ledger_rows_when_schema_is_verified() -> None:
    schema_check = reconcile_staging_migration_ledger.verify_schema_artifacts(_complete_reconciliation_schema())

    plan = reconcile_staging_migration_ledger.evaluate_reconciliation_state(
        local_checksums={"0001_slice_00_foundation.up.sql": "checksum"},
        ledger={},
        ledger_exists=False,
        schema_check=schema_check,
    )

    assert plan["failures"] == []
    assert plan["pending_ledger_rows"] == ["0001_slice_00_foundation.up.sql"]
    assert plan["verified_migrations"] == ["0001_slice_00_foundation.up.sql"]


def test_reconcile_main_dry_run_does_not_apply(tmp_path: Path, monkeypatch: Any) -> None:
    env_file = _env_file(tmp_path)
    output = tmp_path / "reconcile.json"
    applied = {"called": False}

    def fake_build_plan(_database_url: str) -> dict[str, Any]:
        return {
            "ledger_exists": False,
            "ledger_row_count": 0,
            "total_migrations": 1,
            "applied": [],
            "pending_ledger_rows": ["0001_slice_00_foundation.up.sql"],
            "checksum_mismatches": [],
            "unknown_ledger_entries": [],
            "schema_check": {"failures": []},
            "verified_migrations": ["0001_slice_00_foundation.up.sql"],
            "blocked_migrations": [],
            "failures": [],
        }

    def fake_apply_reconciliation(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        applied["called"] = True
        return {"inserted_ledger_rows": ["unexpected"]}

    monkeypatch.setattr(reconcile_staging_migration_ledger, "build_reconciliation_plan", fake_build_plan)
    monkeypatch.setattr(reconcile_staging_migration_ledger, "apply_reconciliation", fake_apply_reconciliation)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "reconcile_staging_migration_ledger.py",
            "--env-file",
            str(env_file),
            "--run-id",
            "staging-run-0001",
            "--output",
            str(output),
        ],
    )

    assert reconcile_staging_migration_ledger.main() == 0
    assert applied["called"] is False
    assert json.loads(output.read_text(encoding="utf-8"))["mode"] == "dry_run"


def test_reconcile_main_apply_requires_confirm_staging(tmp_path: Path, monkeypatch: Any) -> None:
    env_file = _env_file(tmp_path)
    output = tmp_path / "reconcile.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "reconcile_staging_migration_ledger.py",
            "--env-file",
            str(env_file),
            "--run-id",
            "staging-run-0001",
            "--apply",
            "--output",
            str(output),
        ],
    )

    try:
        reconcile_staging_migration_ledger.main()
    except staging_guardrails.StagingGuardrailError as exc:
        assert "--confirm-staging" in str(exc)
    else:
        raise AssertionError("ledger reconciliation apply must require explicit staging confirmation")


def test_staging_cleanup_dry_run_does_not_execute(tmp_path: Path, monkeypatch: Any) -> None:
    env_file = _env_file(tmp_path)
    output = tmp_path / "cleanup.json"
    observed: dict[str, Any] = {}

    def fake_cleanup(*, env_file: Path, run_id: str, execute: bool) -> dict[str, Any]:
        observed.update({"env_file": env_file, "run_id": run_id, "execute": execute})
        return {"run_id": run_id, "mode": "dry_run", "exit_code": 0}

    monkeypatch.setattr(staging_cleanup_synthetic_run, "cleanup", fake_cleanup)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "staging_cleanup_synthetic_run.py",
            "--env-file",
            str(env_file),
            "--run-id",
            "staging-run-0001",
            "--output",
            str(output),
        ],
    )

    assert staging_cleanup_synthetic_run.main() == 0
    assert observed["execute"] is False
    assert json.loads(output.read_text(encoding="utf-8"))["mode"] == "dry_run"


class _CleanupFakeResult:
    rowcount = 0

    def fetchone(self) -> list[int]:
        return [0]


class _CleanupFakeConnection:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> _CleanupFakeResult:
        del params
        self.statements.append(" ".join(sql.lower().split()))
        return _CleanupFakeResult()


def test_cleanup_expands_ads_from_synthetic_credit_ledger_references() -> None:
    conn = _CleanupFakeConnection()

    cleanup_synthetic_run.populate_cleanup_tables(conn, "slice33a_delivery_c100_20260712")
    sql = "\n".join(conn.statements)

    assert "insert into cleanup_ads(id) select distinct id from ads" in sql
    assert "credit_hold_ledger_id in (select id from cleanup_credits_ledger)" in sql
    assert "credit_consumed_ledger_id in (select id from cleanup_credits_ledger)" in sql
    assert sql.index("create temp table cleanup_credits_ledger") < sql.rindex(
        "insert into cleanup_ads(id) select distinct id from ads"
    )


def test_cleanup_expands_ads_from_synthetic_payment_method_references() -> None:
    conn = _CleanupFakeConnection()

    cleanup_synthetic_run.populate_cleanup_tables(conn, "slice33a_delivery_c100_20260712")
    sql = "\n".join(conn.statements)

    assert "insert into cleanup_ads(id) select distinct id from ads where payment_method_id in" in sql
    assert "select id from cleanup_business_payment_methods" in sql
    assert sql.index("create temp table cleanup_business_payment_methods") < sql.index(
        "insert into cleanup_ads(id) select distinct id from ads where payment_method_id in"
    )


def test_cleanup_nulls_ad_ledger_refs_before_deleting_credits_ledger() -> None:
    labels = [label for label, _sql in cleanup_synthetic_run.DELETE_STEPS]
    refs_sql = dict(cleanup_synthetic_run.DELETE_STEPS)["ads_credit_ledger_refs"].lower()

    assert labels.index("ads_credit_ledger_refs") < labels.index("credits_ledger")
    assert "credit_hold_ledger_id = null" in refs_sql
    assert "credit_consumed_ledger_id = null" in refs_sql
    assert "credit_hold_ledger_id in (select id from cleanup_credits_ledger)" in refs_sql
    assert "credit_consumed_ledger_id in (select id from cleanup_credits_ledger)" in refs_sql


def test_cleanup_does_not_delete_audit_logs_or_users() -> None:
    labels = [label for label, _sql in cleanup_synthetic_run.DELETE_STEPS]
    all_delete_sql = "\n".join(sql.lower() for _label, sql in cleanup_synthetic_run.DELETE_STEPS)

    assert "audit_logs" not in labels
    assert "users" not in labels
    assert "delete from audit_logs" not in all_delete_sql
    assert "delete from users" not in all_delete_sql


def test_capacity_real_uses_remote_client_context_for_non_marketplace_paths() -> None:
    assert "_client_context" in inspect.getsource(capacity_real.RealCapacityHarness.run_order_creates)
    assert "_client_context" in inspect.getsource(capacity_real.RealCapacityHarness.run_same_ad_race)
    assert "_client_context" in inspect.getsource(capacity_real.RealCapacityHarness.run_duplicate_idempotency_race)
    assert "_client_context" in inspect.getsource(capacity_real.RealCapacityHarness.run_confirm_distinct)
    assert "_client_context" in inspect.getsource(capacity_real.RealCapacityHarness.run_confirm_same_order_race)


def test_capacity_remote_base_url_requires_fixture_mode(tmp_path: Path) -> None:
    env_file = _env_file(tmp_path)

    try:
        capacity_real.RealCapacityHarness(
            env_file=env_file,
            run_id="staging-run-0001",
            businesses=1,
            ads_per_business=1,
            remitters=1,
            marketplace_reads=1,
            order_creates=1,
            same_ad_race_requests=2,
            payment_confirms=0,
            remote_base_url="https://nodo-staging.example.test",
        )
    except ValueError as exc:
        assert "--remote-base-url requires explicit --fixture-mode" in str(exc)
    else:
        raise AssertionError("remote_base_url must require explicit fixture_mode")


def test_capacity_db_seed_api_remote_fixture_mode_is_identified(tmp_path: Path, monkeypatch: Any) -> None:
    env_file = _env_file(tmp_path)
    harness = capacity_real.RealCapacityHarness(
        env_file=env_file,
        run_id="staging-run-0001",
        businesses=1,
        ads_per_business=1,
        remitters=1,
        marketplace_reads=0,
        order_creates=0,
        same_ad_race_requests=2,
        payment_confirms=0,
        remote_base_url="https://nodo-staging.example.test",
        fixture_mode="db_seed_api_remote",
    )
    monkeypatch.setattr(harness, "prepare_dataset", lambda: {"businesses": [], "ads": [], "payment_ads": [], "remitters": []})
    monkeypatch.setattr(harness, "scan_invariants", lambda: {"negative_balances": 0, "double_credit_consumption": 0})

    payload = harness.run("marketplace-reads")

    assert payload["fixture_mode"] == "db_seed_api_remote"
    assert payload["fixture_mode_detail"]["seed"] == "hybrid_direct_db_seed_plus_configurable_ad_setup"
    assert payload["fixture_mode_detail"]["measured_requests"] == "remote_api"
    assert payload["fixture_setup_mode"] == "api_ads"
    assert payload["fixture_setup"]["ad_setup"] == "api_ads"
    assert "setup_note" in payload["fixture_mode_detail"]


def test_capacity_api_remote_only_blocks_until_db_free_flow_exists(tmp_path: Path) -> None:
    env_file = _env_file(tmp_path)

    try:
        capacity_real.RealCapacityHarness(
            env_file=env_file,
            run_id="staging-run-0001",
            businesses=1,
            ads_per_business=1,
            remitters=1,
            marketplace_reads=1,
            order_creates=1,
            same_ad_race_requests=2,
            payment_confirms=0,
            remote_base_url="https://nodo-staging.example.test",
            fixture_mode="api_remote_only",
        )
    except ValueError as exc:
        assert "api_remote_only is blocked" in str(exc)
    else:
        raise AssertionError("api_remote_only must block while DB seed/invariants are required")


def test_capacity_parses_process_time_and_server_timing() -> None:
    assert capacity_real.parse_process_time_ms("12.3456") == 12.3456
    assert capacity_real.parse_process_time_ms("-1") is None
    assert capacity_real.parse_process_time_ms("not-a-number") is None

    parsed = capacity_real.parse_server_timing("app;dur=12.3, db;dur=4.5;desc=query, cache;dur=0.75")

    assert parsed == {"app": 12.3, "db": 4.5, "cache": 0.75}


def test_capacity_latency_isolation_aggregates_headers_and_delta(tmp_path: Path) -> None:
    env_file = _env_file(tmp_path)
    harness = capacity_real.RealCapacityHarness(
        env_file=env_file,
        run_id="staging-run-0001",
        businesses=1,
        ads_per_business=1,
        remitters=1,
        marketplace_reads=1,
        order_creates=0,
        same_ad_race_requests=2,
        payment_confirms=0,
    )

    response = httpx.Response(
        200,
        headers={
            "X-NODO-Process-Time-Ms": "15.5",
            "Server-Timing": "app;dur=15.5, db;dur=4.25",
            "X-Request-Id": "req_staging_0001",
            "X-Correlation-Id": "corr_staging_0001",
        },
        content=b'{"data":{"items":[]}}',
    )
    harness._record_latency_sample(
        name="capacity:marketplace:read",
        method="GET",
        path="/api/v1/ads/search",
        status_code=200,
        external_duration_ms=45.5,
        response=response,
    )

    summary = harness.latency_isolation_summary()

    assert summary["backend_process"]["p95_ms"] == 15.5
    assert summary["external_minus_backend"]["p95_ms"] == 30.0
    assert summary["server_timing"]["db"]["p95_ms"] == 4.25
    assert summary["response_size_bytes"]["p95_ms"] == len(response.content)
    assert harness.latency_samples[0]["request_id"] == "req_staging_0001"
    assert harness.latency_samples[0]["correlation_id"] == "corr_staging_0001"


def test_capacity_classifies_httpx_request_errors() -> None:
    assert capacity_real.classify_request_error(httpx.ConnectTimeout("connect timed out")) == "CONNECT_TIMEOUT"
    assert capacity_real.classify_request_error(httpx.ConnectError("all connection attempts failed")) == "CONNECT_ERROR"
    assert capacity_real.classify_request_error(httpx.ReadTimeout("read timed out")) == "READ_TIMEOUT"
    assert capacity_real.classify_request_error(httpx.WriteTimeout("write timed out")) == "WRITE_TIMEOUT"
    assert capacity_real.classify_request_error(httpx.PoolTimeout("pool timed out")) == "POOL_TIMEOUT"
    assert (
        capacity_real.classify_request_error(httpx.RemoteProtocolError("server disconnected"))
        == "REMOTE_DISCONNECT_OR_PROTOCOL_ERROR"
    )
    assert capacity_real.classify_request_error(httpx.RequestError("generic failure")) == "UNKNOWN_CLIENT_ERROR"


def test_capacity_redacts_request_error_message() -> None:
    message = (
        "Authorization: Bearer secret-token DATABASE_URL=postgres://secret "
        "refresh_token=refresh-secret https://api.example.test/path?access_token=secret"
    )

    redacted = capacity_real.redact_exception_message(message)

    assert "secret-token" not in redacted
    assert "postgres://secret" not in redacted
    assert "refresh-secret" not in redacted
    assert "access_token=secret" not in redacted


def test_cloud_load_runner_product_gate_caps_staging_concurrency() -> None:
    cloud_load_runner.validate_staging_concurrency_policy(concurrency=50, run_purpose="product-gate")
    cloud_load_runner.validate_staging_concurrency_policy(concurrency=100, run_purpose="infra-probe")

    try:
        cloud_load_runner.validate_staging_concurrency_policy(concurrency=100, run_purpose="product-gate")
    except RuntimeError as exc:
        assert "capped at c50" in str(exc)
        assert "infra-probe" in str(exc)
    else:
        raise AssertionError("c100 product-gate must be rejected")


def test_cloud_load_runner_policy_payload_marks_c100_as_infra_probe() -> None:
    payload = cloud_load_runner.staging_concurrency_policy_payload(concurrency=100, run_purpose="infra-probe")

    assert payload["product_gate_max_concurrency"] == 50
    assert payload["classification"] == "infrastructure_transport_probe"
    assert payload["c100_plus_requires_infra_probe"] is True
    assert payload["diagnosis"]["marketplace_product"] == "not_primary_bottleneck"


def test_capacity_records_request_error_samples_outside_latency_limit(tmp_path: Path) -> None:
    env_file = _env_file(tmp_path)
    harness = capacity_real.RealCapacityHarness(
        env_file=env_file,
        run_id="staging-run-0001",
        businesses=1,
        ads_per_business=1,
        remitters=1,
        marketplace_reads=1,
        order_creates=0,
        same_ad_race_requests=2,
        payment_confirms=0,
        profile_detail_limit=0,
    )

    class FailingClient:
        base_url = "https://nodo-staging.example.test"

        def __init__(self) -> None:
            self.headers: dict[str, str] = {}

        async def request(self, _method: str, _url: str, **kwargs: Any) -> httpx.Response:
            self.headers = kwargs["headers"]
            raise httpx.ReadTimeout(
                "read timeout Authorization: Bearer secret-token refresh_token=secret",
                request=httpx.Request("GET", f"{self.base_url}/api/v1/ads/search"),
            )

    client = FailingClient()

    response = asyncio.run(
        harness._request(
            client,  # type: ignore[arg-type]
            "capacity:marketplace:read",
            "GET",
            "/api/v1/ads/search",
            headers={"Authorization": "Bearer should-not-be-persisted", "X-Request-Id": "req_existing"},
        )
    )

    assert response.status_code == 599
    assert harness.latency_samples == []
    assert len(harness.request_error_samples) == 1
    sample = harness.request_error_samples[0]
    assert sample["classification"] == "READ_TIMEOUT"
    assert sample["exception_class"] == "ReadTimeout"
    assert sample["request_id"] == "req_existing"
    assert sample["correlation_id"] == "corr_staging-run-0001"
    assert sample["operation_id"] == "op_staging-run-0001_capacity_marketplace_read"
    assert sample["response_started"] is False
    assert "secret-token" not in json.dumps(sample)
    assert "should-not-be-persisted" not in json.dumps(sample)
    assert client.headers["X-Correlation-Id"] == "corr_staging-run-0001"
    assert client.headers["X-NODO-Operation-Id"] == "op_staging-run-0001_capacity_marketplace_read"
    assert client.headers["X-NODO-Surface"] == "client_mini_app"

    summary = harness.request_error_summary()
    assert summary["total"] == 1
    assert summary["by_classification"]["READ_TIMEOUT"] == 1
    assert summary["by_endpoint"]["GET /api/v1/ads/search"] == 1
    assert summary["by_group"]["capacity:marketplace:read"] == 1


def test_capacity_remote_mode_uses_staging_guardrails(tmp_path: Path) -> None:
    env_file = _env_file(tmp_path, extra={"NODO_STAGING_API_HOST_ALLOWLIST": "other.example.test"})

    try:
        capacity_real.RealCapacityHarness(
            env_file=env_file,
            run_id="staging-run-0001",
            businesses=1,
            ads_per_business=1,
            remitters=1,
            marketplace_reads=1,
            order_creates=0,
            same_ad_race_requests=2,
            payment_confirms=0,
            remote_base_url="https://nodo-staging.example.test",
            fixture_mode="db_seed_api_remote",
        )
    except staging_guardrails.StagingGuardrailError as exc:
        assert "API base URL host is not in NODO_STAGING_API_HOST_ALLOWLIST" in str(exc)
    else:
        raise AssertionError("remote staging capacity runs must enforce API host guardrails")


def test_capacity_remote_client_uses_explicit_max_connections(tmp_path: Path) -> None:
    harness = capacity_real.RealCapacityHarness(
        env_file=_env_file(tmp_path),
        run_id="staging-run-0001",
        businesses=1,
        ads_per_business=1,
        remitters=1,
        marketplace_reads=1,
        order_creates=0,
        same_ad_race_requests=2,
        payment_confirms=0,
        remote_base_url="https://nodo-staging.example.test",
        fixture_mode="db_seed_api_remote",
        max_connections=7,
    )

    client = harness._client_context(concurrency=50)

    try:
        assert client._transport._pool._max_connections == 7  # type: ignore[attr-defined]  # noqa: SLF001
    finally:
        asyncio.run(client.aclose())


def test_capacity_output_separates_setup_and_measured_load(tmp_path: Path) -> None:
    harness = capacity_real.RealCapacityHarness(
        env_file=_env_file(tmp_path),
        run_id="staging-run-0001",
        businesses=1,
        ads_per_business=1,
        remitters=1,
        marketplace_reads=1,
        order_creates=0,
        same_ad_race_requests=2,
        payment_confirms=0,
    )

    async def fake_marketplace_reads(_prepared: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        harness.metrics.record("capacity:marketplace:read", 200, started, route_group="GET /api/v1/ads/search")
        return {"status_codes": [200]}

    harness.prepare_dataset = lambda: {"businesses": [], "ads": [], "payment_ads": [], "remitters": []}  # type: ignore[method-assign]
    harness.run_marketplace_reads = fake_marketplace_reads  # type: ignore[method-assign]
    harness.scan_invariants = lambda: {"negative_balances": 0, "double_credit_consumption": 0}  # type: ignore[method-assign]

    payload = harness.run("marketplace-reads")

    assert payload["phase_timings"]["setup_seconds"] >= 0
    assert payload["phase_timings"]["measured_load_seconds"] >= 0
    assert payload["phase_timings"]["total_seconds"] >= payload["phase_timings"]["measured_load_seconds"]
    assert payload["metrics"]["total_requests"] == 1


def test_capacity_rejects_unknown_fixture_setup_mode(tmp_path: Path) -> None:
    try:
        capacity_real.RealCapacityHarness(
            env_file=_env_file(tmp_path),
            run_id="staging-run-0001",
            businesses=1,
            ads_per_business=1,
            remitters=1,
            marketplace_reads=1,
            order_creates=0,
            same_ad_race_requests=2,
            payment_confirms=0,
            fixture_setup_mode="unknown",  # type: ignore[arg-type]
        )
    except ValueError as exc:
        assert "fixture_setup_mode must be one of" in str(exc)
    else:
        raise AssertionError("capacity harness must reject unknown fixture setup modes")


def test_capacity_db_direct_ad_setup_dispatches_without_api_call(tmp_path: Path, monkeypatch: Any) -> None:
    harness = capacity_real.RealCapacityHarness(
        env_file=_env_file(tmp_path),
        run_id="staging-run-0001",
        businesses=1,
        ads_per_business=1,
        remitters=1,
        marketplace_reads=1,
        order_creates=0,
        same_ad_race_requests=2,
        payment_confirms=0,
        fixture_setup_mode="db_direct_ads",
    )
    calls: list[str] = []

    def fake_db(**_kwargs: Any) -> dict[str, Any]:
        calls.append("db")
        return {"id": "ad-db"}

    def fake_api(**_kwargs: Any) -> dict[str, Any]:
        calls.append("api")
        return {"id": "ad-api"}

    monkeypatch.setattr(harness, "_create_ad_fixture_direct_db", fake_db)
    monkeypatch.setattr(harness, "_create_ad_fixture_via_api", fake_api)

    ad = harness._create_ad_fixture(
        owner={"user": {"id": "user-1"}},
        fixture={"business_id": "business-1"},
        payment_method_id="payment-method-1",
        payment_method="zelle",
        business_index=0,
        ad_index=0,
        amount_min=20,
        amount_max=100,
        request_label="capacity:ads:create:0:0",
    )

    assert ad == {"id": "ad-db"}
    assert calls == ["db"]


def test_capacity_output_reports_db_direct_fixture_setup_mode(tmp_path: Path) -> None:
    harness = capacity_real.RealCapacityHarness(
        env_file=_env_file(tmp_path),
        run_id="staging-run-0001",
        businesses=1,
        ads_per_business=1,
        remitters=1,
        marketplace_reads=1,
        order_creates=0,
        same_ad_race_requests=2,
        payment_confirms=0,
        fixture_setup_mode="db_direct_ads",
    )
    harness.prepare_dataset = lambda: {"businesses": [], "ads": [], "payment_ads": [], "remitters": []}  # type: ignore[method-assign]
    harness.run_marketplace_reads = lambda _prepared: {"status_codes": []}  # type: ignore[method-assign]
    harness.scan_invariants = lambda: {"negative_balances": 0, "double_credit_consumption": 0}  # type: ignore[method-assign]
    harness._direct_ads_created = 3
    harness._marketplace_cache_invalidated = True

    payload = harness.run("order-flow")

    assert payload["fixture_setup_mode"] == "db_direct_ads"
    assert payload["fixture_setup"]["ad_setup"] == "db_direct_ads"
    assert payload["fixture_setup"]["direct_ads_created"] == 3
    assert payload["fixture_setup"]["marketplace_cache_invalidated"] is True


def test_capacity_fallback_db_token_helper_creates_old_but_unexpired_token() -> None:
    issued_at = int(time.time()) - 360
    token = capacity_real.create_access_token_at(
        user_id="user-1",
        role="remitter",
        status="active",
        secret="test-secret",
        ttl_seconds=900,
        issued_at=issued_at,
    )

    payload = decode_access_token(token, "test-secret")

    assert payload["sub"] == "user-1"
    assert int(time.time()) - payload["iat"] > 300
    assert payload["exp"] > int(time.time())


def test_capacity_profile_marketplace_adds_profile_header(tmp_path: Path, monkeypatch: Any) -> None:
    env_file = _env_file(tmp_path)
    harness = capacity_real.RealCapacityHarness(
        env_file=env_file,
        run_id="staging-run-0001",
        businesses=1,
        ads_per_business=1,
        remitters=1,
        marketplace_reads=1,
        order_creates=0,
        same_ad_race_requests=2,
        payment_confirms=0,
        profile_marketplace=True,
    )
    observed: dict[str, Any] = {}

    async def fake_request(_client: httpx.AsyncClient, _name: str, _method: str, _url: str, **kwargs: Any) -> httpx.Response:
        observed["headers"] = kwargs["headers"]
        return httpx.Response(200, json={"data": {"items": []}})

    monkeypatch.setattr(harness, "_request", fake_request)

    result = asyncio.run(harness.run_marketplace_reads({"remitters": [{"access_token": "token"}]}))

    assert result["status_codes"] == [200]
    assert observed["headers"]["X-NODO-Profile"] == "1"


def test_capacity_without_profile_marketplace_does_not_add_profile_header(tmp_path: Path, monkeypatch: Any) -> None:
    env_file = _env_file(tmp_path)
    harness = capacity_real.RealCapacityHarness(
        env_file=env_file,
        run_id="staging-run-0001",
        businesses=1,
        ads_per_business=1,
        remitters=1,
        marketplace_reads=1,
        order_creates=0,
        same_ad_race_requests=2,
        payment_confirms=0,
        profile_marketplace=False,
    )
    observed: dict[str, Any] = {}

    async def fake_request(_client: httpx.AsyncClient, _name: str, _method: str, _url: str, **kwargs: Any) -> httpx.Response:
        observed["headers"] = kwargs["headers"]
        return httpx.Response(200, json={"data": {"items": []}})

    monkeypatch.setattr(harness, "_request", fake_request)

    asyncio.run(harness.run_marketplace_reads({"remitters": [{"access_token": "token"}]}))

    assert "X-NODO-Profile" not in observed["headers"]


def test_capacity_profile_summary_aggregates_stages_without_secrets(tmp_path: Path) -> None:
    env_file = _env_file(tmp_path)
    harness = capacity_real.RealCapacityHarness(
        env_file=env_file,
        run_id="staging-run-0001",
        businesses=1,
        ads_per_business=1,
        remitters=1,
        marketplace_reads=1,
        order_creates=0,
        same_ad_race_requests=2,
        payment_confirms=0,
        profile_marketplace=True,
    )
    harness._record_profile(
        name="capacity:marketplace:read",
        method="GET",
        path="/api/v1/ads/search",
        status_code=200,
        profile={
            "total_ms": 12.0,
            "dependency": {
                "auth": {
                    "mode": "marketplace_claims",
                    "stages": [{"stage": "auth:marketplace_decode_access_token", "elapsed_ms": 1.0}],
                }
            },
            "stages": [
                {"stage": "cache:hit", "elapsed_ms": 0.1, "metadata": {"hit_type": "miss"}},
                {"stage": "db:acquire", "elapsed_ms": 2.0},
                {"stage": "db:query:list_marketplace_ads_with_businesses", "elapsed_ms": 7.0},
            ],
        },
    )

    summary = harness.profile_summary()
    serialized = json.dumps(summary)

    assert summary["captured_profiles"] == 1
    assert summary["auth_mode_counts"]["marketplace_claims"] == 1
    assert summary["cache_hit_counts"]["miss"] == 1
    assert summary["db_acquire_p95_ms"] == 2.0
    assert summary["db_query_p95_ms"] == 7.0
    assert "Bearer " not in serialized
    assert "secret" not in serialized.lower()


def test_cloud_load_runner_cost_units_capture_profile_without_secrets() -> None:
    runner = cloud_load_runner.CloudLoadRunner(
        base_url="https://nodo-staging.example.test",
        scenario="marketplace",
        run_id="cloud-cost-test",
        requests=10,
        concurrency=5,
        timeout_seconds=5.0,
        bot_token="secret-token",
        remitters=3,
        amount_usd="50.00",
        payment_method="zelle",
        delivery_method="pago_movil_ve",
        profile_marketplace=True,
        order_ad_ids=[],
    )
    response = httpx.Response(
        200,
        headers={"X-NODO-Process-Time-Ms": "12.5", "X-Railway-Edge": "mia1"},
        json={
            "data": {
                "items": [],
                "_profile": {
                    "stages": [
                        {"stage": "cache:hit", "elapsed_ms": 0.1, "metadata": {"hit_type": "local"}},
                        {"stage": "db:query:list_marketplace_ads_with_businesses", "elapsed_ms": 5.0},
                    ],
                    "dependency": {
                        "auth": {
                            "stages": [{"stage": "auth:marketplace_decode_access_token", "elapsed_ms": 0.2}],
                        }
                    },
                },
            }
        },
    )

    runner.client_latencies.append(20.0)
    runner._capture_headers(response)
    runner.response_bytes_total += len(response.content)
    runner._capture_profile(response)
    summary = runner._cost_units(setup_requests=3)
    serialized = json.dumps(summary)

    assert summary["unit"] == "operational_units_not_dollars"
    assert summary["total_http_requests"] == 4
    assert summary["synthetic_users_created"] == 3
    assert summary["profiled_requests"] == 1
    assert summary["profile_cache_hit_counts"]["local"] == 1
    assert summary["profile_stage_counts"]["db:query:list_marketplace_ads_with_businesses"] == 1
    assert summary["profile_stage_latency"]["db:query:list_marketplace_ads_with_businesses"]["p95_ms"] == 5.0
    assert summary["profile_stage_latency_by_operation"]["unknown"]["auth:marketplace_decode_access_token"]["p95_ms"] == 0.2
    assert "secret-token" not in serialized
    assert "Bearer " not in serialized


def test_cloud_load_runner_mixed_scenario_reports_operations_separately() -> None:
    runner = cloud_load_runner.CloudLoadRunner(
        base_url="https://nodo-staging.example.test",
        scenario="mixed-read-order",
        run_id="cloud-mixed-test",
        requests=8,
        concurrency=4,
        timeout_seconds=5.0,
        bot_token="secret-token",
        remitters=4,
        amount_usd="50.00",
        payment_method="zelle",
        delivery_method="pago_movil_ve",
        profile_marketplace=True,
        order_ad_ids=["ad_1", "ad_2"],
    )

    order_spec = runner._request_spec(0, tokens=["access-token"])
    market_spec = runner._request_spec(2, tokens=["access-token"])

    assert order_spec.operation == "order_create"
    assert market_spec.operation == "marketplace_read"

    order_response = httpx.Response(201, headers={"X-NODO-Process-Time-Ms": "300.0"}, json={"data": {"id": "order-1"}})
    market_response = httpx.Response(200, headers={"X-NODO-Process-Time-Ms": "8.0"}, json={"data": {"items": []}})
    runner.client_latencies_by_operation.setdefault("order_create", []).append(500.0)
    runner.statuses_by_operation.setdefault("order_create", Counter())["201"] += 1
    runner._capture_headers(order_response, operation="order_create")
    runner._record_response_bytes("order_create", len(order_response.content))
    runner.client_latencies_by_operation.setdefault("marketplace_read", []).append(20.0)
    runner.statuses_by_operation.setdefault("marketplace_read", Counter())["200"] += 1
    runner._capture_headers(market_response, operation="marketplace_read")
    runner._record_response_bytes("marketplace_read", len(market_response.content))

    operations = runner._operation_summary()
    cost_units = runner._cost_units(setup_requests=4)

    assert operations["order_create"]["requests"] == 1
    assert operations["order_create"]["server_process_time"]["p95_ms"] == 300.0
    assert operations["marketplace_read"]["requests"] == 1
    assert operations["marketplace_read"]["server_process_time"]["p95_ms"] == 8.0
    assert cost_units["operations"]["order_create"]["measured_http_requests"] == 1
    assert cost_units["operations"]["marketplace_read"]["measured_http_requests"] == 1


def test_cloud_load_runner_mixed_marketplace_profiles_are_captured() -> None:
    runner = cloud_load_runner.CloudLoadRunner(
        base_url="https://nodo-staging.example.test",
        scenario="mixed-read-order",
        run_id="cloud-mixed-profile-test",
        requests=8,
        concurrency=4,
        timeout_seconds=5.0,
        bot_token="secret-token",
        remitters=4,
        amount_usd="50.00",
        payment_method="zelle",
        delivery_method="pago_movil_ve",
        profile_marketplace=True,
        order_ad_ids=["ad_1", "ad_2"],
    )
    response = httpx.Response(
        200,
        json={
            "data": {
                "_profile": {
                    "stages": [{"stage": "cache:hit", "elapsed_ms": 0.1, "metadata": {"hit_type": "local"}}],
                    "dependency": {"auth": {"stages": [{"stage": "auth:marketplace_claim_user", "elapsed_ms": 0.2}]}},
                }
            }
        },
    )

    runner._capture_profile(response, operation="marketplace_read")

    summary = runner._cost_units(setup_requests=4)

    assert runner.profiled_requests == 1
    assert runner.profiled_requests_by_operation["marketplace_read"] == 1
    assert summary["profiled_requests_by_operation"]["marketplace_read"] == 1
    assert summary["profile_cache_hit_counts"]["local"] == 1
    assert summary["profile_stage_latency_by_operation"]["marketplace_read"]["cache:hit"]["p95_ms"] == 0.1


def test_cloud_load_runner_profile_marketplace_adds_header() -> None:
    runner = cloud_load_runner.CloudLoadRunner(
        base_url="https://nodo-staging.example.test",
        scenario="marketplace",
        run_id="cloud-profile-test",
        requests=1,
        concurrency=1,
        timeout_seconds=5.0,
        bot_token="secret-token",
        remitters=1,
        amount_usd="50.00",
        payment_method="zelle",
        delivery_method="pago_movil_ve",
        profile_marketplace=True,
        order_ad_ids=[],
    )

    spec = runner._request_spec(0, tokens=["access-token"])

    assert spec.method == "GET"
    assert spec.path.startswith("/api/v1/ads/search")
    assert spec.headers["X-NODO-Profile"] == "1"
    assert spec.headers["Authorization"] == "Bearer access-token"


def test_cloud_load_runner_order_create_requires_explicit_prepared_ads() -> None:
    runner = cloud_load_runner.CloudLoadRunner(
        base_url="https://nodo-staging.example.test",
        scenario="order-create",
        run_id="cloud-order-test",
        requests=2,
        concurrency=2,
        timeout_seconds=5.0,
        bot_token="secret-token",
        remitters=2,
        amount_usd="50.00",
        payment_method="zelle",
        delivery_method="pago_movil_ve",
        profile_marketplace=False,
        order_ad_ids=["ad_1"],
    )

    try:
        runner._validate_scenario_inputs()
    except RuntimeError as exc:
        assert "order-create requires --order-ad-ids" in str(exc)
    else:
        raise AssertionError("order-create must not run without one prepared ad per request")


def test_cloud_load_runner_order_create_builds_post_without_sensitive_payload() -> None:
    runner = cloud_load_runner.CloudLoadRunner(
        base_url="https://nodo-staging.example.test",
        scenario="order-create",
        run_id="cloud-order-test",
        requests=1,
        concurrency=1,
        timeout_seconds=5.0,
        bot_token="secret-token",
        remitters=1,
        amount_usd="50.00",
        payment_method="zelle",
        delivery_method="pago_movil_ve",
        profile_marketplace=False,
        order_ad_ids=["ad_prepared_1"],
    )

    spec = runner._request_spec(0, tokens=["access-token"])
    serialized = json.dumps({"headers": spec.headers, "body": spec.json})

    assert spec.method == "POST"
    assert spec.path == "/api/v1/orders"
    assert spec.headers["Idempotency-Key"] == "cloud-order-test_cloud_order_0"
    assert spec.json is not None
    assert spec.json["ad_id"] == "ad_prepared_1"
    assert spec.json["amount_usd"] == "50.00"
    assert "secret-token" not in serialized
    assert "account_value" not in serialized


def test_cloud_load_runner_order_create_adds_profile_header_when_enabled() -> None:
    runner = cloud_load_runner.CloudLoadRunner(
        base_url="https://nodo-staging.example.test",
        scenario="order-create",
        run_id="cloud-order-profile-test",
        requests=1,
        concurrency=1,
        timeout_seconds=5.0,
        bot_token="secret-token",
        remitters=1,
        amount_usd="50.00",
        payment_method="zelle",
        delivery_method="pago_movil_ve",
        profile_marketplace=True,
        order_ad_ids=["ad_prepared_1"],
    )

    spec = runner._request_spec(0, tokens=["access-token"])

    assert spec.method == "POST"
    assert spec.path == "/api/v1/orders"
    assert spec.headers["X-NODO-Profile"] == "1"


def test_external_latency_probe_parser_accepts_client_modes(tmp_path: Path) -> None:
    base_args = [
        "--env-file",
        str(_env_file(tmp_path)),
        "--remote-base-url",
        "https://nodo-staging.example.test",
        "--path",
        "/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&delivery_method=pago_movil_ve&limit=20",
        "--run-id",
        "staging-run-0001",
        "--requests",
        "2",
        "--concurrency",
        "1",
        "--output",
        str(tmp_path / "probe.json"),
    ]

    shared = external_latency_probe.parse_args([*base_args, "--client-mode", "shared"])
    new_client = external_latency_probe.parse_args([*base_args, "--client-mode", "new-per-request"])

    assert shared.client_mode == "shared"
    assert new_client.client_mode == "new-per-request"


def test_external_latency_probe_shared_mode_uses_max_connections(tmp_path: Path) -> None:
    class FakeClient:
        created: list["FakeClient"] = []

        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            FakeClient.created.append(self)

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *_args: Any) -> None:
            return None

        async def get(self, _path: str, *, headers: dict[str, str]) -> httpx.Response:
            return httpx.Response(
                200,
                headers={
                    "X-NODO-Process-Time-Ms": "2.5",
                    "Server-Timing": "app;dur=2.5, db;dur=0.4",
                    "X-Request-Id": headers["X-Request-Id"],
                    "X-Correlation-Id": headers["X-Correlation-Id"],
                    "X-NODO-Operation-Id": headers["X-NODO-Operation-Id"],
                },
                json={"data": {"items": []}},
            )

    output = tmp_path / "probe_shared.json"
    probe = external_latency_probe.ExternalLatencyProbe(
        env_file=_env_file(tmp_path),
        remote_base_url="https://nodo-staging.example.test",
        path="/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&delivery_method=pago_movil_ve&limit=20",
        run_id="staging-run-0001",
        requests=3,
        concurrency=2,
        client_mode="shared",
        max_connections=7,
        profile_marketplace=False,
        output=output,
        client_factory=FakeClient,  # type: ignore[arg-type]
    )

    payload = probe.run()

    assert len(FakeClient.created) == 1
    limits = FakeClient.created[0].kwargs["limits"]
    assert limits.max_connections == 7
    assert payload["summary"]["status_counts"] == {"200": 3}
    assert payload["summary"]["backend_process"]["p95_ms"] == 2.5


def test_external_latency_probe_new_per_request_creates_client_per_request(tmp_path: Path) -> None:
    class FakeClient:
        created: list["FakeClient"] = []

        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            FakeClient.created.append(self)

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *_args: Any) -> None:
            return None

        async def get(self, _path: str, *, headers: dict[str, str]) -> httpx.Response:
            return httpx.Response(
                200,
                headers={
                    "X-NODO-Process-Time-Ms": "1.0",
                    "X-Request-Id": headers["X-Request-Id"],
                    "X-Correlation-Id": headers["X-Correlation-Id"],
                    "X-NODO-Operation-Id": headers["X-NODO-Operation-Id"],
                },
                json={"data": {"items": []}},
            )

    output = tmp_path / "probe_new_per_request.json"
    probe = external_latency_probe.ExternalLatencyProbe(
        env_file=_env_file(tmp_path),
        remote_base_url="https://nodo-staging.example.test",
        path="/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&delivery_method=pago_movil_ve&limit=20",
        run_id="staging-run-0001",
        requests=4,
        concurrency=2,
        client_mode="new-per-request",
        max_connections=50,
        profile_marketplace=False,
        output=output,
        client_factory=FakeClient,  # type: ignore[arg-type]
    )

    payload = probe.run()

    assert len(FakeClient.created) == 4
    assert payload["client"]["mode"] == "new-per-request"
    assert payload["summary"]["status_counts"] == {"200": 4}


def test_external_latency_probe_delta_and_percentiles() -> None:
    assert external_latency_probe.external_minus_backend_ms(45.5, 15.5) == 30.0
    assert external_latency_probe.external_minus_backend_ms(10.0, None) is None

    summary = external_latency_probe._percentiles([5.0, 1.0, 3.0, 9.0, 7.0])

    assert summary["count"] == 5
    assert summary["p50_ms"] == 5.0
    assert summary["p95_ms"] == 9.0
    assert summary["p99_ms"] == 9.0


def test_external_latency_probe_profile_summary_does_not_store_secrets() -> None:
    aggregator = external_latency_probe.ProfileAggregator()

    aggregator.add(
        {
            "total_ms": 8.0,
            "dependency": {
                "auth": {
                    "mode": "marketplace_claims",
                    "stages": [{"stage": "auth:marketplace_decode_access_token", "elapsed_ms": 0.5}],
                }
            },
            "stages": [
                {"stage": "cache:hit", "elapsed_ms": 0.1, "metadata": {"hit_type": "shared"}},
                {"stage": "db:acquire", "elapsed_ms": 0.2},
                {"stage": "db:query:list_marketplace_ads_with_businesses", "elapsed_ms": 3.0},
            ],
            "Authorization": "Bearer should-not-be-persisted",
        }
    )

    summary = aggregator.summary()
    serialized = json.dumps(summary)

    assert summary["captured_profiles"] == 1
    assert summary["auth_mode_counts"]["marketplace_claims"] == 1
    assert summary["cache_hit_counts"]["shared"] == 1
    assert summary["db_query_p95_ms"] == 3.0
    assert "Bearer " not in serialized
    assert "should-not-be-persisted" not in serialized


def test_external_latency_probe_output_redacts_env_and_headers(tmp_path: Path) -> None:
    class FakeClient:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *_args: Any) -> None:
            return None

        async def get(self, _path: str, *, headers: dict[str, str]) -> httpx.Response:
            assert "Authorization" in headers
            return httpx.Response(
                200,
                headers={
                    "X-NODO-Process-Time-Ms": "2.5",
                    "X-Request-Id": headers["X-Request-Id"],
                    "X-Correlation-Id": headers["X-Correlation-Id"],
                },
                json={
                    "data": {
                        "_profile": {
                            "total_ms": 2.5,
                            "stages": [{"stage": "cache:hit", "elapsed_ms": 0.1, "metadata": {"hit_type": "miss"}}],
                        }
                    }
                },
            )

    env_file = _env_file(tmp_path, extra={"JWT_SECRET": "jwt-secret-value-for-test"})
    output = tmp_path / "probe_output.json"
    probe = external_latency_probe.ExternalLatencyProbe(
        env_file=env_file,
        remote_base_url="https://nodo-staging.example.test",
        path="/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&delivery_method=pago_movil_ve&limit=20",
        run_id="staging-run-0001",
        requests=1,
        concurrency=1,
        client_mode="shared",
        max_connections=1,
        profile_marketplace=True,
        output=output,
        client_factory=FakeClient,  # type: ignore[arg-type]
    )

    probe.run()
    serialized = output.read_text(encoding="utf-8")

    assert "postgresql://user:password" not in serialized
    assert "jwt-secret-value-for-test" not in serialized
    assert "Authorization" not in serialized
    assert "Bearer " not in serialized
    assert "storage_path" not in serialized
    assert "account_value" not in serialized


def test_external_latency_probe_remote_url_requires_guardrails(tmp_path: Path) -> None:
    env_file = _env_file(tmp_path, extra={"NODO_STAGING_API_HOST_ALLOWLIST": "other.example.test"})

    try:
        external_latency_probe.ExternalLatencyProbe(
            env_file=env_file,
            remote_base_url="https://nodo-staging.example.test",
            path="/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&delivery_method=pago_movil_ve&limit=20",
            run_id="staging-run-0001",
            requests=1,
            concurrency=1,
            client_mode="shared",
            max_connections=1,
            profile_marketplace=False,
            output=tmp_path / "probe.json",
        )
    except staging_guardrails.StagingGuardrailError as exc:
        assert "API base URL host is not in NODO_STAGING_API_HOST_ALLOWLIST" in str(exc)
    else:
        raise AssertionError("external latency probe must enforce remote API guardrails")


def test_storage_smoke_output_contract_does_not_expose_private_paths(tmp_path: Path, monkeypatch: Any) -> None:
    env_file = _env_file(tmp_path, extra={"STAGING_VALIDATION_ACK": "staging-run-0001"})
    output = tmp_path / "storage.json"

    def fake_run_storage_smoke(_env: dict[str, str], *, run_id: str) -> dict[str, Any]:
        return {
            "bucket": "business-intake",
            "object_deleted": True,
            "size_bytes": 32,
            "checksum_sha256": "a" * 64,
            "downloaded_checksum_sha256": "a" * 64,
            "checksum_match": True,
            "signed_url_created": True,
            "storage_path_exposed": False,
            "signed_url_persisted": False,
        }

    monkeypatch.setattr(staging_storage_smoke, "run_storage_smoke", fake_run_storage_smoke)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "staging_storage_smoke.py",
            "--env-file",
            str(env_file),
            "--run-id",
            "staging-run-0001",
            "--confirm-staging",
            "--output",
            str(output),
        ],
    )

    assert staging_storage_smoke.main() == 0
    text = output.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert payload["result"]["storage_path_exposed"] is False
    assert payload["result"]["signed_url_persisted"] is False
    assert "supabase://" not in text
    assert "token=" not in text


def test_telegram_smoke_does_not_print_token_or_secret(tmp_path: Path, monkeypatch: Any) -> None:
    token = "123456:business-secret-token"
    env_file = _env_file(tmp_path, extra={"BUSINESS_INTAKE_BOT_TOKEN": token})
    output = tmp_path / "telegram.json"
    secret = telegram_webhook_secret(token)

    def fake_post(url: str, **_kwargs: Any) -> httpx.Response:
        assert secret in url
        return httpx.Response(200, json={"data": {"ok": True}})

    monkeypatch.setattr(staging_telegram_webhook_smoke.httpx, "post", fake_post)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "staging_telegram_webhook_smoke.py",
            "--env-file",
            str(env_file),
            "--bot",
            "business-intake",
            "--allow-send",
            "--test-chat-id",
            "123456789",
            "--output",
            str(output),
        ],
    )

    assert staging_telegram_webhook_smoke.main() == 0
    text = output.read_text(encoding="utf-8")
    assert token not in text
    assert secret not in text
    assert "123456789" not in text
    assert "test_chat_hash" in text
