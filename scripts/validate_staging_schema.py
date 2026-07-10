from __future__ import annotations

import argparse
import json
from pathlib import Path

import psycopg
import redis

from local_hardening_common import add_api_path, write_json
from staging_guardrails import guardrail_payload, redact_text, require_staging_guardrails
from validate_local_schema import REQUIRED_COLUMNS, REQUIRED_INDEX_FRAGMENTS, REQUIRED_TABLES

add_api_path()
from app.shared.db.connection import connect  # noqa: E402


def validate_schema(database_url: str, redis_url: str) -> dict:
    failures: list[str] = []
    with connect(database_url, row_factory=psycopg.rows.dict_row) as conn:
        table_rows = conn.execute("select table_name from information_schema.tables where table_schema = 'public'").fetchall()
        tables = {row["table_name"] for row in table_rows}
        failures.extend(f"missing_table:{table}" for table in sorted(REQUIRED_TABLES - tables))

        index_rows = conn.execute("select indexname from pg_indexes where schemaname = 'public'").fetchall()
        indexes = {row["indexname"] for row in index_rows}
        failures.extend(
            f"missing_index:{fragment}"
            for fragment in sorted(fragment for fragment in REQUIRED_INDEX_FRAGMENTS if not any(fragment in index for index in indexes))
        )

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
        for table, required_columns in REQUIRED_COLUMNS.items():
            present = columns_by_table.get(table, set())
            for column in sorted(required_columns - present):
                failures.append(f"missing_column:{table}.{column}")

    redis_ping = False
    try:
        redis_ping = bool(redis.Redis.from_url(redis_url, socket_connect_timeout=3, socket_timeout=3).ping())
    except Exception as exc:
        failures.append(f"redis_ping_failed:{type(exc).__name__}")
    return {
        "table_count": len(tables),
        "index_count": len(indexes),
        "required_tables": sorted(REQUIRED_TABLES),
        "redis_ping": redis_ping,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    guardrails = require_staging_guardrails(env_file=Path(args.env_file))
    payload = {
        "slice": "slice_17A_staging_validation_tooling",
        "phase": "staging_schema_validation",
        "guardrails": guardrail_payload(guardrails),
        "validation": {},
        "failures": [],
        "exit_code": 0,
    }
    try:
        payload["validation"] = validate_schema(guardrails.env["DATABASE_URL"], guardrails.env["REDIS_URL"])
        payload["failures"] = payload["validation"]["failures"]
    except Exception as exc:
        payload["failures"] = [f"{type(exc).__name__}:{redact_text(str(exc))}"]
    payload["exit_code"] = 1 if payload["failures"] else 0
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, default=str))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
