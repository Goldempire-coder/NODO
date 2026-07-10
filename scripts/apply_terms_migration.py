from __future__ import annotations

import argparse
import json
from pathlib import Path

import psycopg

from local_hardening_common import DEFAULT_ENV_FILE, load_env_file, write_json


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--output", default="evidence/slice_runs/terms_migration.json")
    args = parser.parse_args()

    env = load_env_file(Path(args.env_file))
    sql = (ROOT / "database" / "migrations" / "0012_terms_acceptance.up.sql").read_text(encoding="utf-8")
    with psycopg.connect(env["DATABASE_URL"]) as conn:
        conn.execute(sql)
        rows = conn.execute(
            """
            select column_name
            from information_schema.columns
            where table_schema = 'public'
              and table_name = 'users'
              and column_name in ('terms_accepted_at', 'terms_version')
            order by column_name
            """
        ).fetchall()
        conn.commit()

    columns = [row[0] for row in rows]
    expected = ["terms_accepted_at", "terms_version"]
    failures = [] if columns == expected else ["missing_terms_columns"]
    payload = {
        "phase": "terms_migration",
        "migration": "0012_terms_acceptance.up.sql",
        "env_file": args.env_file,
        "columns": columns,
        "failures": failures,
        "exit_code": 1 if failures else 0,
    }
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
