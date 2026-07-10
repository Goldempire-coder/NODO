from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import psycopg

from staging_guardrails import guardrail_payload, redact_text, require_staging_guardrails
from local_hardening_common import ROOT, write_json

MIGRATIONS_DIR = ROOT / "database" / "migrations"
LEDGER_TABLE = "nodo_schema_migrations"
LOCK_KEY = 170001


def _migration_files() -> list[Path]:
    return sorted(path for path in MIGRATIONS_DIR.glob("*.up.sql") if path.is_file())


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _read_ledger(conn: psycopg.Connection) -> dict[str, str]:
    _ensure_ledger(conn)
    rows = conn.execute(f"select filename, checksum_sha256 from {LEDGER_TABLE}").fetchall()
    return {row[0]: row[1] for row in rows}


def build_plan(database_url: str) -> dict[str, Any]:
    migrations = _migration_files()
    with psycopg.connect(database_url) as conn:
        applied = _read_ledger(conn)
        conn.rollback()
    items: list[dict[str, Any]] = []
    checksum_mismatches: list[str] = []
    for migration in migrations:
        checksum = _checksum(migration)
        previous = applied.get(migration.name)
        if previous is None:
            status = "pending"
        elif previous == checksum:
            status = "applied"
        else:
            status = "checksum_mismatch"
            checksum_mismatches.append(migration.name)
        items.append({"filename": migration.name, "checksum_sha256": checksum, "status": status})
    return {
        "total": len(items),
        "pending": [item for item in items if item["status"] == "pending"],
        "applied": [item for item in items if item["status"] == "applied"],
        "checksum_mismatches": checksum_mismatches,
        "items": items,
    }


def apply_pending(database_url: str, *, run_id: str, applied_by: str) -> dict[str, Any]:
    applied_now: list[str] = []
    with psycopg.connect(database_url) as conn:
        lock_row = conn.execute("select pg_try_advisory_lock(%s)", (LOCK_KEY,)).fetchone()
        if not lock_row or lock_row[0] is not True:
            raise RuntimeError("MIGRATION_LOCK_NOT_ACQUIRED")
        try:
            ledger = _read_ledger(conn)
            for migration in _migration_files():
                checksum = _checksum(migration)
                previous = ledger.get(migration.name)
                if previous == checksum:
                    continue
                if previous and previous != checksum:
                    raise RuntimeError(f"CHECKSUM_MISMATCH:{migration.name}")
                sql = migration.read_text(encoding="utf-8")
                conn.execute(sql)
                conn.execute(
                    f"""
                    insert into {LEDGER_TABLE} (filename, checksum_sha256, applied_by, run_id)
                    values (%s, %s, %s, %s)
                    """,
                    (migration.name, checksum, applied_by, run_id),
                )
                applied_now.append(migration.name)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            with conn.cursor() as cur:
                cur.execute("select pg_advisory_unlock(%s)", (LOCK_KEY,))
    return {"applied_now": applied_now}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-staging", action="store_true")
    parser.add_argument("--applied-by", default="slice_17A_tooling")
    args = parser.parse_args()
    apply_mode = bool(args.apply)
    if args.plan and args.apply:
        raise SystemExit("--plan and --apply are mutually exclusive")
    guardrails = require_staging_guardrails(
        env_file=Path(args.env_file),
        mutating=apply_mode,
        confirm_staging=args.confirm_staging,
        run_id=args.run_id,
    )
    payload: dict[str, Any] = {
        "slice": "slice_17A_staging_validation_tooling",
        "phase": "staging_migration_plan" if not apply_mode else "staging_migration_apply",
        "guardrails": guardrail_payload(guardrails),
        "mode": "apply" if apply_mode else "dry_run",
        "plan": {},
        "apply_result": {},
        "failures": [],
        "exit_code": 0,
    }
    try:
        payload["plan"] = build_plan(guardrails.env["DATABASE_URL"])
        if payload["plan"]["checksum_mismatches"]:
            payload["failures"].append("checksum_mismatch")
        elif apply_mode:
            payload["apply_result"] = apply_pending(
                guardrails.env["DATABASE_URL"],
                run_id=args.run_id,
                applied_by=args.applied_by,
            )
            payload["plan_after_apply"] = build_plan(guardrails.env["DATABASE_URL"])
    except Exception as exc:
        payload["failures"].append(f"{type(exc).__name__}:{redact_text(str(exc))}")
    payload["exit_code"] = 1 if payload["failures"] else 0
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, default=str))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
