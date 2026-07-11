from __future__ import annotations

import asyncio
import inspect
import json
import sys
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import apply_staging_migrations  # noqa: E402
import apply_staging_single_migration  # noqa: E402
import capacity_real  # noqa: E402
import reconcile_staging_migration_ledger  # noqa: E402
import staging_cleanup_synthetic_run  # noqa: E402
import staging_guardrails  # noqa: E402
import staging_storage_smoke  # noqa: E402
import staging_telegram_webhook_smoke  # noqa: E402
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
    assert payload["fixture_mode_detail"]["seed"] == "direct_db_seed"
    assert payload["fixture_mode_detail"]["measured_requests"] == "remote_api"


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
