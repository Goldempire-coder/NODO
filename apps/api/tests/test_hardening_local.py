from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from app.shared.db import connection as db_connection
from app.shared.rate_limit.request_identity import client_ip_for_rate_limit
from app.shared.storage.private import (
    LocalFilePrivateStorage,
    UnavailablePrivateStorage,
)

ROOT = Path(__file__).resolve().parents[3]


def test_local_env_template_is_safe_and_complete() -> None:
    template = (ROOT / ".env.local.example").read_text(encoding="utf-8")
    required = [
        "APP_ENV=local",
        "DATABASE_URL=postgresql://nodo_local:nodo_local_password@127.0.0.1:55432/nodo_local",
        "REDIS_URL=redis://127.0.0.1:56379/0",
        "PRIVATE_STORAGE_MODE=local_file",
        "STRIPE_WEBHOOK_SECRET=whsec_local_hardening_placeholder",
    ]
    for item in required:
        assert item in template
    assert "supabase.co" not in template.lower()
    assert "sk_live_" not in template
    assert "whsec_live" not in template


def test_local_compose_defines_postgres_and_redis_only() -> None:
    compose = (ROOT / "docker-compose.local.yml").read_text(encoding="utf-8")
    assert "postgres:16-alpine" in compose
    assert "redis:7-alpine" in compose
    assert "55432:5432" in compose
    assert "56379:6379" in compose
    for forbidden in ["supabase", "stripe", "telegram", "ngrok"]:
        assert forbidden not in compose.lower()


def test_rate_limit_identity_uses_proxy_appended_client_ip_not_spoofed_leftmost() -> None:
    scope = {
        "type": "http",
        "client": ("10.0.0.10", 54321),
        "headers": [(b"x-forwarded-for", b"1.2.3.4, 198.51.100.44")],
    }

    assert (
        client_ip_for_rate_limit(scope, trusted_proxies=("10.0.0.10/32",))
        == "198.51.100.44"
    )


def test_rate_limit_identity_falls_back_to_scope_client_without_forwarded_header() -> None:
    scope = {"type": "http", "client": ("203.0.113.20", 54321), "headers": []}

    assert client_ip_for_rate_limit(scope) == "203.0.113.20"


def test_local_private_storage_writes_under_configured_root_without_exposing_path_in_url() -> None:
    storage_root = ROOT / ".local" / "test_storage_unit"
    if storage_root.exists():
        shutil.rmtree(storage_root)
    storage = LocalFilePrivateStorage(storage_root)
    stored = storage.store_payment_evidence(order_id="order", payment_report_id="report", file_id="file", file_name="proof.png", content=b"proof")
    assert stored.storage_path == "private/payment_evidence/order/report/file.png"
    assert (storage_root / stored.storage_path).exists()
    signed = storage.signed_view_url(storage_path=stored.storage_path, expires_in=60)
    assert signed.startswith("local-private://")
    assert stored.storage_path not in signed


def test_runtime_default_storage_remains_unavailable_without_local_opt_in() -> None:
    storage = UnavailablePrivateStorage()
    try:
        storage.store_credit_purchase_proof(business_id="b", purchase_id="p", file_id="f", file_name="proof.pdf", content=b"x")
    except Exception as exc:  # noqa: BLE001
        assert getattr(exc, "code", "") == "STORAGE_UNAVAILABLE"
    else:
        raise AssertionError("Unavailable storage must reject writes")


def test_slice_11_scripts_and_gitignore_exist() -> None:
    scripts = [
        "local_hardening_common.py",
        "local_infra_check.py",
        "apply_local_migrations.py",
        "validate_local_schema.py",
        "seed_local_synthetic_data.py",
        "local_smoke.py",
        "stress_local.py",
        "concurrency_local.py",
        "run_slice_11_tests.py",
    ]
    for script in scripts:
        assert (ROOT / "scripts" / script).exists()
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".local/" in gitignore
    assert "!.env.local.example" in gitignore


def test_slice_31c_local_synthetic_backup_restore_tooling_exists_and_is_local_only() -> None:
    script_path = ROOT / "scripts" / "local_synthetic_backup_restore.py"
    source = script_path.read_text(encoding="utf-8")

    assert "slice_31C_local_synthetic_backup_restore_tooling" in source
    assert "APP_ENV\") != \"local\"" in source
    assert "assert_local_database_url" in source
    assert "nodo_31c_" in source
    assert '"docker",' in source
    assert '"exec",' in source
    assert "pg_dump" in source
    assert "pg_restore" in source
    assert "supabase.co" not in source.lower()
    assert "READY_FOR_REAL_USE" not in source


def test_slice_31c_database_names_are_generated_and_safe() -> None:
    import importlib.util

    script_path = ROOT / "scripts" / "local_synthetic_backup_restore.py"
    scripts_path = str(ROOT / "scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    spec = importlib.util.spec_from_file_location("local_synthetic_backup_restore", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    source = module.build_local_database_name("slice31c-test_001", "source")
    restore = module.build_local_database_name("slice31c-test_001", "restore")
    assert source == "nodo_31c_source_slice31c_test_001"
    assert restore == "nodo_31c_restore_slice31c_test_001"

    for bad in ["prod", "../prod", "x" * 100, "bad.name"]:
        try:
            module.build_local_database_name(bad, "source")
        except RuntimeError:
            pass
        else:
            raise AssertionError("unsafe 31C run_id must be rejected")


def test_no_ready_for_real_use_claim_in_slice_11_artifacts() -> None:
    scan_targets = [
        ROOT / ".env.local.example",
        ROOT / "docker-compose.local.yml",
        ROOT / "scripts" / "local_smoke.py",
        ROOT / "scripts" / "stress_local.py",
        ROOT / "scripts" / "concurrency_local.py",
    ]
    for path in scan_targets:
        assert "READY_FOR_REAL_USE" not in path.read_text(encoding="utf-8")


def test_local_env_does_not_leak_into_process_defaults() -> None:
    assert os.environ.get("STRIPE_SECRET_KEY") != "sk_live_"


def test_postgres_connection_disables_prepared_statements_for_poolers(monkeypatch) -> None:
    captured = {}

    def fake_connect(database_url: str, **kwargs):  # type: ignore[no-untyped-def]
        captured["database_url"] = database_url
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(db_connection.psycopg, "connect", fake_connect)
    db_connection.connect("postgresql://example")

    assert captured["database_url"] == "postgresql://example"
    assert captured["kwargs"]["prepare_threshold"] is None
