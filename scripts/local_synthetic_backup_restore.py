from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import psycopg
from psycopg import sql

from local_hardening_common import DEFAULT_ENV_FILE, ROOT, assert_local_database_url, configure_env, write_json


SAFE_RUN_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{2,63}$")
LOCAL_DB_PREFIX = "nodo_31c_"
DEFAULT_CONTAINER = "nodo_postgres_local"
ARTIFACT_ROOT = ROOT / ".local" / "backup_restore"

CRITICAL_TABLES = [
    "users",
    "businesses",
    "business_access_links",
    "business_payment_methods",
    "file_assets",
    "ads",
    "credit_wallets",
    "credits_ledger",
    "credit_purchases",
    "credit_purchase_onchain_payments",
    "orders",
    "order_state_events",
    "payment_reports",
    "messages",
    "message_attachments",
    "disputes",
    "dispute_events",
    "support_tickets",
    "support_messages",
    "support_ticket_events",
    "staff_profiles",
    "staff_permissions",
    "staff_invites",
    "audit_logs",
    "notification_jobs",
    "business_intake_requests",
]


def _safe_run_id(run_id: str) -> str:
    if not SAFE_RUN_ID_RE.fullmatch(run_id):
        raise RuntimeError("run_id must be 3-64 chars and contain only letters, numbers, '_' or '-'")
    lowered = run_id.lower()
    if any(forbidden in lowered for forbidden in ("prod", "production", "staging", "supabase")):
        raise RuntimeError("run_id must not reference production, staging or provider targets")
    return run_id.lower().replace("-", "_")


def build_local_database_name(run_id: str, kind: str) -> str:
    safe = _safe_run_id(run_id)
    if kind not in {"source", "restore"}:
        raise RuntimeError("database kind must be source or restore")
    db_name = f"{LOCAL_DB_PREFIX}{kind}_{safe}"
    assert_safe_generated_database_name(db_name)
    return db_name


def assert_safe_generated_database_name(database_name: str) -> None:
    if not database_name.startswith(LOCAL_DB_PREFIX):
        raise RuntimeError("Refusing database name outside slice 31C generated prefix")
    if not re.fullmatch(r"[a-z0-9_]{1,63}", database_name):
        raise RuntimeError("Refusing unsafe generated database name")


def _database_url_for(database_url: str, database_name: str) -> str:
    assert_safe_generated_database_name(database_name)
    parsed = urlparse(database_url)
    return urlunparse(parsed._replace(path=f"/{database_name}"))


def _admin_database_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    base_db = parsed.path.strip("/") or "postgres"
    if "local" not in base_db.lower():
        raise RuntimeError("Refusing local admin URL without local database name")
    return urlunparse(parsed._replace(path=f"/{base_db}"))


def _connect_admin(database_url: str) -> psycopg.Connection[Any]:
    admin_url = _admin_database_url(database_url)
    conn = psycopg.connect(admin_url)
    conn.autocommit = True
    return conn


def _create_database(database_url: str, database_name: str) -> None:
    assert_safe_generated_database_name(database_name)
    with _connect_admin(database_url) as conn:
        conn.execute(sql.SQL("drop database if exists {} with (force)").format(sql.Identifier(database_name)))
        conn.execute(sql.SQL("create database {} owner nodo_local").format(sql.Identifier(database_name)))


def _drop_database(database_url: str, database_name: str) -> None:
    assert_safe_generated_database_name(database_name)
    with _connect_admin(database_url) as conn:
        conn.execute(sql.SQL("drop database if exists {} with (force)").format(sql.Identifier(database_name)))


def _migration_files() -> list[Path]:
    return sorted((ROOT / "database" / "migrations").glob("*.up.sql"))


def _apply_migrations(database_url: str) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    with psycopg.connect(database_url) as conn:
        for migration in _migration_files():
            content = migration.read_text(encoding="utf-8")
            with conn.cursor() as cur:
                cur.execute(content)
            conn.commit()
            applied.append({"file": migration.name, "bytes": len(content), "sha256": _sha256_text(content)})
    return applied


def _seed_synthetic_data(database_url: str, run_id: str) -> dict[str, Any]:
    synthetic_tag = f"synthetic_31c_{_safe_run_id(run_id)}"
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into users (id, telegram_id, username, first_name, role, status, phone)
                values
                    ('00000000-0000-0000-0000-000000031c01', 31000001, 'synthetic_remitter_31c', 'Synthetic Remitter', 'remitter', 'active', '+580000000001'),
                    ('00000000-0000-0000-0000-000000031c02', 31000002, 'synthetic_owner_31c', 'Synthetic Owner', 'business_owner', 'active', '+580000000002'),
                    ('00000000-0000-0000-0000-000000031c03', 31000003, 'synthetic_admin_31c', 'Synthetic Admin', 'super_admin', 'active', '+580000000003'),
                    ('00000000-0000-0000-0000-000000031c04', 31000004, 'synthetic_support_31c', 'Synthetic Support', 'support', 'active', '+580000000004');

                insert into businesses (
                    id, owner_user_id, business_name, phone, verification_status, trust_level, approved_at
                )
                values (
                    '10000000-0000-0000-0000-000000031c01',
                    '00000000-0000-0000-0000-000000031c02',
                    'Synthetic 31C Business',
                    '+580000000010',
                    'approved',
                    'basic',
                    now()
                );

                insert into business_access_links (
                    id, business_id, user_id, telegram_id_snapshot, role_in_business, status, linked_by_admin_id, reason
                )
                values (
                    '10000000-0000-0000-0000-000000031c02',
                    '10000000-0000-0000-0000-000000031c01',
                    '00000000-0000-0000-0000-000000031c02',
                    31000002,
                    'owner',
                    'active',
                    '00000000-0000-0000-0000-000000031c03',
                    null
                );

                insert into business_payment_methods (
                    id, business_id, method_type, network, account_value, account_masked, holder_name, verified_status, active
                )
                values (
                    '10000000-0000-0000-0000-000000031c03',
                    '10000000-0000-0000-0000-000000031c01',
                    'zelle',
                    null,
                    'synthetic-only-never-real@example.test',
                    'synthetic***test',
                    'Synthetic Holder',
                    'approved',
                    true
                );

                insert into credit_wallets (
                    id, business_id, available_credits, lifetime_purchased_credits
                )
                values (
                    '10000000-0000-0000-0000-000000031c04',
                    '10000000-0000-0000-0000-000000031c01',
                    10,
                    10
                );

                insert into ads (
                    id, business_id, payment_method_id, payment_method, delivery_method, rate_bs_per_usd,
                    amount_min_usd, amount_max_usd, required_credits, status, activated_at, expires_at
                )
                values (
                    '20000000-0000-0000-0000-000000031c01',
                    '10000000-0000-0000-0000-000000031c01',
                    '10000000-0000-0000-0000-000000031c03',
                    'zelle',
                    'pago_movil_ve',
                    40.000000,
                    20.00,
                    200.00,
                    1,
                    'active',
                    now(),
                    now() + interval '1 day'
                );

                insert into orders (
                    id, public_order_code, ad_id, business_id, remitter_user_id, status, idempotency_key,
                    amount_usd, rate_snapshot, amount_bs_calculated, business_name_snapshot,
                    payment_method_snapshot, delivery_method_snapshot, min_amount_snapshot, max_amount_snapshot,
                    payment_instructions_snapshot, receiver_data_json, payment_report_deadline_at, expires_at
                )
                values (
                    '30000000-0000-0000-0000-000000031c01',
                    'NODO31C0001',
                    '20000000-0000-0000-0000-000000031c01',
                    '10000000-0000-0000-0000-000000031c01',
                    '00000000-0000-0000-0000-000000031c01',
                    'waiting_payment',
                    'idem-31c-order',
                    25.00,
                    40.000000,
                    1000.00,
                    'Synthetic 31C Business',
                    'zelle',
                    'pago_movil_ve',
                    20.00,
                    200.00,
                    '{"method":"zelle","account_masked":"synthetic***test"}'::jsonb,
                    '{"receiver":"synthetic_31c"}'::jsonb,
                    now() + interval '30 minutes',
                    now() + interval '45 minutes'
                );

                insert into order_state_events (
                    id, order_id, from_status, to_status, event_type, actor_user_id, actor_role, request_id
                )
                values (
                    '30000000-0000-0000-0000-000000031c02',
                    '30000000-0000-0000-0000-000000031c01',
                    null,
                    'waiting_payment',
                    'order_created',
                    '00000000-0000-0000-0000-000000031c01',
                    'remitter',
                    'req-synthetic-31c'
                );

                insert into credit_purchases (
                    id, business_id, package_code, credits_amount, price_usd, payment_method, status,
                    idempotency_key, stripe_checkout_session_id
                )
                values (
                    '40000000-0000-0000-0000-000000031c01',
                    '10000000-0000-0000-0000-000000031c01',
                    'starter',
                    10,
                    10.00,
                    'stripe_checkout',
                    'created',
                    'idem-31c-credit',
                    'cs_test_synthetic_31c'
                );

                insert into credits_ledger (
                    id, business_id, type, amount, available_before, available_after, blocked_before, blocked_after,
                    consumed_before, consumed_after, related_credit_purchase_id, reason, source, reference_type,
                    reference_id, created_by
                )
                values (
                    '40000000-0000-0000-0000-000000031c02',
                    '10000000-0000-0000-0000-000000031c01',
                    'purchase',
                    10,
                    0,
                    10,
                    0,
                    0,
                    0,
                    0,
                    '40000000-0000-0000-0000-000000031c01',
                    'synthetic 31c restore drill seed',
                    'local_synthetic',
                    'credit_purchase',
                    '40000000-0000-0000-0000-000000031c01',
                    '00000000-0000-0000-0000-000000031c03'
                );

                insert into support_tickets (
                    id, requester_user_id, requester_role, requester_surface, business_id, scope, category,
                    status, priority, subject, last_message_at
                )
                values (
                    '50000000-0000-0000-0000-000000031c01',
                    '00000000-0000-0000-0000-000000031c01',
                    'remitter',
                    'client_mini_app',
                    null,
                    'client_general',
                    'technical_issue',
                    'open',
                    'normal',
                    'Synthetic support ticket',
                    now()
                );

                insert into support_messages (
                    id, ticket_id, sender_user_id, sender_role, body, visibility
                )
                values (
                    '50000000-0000-0000-0000-000000031c02',
                    '50000000-0000-0000-0000-000000031c01',
                    '00000000-0000-0000-0000-000000031c01',
                    'remitter',
                    'Synthetic support message for local restore validation.',
                    'participants'
                );

                insert into support_ticket_events (
                    id, ticket_id, actor_user_id, actor_role, event_type, metadata_json
                )
                values (
                    '50000000-0000-0000-0000-000000031c03',
                    '50000000-0000-0000-0000-000000031c01',
                    '00000000-0000-0000-0000-000000031c01',
                    'remitter',
                    'support_ticket_created',
                    '{"synthetic":true}'::jsonb
                );

                insert into staff_profiles (
                    id, user_id, staff_role, status, display_name, created_by_super_admin_id, activated_by_super_admin_id,
                    activated_at, reason
                )
                values (
                    '60000000-0000-0000-0000-000000031c01',
                    '00000000-0000-0000-0000-000000031c04',
                    'support_agent',
                    'active',
                    'Synthetic Support',
                    '00000000-0000-0000-0000-000000031c03',
                    '00000000-0000-0000-0000-000000031c03',
                    now(),
                    'synthetic local restore seed'
                );

                insert into staff_permissions (
                    id, staff_profile_id, permission, scope, scope_value, status, granted_by_super_admin_id, reason
                )
                values (
                    '60000000-0000-0000-0000-000000031c02',
                    '60000000-0000-0000-0000-000000031c01',
                    'view_support_queue',
                    'queue_scope',
                    'client_general',
                    'active',
                    '00000000-0000-0000-0000-000000031c03',
                    'synthetic local restore seed'
                );

                insert into business_intake_requests (
                    id, telegram_user_id, telegram_chat_id, contact_phone, business_phone, status, last_step,
                    last_update_id, business_name, responsible_name, city, operation, min_amount_usd, max_amount_usd,
                    submitted_at
                )
                values (
                    '70000000-0000-0000-0000-000000031c01',
                    31999991,
                    31999992,
                    '+580000000091',
                    '+580000000092',
                    'submitted',
                    'submitted',
                    31001,
                    'Synthetic Intake Business',
                    'Synthetic Responsible',
                    'Caracas',
                    'both',
                    20.00,
                    200.00,
                    now()
                );

                insert into notification_jobs (
                    id, notification_type, status, recipient_user_id, order_id, scheduled_for, dedupe_key, metadata_json
                )
                values (
                    '80000000-0000-0000-0000-000000031c01',
                    'order_payment_deadline_warning',
                    'pending',
                    '00000000-0000-0000-0000-000000031c01',
                    '30000000-0000-0000-0000-000000031c01',
                    now() + interval '10 minutes',
                    'synthetic-31c-notification',
                    '{"synthetic":true}'::jsonb
                );

                insert into audit_logs (
                    id, actor_user_id, actor_role, event_type, resource_type, resource_id, reason, request_id, metadata_json
                )
                values (
                    '90000000-0000-0000-0000-000000031c01',
                    '00000000-0000-0000-0000-000000031c03',
                    'super_admin',
                    'synthetic_backup_restore_seeded',
                    'local_synthetic_restore',
                    '10000000-0000-0000-0000-000000031c01',
                    'local synthetic backup restore validation',
                    'req-synthetic-31c',
                    '{"synthetic":true}'::jsonb
                );
                """
            )
        conn.commit()
    return {"tag": synthetic_tag, "seeded": True}


def _collect_counts(database_url: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    with psycopg.connect(database_url) as conn:
        for table in CRITICAL_TABLES:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("select count(*) from {}").format(sql.Identifier(table)))
                counts[table] = int(cur.fetchone()[0])
    return counts


def _schema_summary(database_url: str) -> dict[str, Any]:
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("select count(*) from information_schema.tables where table_schema = 'public'")
            table_count = int(cur.fetchone()[0])
            cur.execute("select count(*) from pg_indexes where schemaname = 'public'")
            index_count = int(cur.fetchone()[0])
            cur.execute(
                """
                select count(*)
                from information_schema.table_constraints
                where table_schema = 'public'
                """
            )
            constraint_count = int(cur.fetchone()[0])
            cur.execute(
                """
                select table_name
                from information_schema.tables
                where table_schema = 'public'
                """
            )
            tables = {row[0] for row in cur.fetchall()}
    missing_tables = sorted(set(CRITICAL_TABLES) - tables)
    return {
        "table_count": table_count,
        "index_count": index_count,
        "constraint_count": constraint_count,
        "missing_critical_tables": missing_tables,
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _docker_tool_version(container: str, tool: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["docker", "exec", container, tool, "--version"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    return {
        "tool": tool,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _run_pg_dump(container: str, database_name: str, dump_path: Path) -> dict[str, Any]:
    assert_safe_generated_database_name(database_name)
    started = time.time()
    command = [
        "docker",
        "exec",
        "-e",
        "PGPASSWORD=nodo_local_password",
        container,
        "pg_dump",
        "-U",
        "nodo_local",
        "-d",
        database_name,
        "-Fc",
        "--no-owner",
        "--no-privileges",
    ]
    dump_path.parent.mkdir(parents=True, exist_ok=True)
    with dump_path.open("wb") as output:
        completed = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.PIPE, check=False, timeout=120)
    return {
        "tool": "pg_dump",
        "exit_code": completed.returncode,
        "duration_seconds": round(time.time() - started, 3),
        "stderr": completed.stderr.decode("utf-8", errors="replace")[-2000:],
    }


def _run_pg_restore(container: str, database_name: str, dump_path: Path) -> dict[str, Any]:
    assert_safe_generated_database_name(database_name)
    started = time.time()
    command = [
        "docker",
        "exec",
        "-i",
        "-e",
        "PGPASSWORD=nodo_local_password",
        container,
        "pg_restore",
        "-U",
        "nodo_local",
        "-d",
        database_name,
        "--no-owner",
        "--no-privileges",
        "--exit-on-error",
    ]
    with dump_path.open("rb") as input_file:
        completed = subprocess.run(command, cwd=ROOT, stdin=input_file, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=120)
    return {
        "tool": "pg_restore",
        "exit_code": completed.returncode,
        "duration_seconds": round(time.time() - started, 3),
        "stdout": completed.stdout.decode("utf-8", errors="replace")[-2000:],
        "stderr": completed.stderr.decode("utf-8", errors="replace")[-2000:],
    }


def _compare_counts(source: dict[str, int], restored: dict[str, int]) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    for table in CRITICAL_TABLES:
        if source.get(table) != restored.get(table):
            mismatches.append({"table": table, "source": source.get(table), "restored": restored.get(table)})
    return mismatches


def run(args: argparse.Namespace) -> dict[str, Any]:
    env = configure_env(Path(args.env_file))
    if env.get("APP_ENV") != "local":
        raise RuntimeError("Refusing non-local APP_ENV for slice 31C local tooling")
    database_url = env["DATABASE_URL"]
    assert_local_database_url(database_url)

    source_db = build_local_database_name(args.run_id, "source")
    restore_db = build_local_database_name(args.run_id, "restore")
    source_url = _database_url_for(database_url, source_db)
    restore_url = _database_url_for(database_url, restore_db)
    artifact_dir = ARTIFACT_ROOT / _safe_run_id(args.run_id)
    dump_path = artifact_dir / "source.dump"

    tool_versions = [_docker_tool_version(args.postgres_container, tool) for tool in ("pg_dump", "pg_restore", "psql")]
    missing_tools = [item for item in tool_versions if item["exit_code"] != 0]
    if missing_tools:
        return {
            "slice": "slice_31C_local_synthetic_backup_restore_tooling",
            "run_id": args.run_id,
            "decision": "BLOCKED_BY_COMMAND_NOT_AVAILABLE",
            "tool_versions": tool_versions,
            "exit_code": 2,
        }

    failures: list[str] = []
    steps: list[dict[str, Any]] = []
    try:
        _create_database(database_url, source_db)
        steps.append({"step": "create_source_database", "database": source_db, "status": "ok"})
        applied = _apply_migrations(source_url)
        steps.append({"step": "apply_migrations", "count": len(applied), "status": "ok"})
        seed = _seed_synthetic_data(source_url, args.run_id)
        steps.append({"step": "seed_synthetic_data", **seed, "status": "ok"})
        source_counts = _collect_counts(source_url)
        source_schema = _schema_summary(source_url)
        if source_schema["missing_critical_tables"]:
            failures.extend(f"missing_source_table:{table}" for table in source_schema["missing_critical_tables"])

        dump_result = _run_pg_dump(args.postgres_container, source_db, dump_path)
        steps.append({"step": "pg_dump", **dump_result, "dump_file": str(dump_path.relative_to(ROOT))})
        if dump_result["exit_code"] != 0:
            failures.append("pg_dump_failed")

        if not failures:
            _create_database(database_url, restore_db)
            steps.append({"step": "create_restore_database", "database": restore_db, "status": "ok"})
            restore_result = _run_pg_restore(args.postgres_container, restore_db, dump_path)
            steps.append({"step": "pg_restore", **restore_result})
            if restore_result["exit_code"] != 0:
                failures.append("pg_restore_failed")
            restored_counts = _collect_counts(restore_url) if not failures else {}
            restored_schema = _schema_summary(restore_url) if not failures else {}
        else:
            restored_counts = {}
            restored_schema = {}

        count_mismatches = _compare_counts(source_counts, restored_counts) if restored_counts else []
        failures.extend(f"count_mismatch:{item['table']}" for item in count_mismatches)
        if restored_schema and restored_schema["missing_critical_tables"]:
            failures.extend(f"missing_restored_table:{table}" for table in restored_schema["missing_critical_tables"])

        dump_info = {
            "file": str(dump_path.relative_to(ROOT)) if dump_path.exists() else None,
            "size_bytes": dump_path.stat().st_size if dump_path.exists() else 0,
            "sha256": _sha256_file(dump_path) if dump_path.exists() else None,
        }
        decision = "LOCAL_SYNTHETIC_BACKUP_RESTORE_VALIDATED" if not failures else "LOCAL_SYNTHETIC_BACKUP_RESTORE_FAILED"
        return {
            "slice": "slice_31C_local_synthetic_backup_restore_tooling",
            "mode": "BUILD_TOOLING_ONLY",
            "scope": "local_synthetic_only",
            "run_id": args.run_id,
            "decision": decision,
            "source_database": source_db,
            "restore_database": restore_db,
            "databases_are_generated": True,
            "tool_versions": tool_versions,
            "migrations_applied": len(applied),
            "dump": dump_info,
            "source_counts": source_counts,
            "restored_counts": restored_counts,
            "count_mismatches": count_mismatches,
            "source_schema": source_schema,
            "restored_schema": restored_schema,
            "steps": steps,
            "cleanup": {"drop_generated_databases": not args.keep_databases},
            "failures": failures,
            "exit_code": 0 if not failures else 1,
        }
    finally:
        if not args.keep_databases:
            for db_name in (restore_db, source_db):
                try:
                    _drop_database(database_url, db_name)
                except Exception as exc:  # noqa: BLE001
                    steps.append({"step": "cleanup_generated_database", "database": db_name, "status": "failed", "error": type(exc).__name__})


def main() -> int:
    parser = argparse.ArgumentParser(description="Local-only synthetic backup/restore drill tooling for NODO slice 31C.")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--postgres-container", default=DEFAULT_CONTAINER)
    parser.add_argument("--keep-databases", action="store_true")
    args = parser.parse_args()

    try:
        payload = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {
            "slice": "slice_31C_local_synthetic_backup_restore_tooling",
            "mode": "BUILD_TOOLING_ONLY",
            "scope": "local_synthetic_only",
            "run_id": getattr(args, "run_id", None),
            "decision": "BLOCKED_BY_LOCAL_DB_TOOLING",
            "error_class": type(exc).__name__,
            "error_message": str(exc),
            "exit_code": 2,
        }
    write_json(Path(args.output), payload)
    print(payload)
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
