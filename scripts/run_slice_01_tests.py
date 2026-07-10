from __future__ import annotations

import json
import pathlib
import re
import traceback

ROOT = pathlib.Path(__file__).resolve().parents[1]

FORBIDDEN_FRONTEND_PATTERNS = (
    "BOT_TOKEN",
    "JWT_SECRET",
    "JWT_REFRESH_SECRET",
    "DATABASE_URL",
    "REDIS_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _implementation_text() -> str:
    roots = [ROOT / "apps" / "api" / "app", ROOT / "apps" / "web" / "src", ROOT / "database" / "migrations"]
    chunks = []
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".ts", ".tsx", ".css", ".sql"}:
                chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def test_sessions_migration_contract() -> None:
    up_sql = _read("database/migrations/0002_slice_01_auth_telegram.up.sql")
    down_sql = _read("database/migrations/0002_slice_01_auth_telegram.down.sql")
    required_snippets = (
        "create table if not exists sessions",
        "id uuid primary key",
        "user_id uuid not null references users(id)",
        "refresh_token_hash text not null unique",
        "status text not null default 'active'",
        "access_token_jti text null",
        "expires_at timestamptz not null",
        "revoked_at timestamptz null",
        "last_used_at timestamptz null",
        "ip_hash text null",
        "user_agent text null",
        "sessions_status_check check (status in ('active', 'revoked', 'expired'))",
        "sessions_revoked_at_check",
        "sessions_user_status_created_idx",
        "sessions_refresh_token_hash_idx",
        "sessions_access_token_jti_idx",
        "sessions_expires_at_idx",
    )
    for snippet in required_snippets:
        assert_true(snippet in up_sql, f"missing sessions migration contract snippet: {snippet}")
    assert_true("drop table if exists sessions" in down_sql, "sessions rollback must exist")
    assert_true("session_revocations" not in up_sql, "session_revocations is forbidden in MVP")


def test_auth_routes_are_canonical() -> None:
    implementation = _implementation_text()
    assert_true("/auth/telegram-login" not in implementation, "old auth endpoint is forbidden")
    routes = _read("apps/api/app/routes/auth.py")
    users = _read("apps/api/app/routes/users.py")
    assert_true('@router.post("/auth/telegram")' in routes, "canonical telegram auth route missing")
    assert_true('@router.post("/auth/refresh")' in routes, "canonical refresh route missing")
    assert_true('@router.post("/auth/logout")' in routes, "canonical logout route missing")
    assert_true('@router.get("/users/me")' in users, "canonical users/me route missing")


def test_backend_security_contract_static() -> None:
    service = _read("apps/api/app/modules/users/service.py")
    jwt_module = _read("apps/api/app/auth/jwt.py")
    telegram = _read("apps/api/app/auth/telegram.py")
    repository = _read("apps/api/app/modules/users/repository.py")
    audit_service = _read("apps/api/app/shared/audit/audit_service.py")
    redis_limiter = _read("apps/api/app/shared/rate_limit/redis.py")
    main = _read("apps/api/app/main.py")
    dependencies = _read("apps/api/app/auth/dependencies.py")
    public_payload = re.search(r"def public_user_payload\(.*?\n\n", service, flags=re.DOTALL)

    assert_true("validate_telegram_init_data" in service, "backend must validate Telegram initData")
    assert_true("hmac.compare_digest" in telegram, "Telegram hash validation must use constant-time compare")
    assert_true("hash_refresh_token" in service, "refresh token hash must be used before persistence")
    assert_true("create_refresh_token" in jwt_module, "opaque refresh token factory missing")
    assert_true("rotate_session" in repository and "last_used_at" in repository, "refresh must rotate and update session")
    assert_true("revoke_session" in repository and "revoked_at" in repository, "logout must revoke session")
    assert_true(public_payload is not None and "telegram_id" not in public_payload.group(0), "telegram_id must not be public")
    assert_true('"init_data"' not in service and "metadata_json={\"reason\"" in service, "raw initData must not be audited")
    assert_true("BOT_TOKEN" not in service and "JWT_SECRET" not in service, "secret key names should not be logged in service")
    assert_true("class PostgresUserRepository" in repository, "runtime auth repository must support PostgreSQL users/sessions")
    assert_true("insert into sessions" in repository and "update sessions" in repository, "sessions must be persisted in DB-backed repository")
    assert_true("class PostgresAuditWriter" in audit_service and "insert into audit_logs" in audit_service, "audit events must support DB persistence")
    assert_true("class RedisRateLimiter" in redis_limiter and "Redis.from_url" in redis_limiter, "auth rate limit must support Redis")
    assert_true("settings.app_env == \"test\"" in main, "in-memory auth dependencies may only be selected for tests")
    assert_true("PostgresUserRepository(settings.database_url)" in main, "non-test runtime must use PostgreSQL user repository")
    assert_true("PostgresAuditWriter(settings.database_url)" in main, "non-test runtime must use PostgreSQL audit writer")
    assert_true("RedisRateLimiter(settings.redis_url)" in main, "non-test runtime must use Redis rate limiter")
    assert_true("REFRESH_ALLOWED_STATUSES_BY_ROLE" in service, "refresh must enforce role/status matrix")
    assert_true("OPERATE_ALLOWED_STATUSES_BY_ROLE" in dependencies, "auth dependency must enforce role/status matrix")


def test_required_audit_events_declared_and_written() -> None:
    events = _read("apps/api/app/shared/audit/events.py")
    service = _read("apps/api/app/modules/users/service.py")
    for event_type in ("user_created", "user_login", "user_logout", "session_refreshed", "auth_failed"):
        assert_true(f'"{event_type}"' in events, f"{event_type} must be declared")
        assert_true(f'event_type="{event_type}"' in service, f"{event_type} must be written")
    assert_true("resource_type=" in service and "request_id=" in service, "audit entries need resource_type and request_id")


def test_frontend_telegram_ui_and_motion_contract() -> None:
    layout = _read("apps/web/src/app/layout.tsx")
    css = _read("apps/web/src/app/globals.css")
    frontend_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "apps" / "web" / "src").rglob("*")
        if path.is_file() and path.suffix in {".ts", ".tsx", ".css"}
    )
    assert_true("@telegram-apps/sdk" in frontend_source, "frontend must use Telegram Mini App SDK")
    assert_true("@telegram-apps/telegram-ui" in frontend_source, "frontend must use Telegram UI kit")
    assert_true("@telegram-apps/telegram-ui/dist/styles.css" in layout, "Telegram UI styles must be loaded")
    assert_true("retrieveRawInitData" in frontend_source, "frontend must obtain Telegram initData from SDK")
    assert_true("bindThemeParamsCssVars" in frontend_source, "frontend must respect Telegram themeParams")
    assert_true("AnimatedLogo" in frontend_source and "animated-logo" in css, "entry must include AnimatedLogo")
    assert_true("1100ms" in css, "AnimatedLogo motion must be within 900ms-1400ms")
    assert_true("animation-iteration-count: 1" in css, "AnimatedLogo must not loop infinitely")
    assert_true("prefers-reduced-motion: reduce" in css, "reduced motion is required")
    assert_true("Foundation" not in frontend_source, "slice 00 foundation screen must not remain as entry")


def test_frontend_sources_do_not_reference_backend_secrets() -> None:
    web_root = ROOT / "apps" / "web"
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in web_root.rglob("*")
        if path.is_file() and path.suffix in {".ts", ".tsx", ".js", ".mjs", ".json", ".css"}
    )
    for pattern in FORBIDDEN_FRONTEND_PATTERNS:
        assert_true(pattern not in source_text, f"{pattern} must not appear in frontend sources")


def main() -> int:
    tests = [
        test_sessions_migration_contract,
        test_auth_routes_are_canonical,
        test_backend_security_contract_static,
        test_required_audit_events_declared_and_written,
        test_frontend_telegram_ui_and_motion_contract,
        test_frontend_sources_do_not_reference_backend_secrets,
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
    output_file = output_dir / "slice_01_auth_telegram_test_results.json"
    output_file.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")

    failed = [result for result in results if result["status"] != "passed"]
    print(json.dumps({"passed": len(results) - len(failed), "failed": len(failed), "output": str(output_file)}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
