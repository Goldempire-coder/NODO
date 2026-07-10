from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from local_hardening_common import ROOT, write_json
from staging_guardrails import guardrail_payload, redact_text, require_staging_guardrails
from validate_local_schema import REQUIRED_COLUMNS, REQUIRED_INDEX_FRAGMENTS, REQUIRED_TABLES

MIGRATIONS_DIR = ROOT / "database" / "migrations"
LEDGER_TABLE = "nodo_schema_migrations"
LOCK_KEY = 170001

CRITICAL_COLUMNS: dict[str, set[str]] = {
    **REQUIRED_COLUMNS,
    "ads": {
        "business_id",
        "payment_method_id",
        "status",
        "credit_hold_ledger_id",
        "credit_consumed_ledger_id",
        "required_credits",
    },
    "credits_ledger": {
        "business_id",
        "type",
        "amount",
        "related_ad_id",
        "related_order_id",
        "reference_type",
        "reference_id",
    },
    "orders": {
        "ad_id",
        "business_id",
        "remitter_user_id",
        "status",
        "public_order_code",
        "idempotency_key",
        "payment_confirmed_at",
        "delivered_at",
    },
    "payment_reports": {"order_id", "reported_by_user_id", "status", "idempotency_key"},
    "messages": {"order_id", "sender_user_id", "sender_role", "body", "status"},
    "disputes": {"order_id", "status", "previous_order_status", "reason"},
    "credit_purchases": {"business_id", "status", "payment_method", "credits_amount", "idempotency_key"},
    "notification_jobs": {"notification_type", "status", "dedupe_key", "scheduled_for"},
}

CRITICAL_INDEX_FRAGMENTS = {
    *REQUIRED_INDEX_FRAGMENTS,
    "ads_business_status_created_idx",
    "ads_payment_method_id_idx",
    "credits_ledger_reference_type_id_type_idx",
    "credits_ledger_related_order_type_idx",
    "orders_business_status_created_idx",
    "orders_active_created_idx",
    "payment_reports_order_status_created_idx",
    "messages_sender_idempotency_idx",
    "disputes_open_order_idx",
    "credit_purchases_business_idempotency_idx",
    "business_intake_requests_chat_update_unique_idx",
}

CRITICAL_CONSTRAINTS = {
    "users_role_check",
    "users_status_check",
    "credit_wallets_business_unique",
    "credit_wallets_balances_check",
    "ads_credit_hold_ledger_fk",
    "ads_credit_consumed_ledger_fk",
    "ads_status_check",
    "credits_ledger_type_check",
    "credits_ledger_related_order_fk",
    "orders_status_check",
    "payment_reports_status_check",
    "messages_status_check",
    "disputes_status_check",
    "business_access_links_status_check",
    "business_intake_requests_status_check",
    "file_assets_resource_type_check",
    "file_assets_file_type_check",
}


def migration_files() -> list[Path]:
    return sorted(path for path in MIGRATIONS_DIR.glob("*.up.sql") if path.is_file())


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def migration_checksums() -> dict[str, str]:
    return {path.name: checksum(path) for path in migration_files()}


def _ensure_ledger(conn: psycopg.Connection) -> None:
    conn.execute(
        f"""
        create table if not exists {LEDGER_TABLE} (
            id bigserial primary key,
            filename text not null unique,
            checksum_sha256 text not null,
            applied_at timestamptz not null default now(),
            applied_by text not null,
            run_id text
        )
        """
    )


def _ledger_exists(conn: psycopg.Connection) -> bool:
    row = conn.execute("select to_regclass(%s) as ledger_table", (f"public.{LEDGER_TABLE}",)).fetchone()
    if isinstance(row, dict):
        return row["ledger_table"] is not None
    return row[0] is not None


def _read_ledger(conn: psycopg.Connection) -> dict[str, str]:
    if not _ledger_exists(conn):
        return {}
    rows = conn.execute(f"select filename, checksum_sha256 from {LEDGER_TABLE}").fetchall()
    return {row["filename"]: row["checksum_sha256"] for row in rows}


def _acquire_lock(conn: psycopg.Connection) -> None:
    row = conn.execute("select pg_try_advisory_lock(%s) as acquired", (LOCK_KEY,)).fetchone()
    acquired = row["acquired"] if isinstance(row, dict) else row[0]
    if acquired is not True:
        raise RuntimeError("MIGRATION_LEDGER_RECONCILE_LOCK_NOT_ACQUIRED")


def _release_lock(conn: psycopg.Connection) -> None:
    conn.execute("select pg_advisory_unlock(%s)", (LOCK_KEY,))


def inspect_schema(conn: psycopg.Connection) -> dict[str, set[str] | dict[str, set[str]]]:
    table_rows = conn.execute("select table_name from information_schema.tables where table_schema = 'public'").fetchall()
    tables = {row["table_name"] for row in table_rows}

    column_rows = conn.execute(
        """
        select table_name, column_name
        from information_schema.columns
        where table_schema = 'public'
        """
    ).fetchall()
    columns_by_table: dict[str, set[str]] = {}
    for row in column_rows:
        columns_by_table.setdefault(row["table_name"], set()).add(row["column_name"])

    index_rows = conn.execute("select indexname from pg_indexes where schemaname = 'public'").fetchall()
    indexes = {row["indexname"] for row in index_rows}

    constraint_rows = conn.execute(
        """
        select con.conname as constraint_name
        from pg_constraint con
        join pg_class rel on rel.oid = con.conrelid
        join pg_namespace nsp on nsp.oid = rel.relnamespace
        where nsp.nspname = 'public'
        """
    ).fetchall()
    constraints = {row["constraint_name"] for row in constraint_rows}

    return {
        "tables": tables,
        "columns_by_table": columns_by_table,
        "indexes": indexes,
        "constraints": constraints,
    }


def verify_schema_artifacts(schema: dict[str, Any]) -> dict[str, Any]:
    tables: set[str] = schema["tables"]
    columns_by_table: dict[str, set[str]] = schema["columns_by_table"]
    indexes: set[str] = schema["indexes"]
    constraints: set[str] = schema["constraints"]

    missing_tables = sorted(REQUIRED_TABLES - tables)
    missing_columns: list[str] = []
    for table, required_columns in sorted(CRITICAL_COLUMNS.items()):
        present = columns_by_table.get(table, set())
        for column in sorted(required_columns - present):
            missing_columns.append(f"{table}.{column}")

    missing_indexes = sorted(
        fragment for fragment in CRITICAL_INDEX_FRAGMENTS if not any(fragment in index for index in indexes)
    )
    missing_constraints = sorted(CRITICAL_CONSTRAINTS - constraints)
    failures = [
        *(f"missing_table:{item}" for item in missing_tables),
        *(f"missing_column:{item}" for item in missing_columns),
        *(f"missing_index:{item}" for item in missing_indexes),
        *(f"missing_constraint:{item}" for item in missing_constraints),
    ]
    return {
        "table_count": len(tables),
        "index_count": len(indexes),
        "constraint_count": len(constraints),
        "missing_tables": missing_tables,
        "missing_columns": missing_columns,
        "missing_indexes": missing_indexes,
        "missing_constraints": missing_constraints,
        "failures": failures,
    }


def evaluate_reconciliation_state(
    *,
    local_checksums: dict[str, str],
    ledger: dict[str, str],
    ledger_exists: bool,
    schema_check: dict[str, Any],
) -> dict[str, Any]:
    checksum_mismatches = sorted(
        filename
        for filename, previous_checksum in ledger.items()
        if filename in local_checksums and local_checksums[filename] != previous_checksum
    )
    unknown_ledger_entries = sorted(filename for filename in ledger if filename not in local_checksums)
    pending = sorted(filename for filename in local_checksums if filename not in ledger)
    applied = sorted(filename for filename in local_checksums if ledger.get(filename) == local_checksums[filename])
    failures = [
        *schema_check["failures"],
        *(f"checksum_mismatch:{item}" for item in checksum_mismatches),
        *(f"unknown_ledger_entry:{item}" for item in unknown_ledger_entries),
    ]
    return {
        "ledger_exists": ledger_exists,
        "ledger_row_count": len(ledger),
        "total_migrations": len(local_checksums),
        "applied": applied,
        "pending_ledger_rows": pending,
        "checksum_mismatches": checksum_mismatches,
        "unknown_ledger_entries": unknown_ledger_entries,
        "schema_check": schema_check,
        "verified_migrations": [] if failures else sorted(local_checksums),
        "blocked_migrations": pending if failures else [],
        "failures": failures,
    }


def build_reconciliation_plan(database_url: str) -> dict[str, Any]:
    local_checksums = migration_checksums()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        _acquire_lock(conn)
        try:
            ledger_exists = _ledger_exists(conn)
            ledger = _read_ledger(conn)
            schema_check = verify_schema_artifacts(inspect_schema(conn))
        finally:
            _release_lock(conn)
            conn.rollback()
    return evaluate_reconciliation_state(
        local_checksums=local_checksums,
        ledger=ledger,
        ledger_exists=ledger_exists,
        schema_check=schema_check,
    )


def apply_reconciliation(database_url: str, *, run_id: str, applied_by: str) -> dict[str, Any]:
    local_checksums = migration_checksums()
    inserted: list[str] = []
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        _acquire_lock(conn)
        try:
            ledger = _read_ledger(conn)
            schema_check = verify_schema_artifacts(inspect_schema(conn))
            checksum_mismatches = sorted(
                filename
                for filename, previous_checksum in ledger.items()
                if filename in local_checksums and local_checksums[filename] != previous_checksum
            )
            unknown_ledger_entries = sorted(filename for filename in ledger if filename not in local_checksums)
            failures = [
                *schema_check["failures"],
                *(f"checksum_mismatch:{item}" for item in checksum_mismatches),
                *(f"unknown_ledger_entry:{item}" for item in unknown_ledger_entries),
            ]
            if failures:
                raise RuntimeError("SCHEMA_DRIFT:" + ",".join(failures[:25]))

            _ensure_ledger(conn)
            for filename, file_checksum in sorted(local_checksums.items()):
                if ledger.get(filename) == file_checksum:
                    continue
                conn.execute(
                    f"""
                    insert into {LEDGER_TABLE} (filename, checksum_sha256, applied_by, run_id)
                    values (%s, %s, %s, %s)
                    """,
                    (filename, file_checksum, applied_by, run_id),
                )
                inserted.append(filename)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            _release_lock(conn)
    return {"inserted_ledger_rows": inserted}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-staging", action="store_true")
    parser.add_argument("--applied-by", default="slice_17D_ledger_reconciliation")
    args = parser.parse_args()
    if args.dry_run and args.apply:
        raise SystemExit("--dry-run and --apply are mutually exclusive")

    apply_mode = bool(args.apply)
    guardrails = require_staging_guardrails(
        env_file=Path(args.env_file),
        mutating=apply_mode,
        confirm_staging=args.confirm_staging,
        run_id=args.run_id,
    )
    payload: dict[str, Any] = {
        "slice": "slice_17D_staging_migration_ledger_reconciliation",
        "phase": "staging_migration_ledger_reconciliation",
        "mode": "apply" if apply_mode else "dry_run",
        "guardrails": guardrail_payload(guardrails),
        "plan": {},
        "apply_result": {},
        "failures": [],
        "exit_code": 0,
    }
    try:
        payload["plan"] = build_reconciliation_plan(guardrails.env["DATABASE_URL"])
        payload["failures"].extend(payload["plan"]["failures"])
        if apply_mode and not payload["failures"]:
            payload["apply_result"] = apply_reconciliation(
                guardrails.env["DATABASE_URL"],
                run_id=args.run_id,
                applied_by=args.applied_by,
            )
            payload["plan_after_apply"] = build_reconciliation_plan(guardrails.env["DATABASE_URL"])
    except Exception as exc:
        payload["failures"].append(f"{type(exc).__name__}:{redact_text(str(exc))}")

    payload["exit_code"] = 1 if payload["failures"] else 0
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, default=str))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
