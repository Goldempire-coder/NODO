from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import psycopg

from local_hardening_common import ROOT, write_json
from staging_guardrails import guardrail_payload, redact_text, require_staging_guardrails

MIGRATIONS_DIR = ROOT / "database" / "migrations"
LOCK_KEY = 170002
LEDGER_TABLE = "nodo_schema_migrations"
DANGEROUS_SQL_RE = re.compile(r"\b(drop|truncate|reset)\b|\bdelete\s+from\b", re.IGNORECASE)
CREATE_INDEX_RE = re.compile(
    r"create\s+(unique\s+)?index\s+(concurrently\s+)?(if\s+not\s+exists\s+)?(?P<name>[a-zA-Z0-9_]+)",
    re.IGNORECASE,
)


class SingleMigrationError(RuntimeError):
    pass


def migration_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_migration_path(migration: str) -> Path:
    raw_path = Path(migration)
    if raw_path.is_absolute():
        raise SingleMigrationError("absolute migration paths are not allowed")
    if ".." in raw_path.parts:
        raise SingleMigrationError("parent directory traversal is not allowed")
    if raw_path.name != migration:
        raise SingleMigrationError("migration must be a file name under database/migrations")
    if not migration.endswith(".up.sql"):
        raise SingleMigrationError("migration must be a .up.sql file")

    migrations_dir = MIGRATIONS_DIR.resolve()
    candidate = (migrations_dir / raw_path).resolve()
    if candidate.parent != migrations_dir:
        raise SingleMigrationError("migration must stay inside database/migrations")
    if not candidate.exists():
        raise FileNotFoundError(candidate)
    return candidate


def split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(current).strip().rstrip(";").strip()
            if statement:
                statements.append(statement)
            current = []
    trailing = "\n".join(current).strip()
    if trailing:
        statements.append(trailing)
    return statements


def statement_summary(statement: str) -> dict[str, Any]:
    normalized = " ".join(statement.split())
    lowered = normalized.lower()
    if lowered.startswith("create unique index"):
        kind = "create_unique_index"
    elif lowered.startswith("create index"):
        kind = "create_index"
    elif lowered.startswith("alter table"):
        kind = "alter_table"
    elif lowered.startswith("create table"):
        kind = "create_table"
    else:
        kind = lowered.split(" ", 1)[0] if lowered else "unknown"

    create_index_match = CREATE_INDEX_RE.search(normalized)
    return {
        "kind": kind,
        "object_name": create_index_match.group("name") if create_index_match else None,
        "create_index_if_not_exists": bool(create_index_match and create_index_match.group(3)),
    }


def analyze_migration(path: Path) -> dict[str, Any]:
    sql = path.read_text(encoding="utf-8")
    lowered_sql = sql.lower()
    if LEDGER_TABLE in lowered_sql:
        raise SingleMigrationError("migration must not reference nodo_schema_migrations")
    if DANGEROUS_SQL_RE.search(sql):
        raise SingleMigrationError("migration contains blocked destructive SQL")

    statements = split_sql_statements(sql)
    summaries = [statement_summary(statement) for statement in statements]
    create_index_statements = [item for item in summaries if item["kind"] in {"create_index", "create_unique_index"}]
    return {
        "filename": path.name,
        "checksum_sha256": migration_checksum(path),
        "statement_count": len(statements),
        "statements": summaries,
        "create_index_count": len(create_index_statements),
        "create_index_if_not_exists_count": sum(
            1 for item in create_index_statements if item["create_index_if_not_exists"]
        ),
        "writes_database": False,
    }


def apply_single_migration(database_url: str, path: Path) -> dict[str, Any]:
    sql = path.read_text(encoding="utf-8")
    with psycopg.connect(database_url) as conn:
        lock_row = conn.execute("select pg_try_advisory_lock(%s)", (LOCK_KEY,)).fetchone()
        if not lock_row or lock_row[0] is not True:
            raise RuntimeError("SINGLE_MIGRATION_LOCK_NOT_ACQUIRED")
        try:
            conn.execute(sql)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            with conn.cursor() as cur:
                cur.execute("select pg_advisory_unlock(%s)", (LOCK_KEY,))
    return {"applied_migration": path.name}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--migration", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-staging", action="store_true")
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
        "slice": "slice_17E_staging_missing_index_repair",
        "phase": "staging_single_migration",
        "mode": "apply" if apply_mode else "dry_run",
        "guardrails": guardrail_payload(guardrails),
        "migration": {},
        "apply_result": {},
        "failures": [],
        "exit_code": 0,
    }
    try:
        migration_path = resolve_migration_path(args.migration)
        payload["migration"] = analyze_migration(migration_path)
        if apply_mode:
            payload["apply_result"] = apply_single_migration(guardrails.env["DATABASE_URL"], migration_path)
            payload["migration"]["writes_database"] = True
    except Exception as exc:
        payload["failures"].append(f"{type(exc).__name__}:{redact_text(str(exc))}")

    payload["exit_code"] = 1 if payload["failures"] else 0
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, default=str))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
