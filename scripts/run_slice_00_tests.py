from __future__ import annotations

import importlib
import json
import pathlib
import re
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from app.core.config import EnvValidationError, load_settings, validate_env  # noqa: E402
from app.core.logging import redact_secret  # noqa: E402
from app.services.health_service import HealthService  # noqa: E402


REQUIRED_TABLES = ("users", "audit_logs", "job_runs", "app_metadata")
FORBIDDEN_SECRET_PATTERNS = (
    "BOT_TOKEN",
    "JWT_SECRET",
    "DATABASE_URL",
    "REDIS_URL",
    "STRIPE_SECRET_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sample_env(**overrides: str) -> dict[str, str]:
    env = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-00",
        "NODO_BUILD_ID": "test-build",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
    }
    env.update(overrides)
    return env


def test_env_validation() -> None:
    validate_env(sample_env())
    broken = sample_env()
    broken.pop("DATABASE_URL")
    try:
        validate_env(broken)
    except EnvValidationError as exc:
        assert_true(exc.missing_keys == ["DATABASE_URL"], "missing key should be reported safely")
    else:
        raise AssertionError("missing DATABASE_URL must fail")


def test_health_version_ready_unavailable() -> None:
    service = HealthService(load_settings(sample_env()))
    health = service.health()
    version = service.version()
    ready, payload = service.readiness()
    assert_true(health["status"] == "ok", "health must be ok without storing DB health rows")
    assert_true(version["version"] == "0.0.0-slice-00", "version must use env version")
    assert_true(ready is False, "closed test ports must be unavailable")
    assert_true(payload["checks"]["database"]["ok"] is False, "DB unavailable must be explicit")
    assert_true(payload["checks"]["redis"]["ok"] is False, "Redis unavailable must be explicit")


def test_error_contract_without_fastapi_dependency() -> None:
    module = importlib.import_module("app.core.errors")
    payload = module.error_payload("DATABASE_UNAVAILABLE", "La base de datos no esta disponible.", "req_test")
    assert_true(payload["error"]["code"] == "DATABASE_UNAVAILABLE", "error code must match contract")
    assert_true(payload["request_id"] == "req_test", "request id is required")


def test_logging_redacts_secrets() -> None:
    text = "DATABASE_URL=postgresql://user:password@db.local/nodo Bearer abc.def JWT_SECRET=secret"
    redacted = redact_secret(text)
    assert_true("password" not in redacted, "database password must be redacted")
    assert_true("abc.def" not in redacted, "bearer token must be redacted")
    assert_true("secret" not in redacted.lower(), "plain secret value must be redacted")


def test_migrations_contract() -> None:
    up_sql = (ROOT / "database" / "migrations" / "0001_slice_00_foundation.up.sql").read_text(encoding="utf-8")
    down_sql = (ROOT / "database" / "migrations" / "0001_slice_00_foundation.down.sql").read_text(encoding="utf-8")
    for table in REQUIRED_TABLES:
        assert_true(re.search(rf"create table if not exists {table}\b", up_sql), f"{table} table must exist")
    assert_true("resource_type text not null" in up_sql, "audit_logs must use resource_type")
    assert_true("resource_id uuid null" in up_sql, "audit_logs must use resource_id")
    assert_true("entity_type" not in up_sql and "entity_id" not in up_sql, "entity_* audit fields are forbidden")
    assert_true("request_id text not null" in up_sql, "audit_logs request_id is required")
    assert_true("job_id uuid null references job_runs(id)" in up_sql, "audit_logs job_id must exist when applicable")
    assert_true("'business_owner'" in up_sql and "'super_admin'" in up_sql, "persistent roles must include business_owner and super_admin")
    assert_true("'business'" not in up_sql, "business role must not be persisted")
    assert_true("guest" not in up_sql, "guest must not be persisted")
    assert_true("prevent_audit_logs_mutation" in up_sql, "audit logs must be append-only")
    for table in reversed(REQUIRED_TABLES):
        assert_true(f"drop table if exists {table}" in down_sql, f"{table} rollback must exist")


def test_frontend_bundle_sources_do_not_reference_backend_secrets() -> None:
    web_root = ROOT / "apps" / "web"
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in web_root.rglob("*")
        if path.is_file() and path.suffix in {".ts", ".tsx", ".js", ".mjs", ".json"}
    )
    for pattern in FORBIDDEN_SECRET_PATTERNS:
        assert_true(pattern not in source_text, f"{pattern} must not appear in frontend sources")


def main() -> int:
    tests = [
        test_env_validation,
        test_health_version_ready_unavailable,
        test_error_contract_without_fastapi_dependency,
        test_logging_redacts_secrets,
        test_migrations_contract,
        test_frontend_bundle_sources_do_not_reference_backend_secrets,
    ]
    results = []
    for test in tests:
        try:
            test()
            results.append({"name": test.__name__, "status": "passed"})
        except Exception as exc:  # noqa: BLE001
            results.append({"name": test.__name__, "status": "failed", "error": str(exc), "traceback": traceback.format_exc()})

    output_dir = ROOT / "evidence" / "slice_runs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "slice_00_foundation_test_results.json"
    output_file.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")

    failed = [result for result in results if result["status"] != "passed"]
    print(json.dumps({"passed": len(results) - len(failed), "failed": len(failed), "output": str(output_file)}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
