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
    parser.add_argument("--migration", required=True)
    parser.add_argument("--output", default="evidence/slice_runs/manual_migration_file.json")
    args = parser.parse_args()

    migration = ROOT / "database" / "migrations" / args.migration
    if not migration.exists():
        raise FileNotFoundError(migration)

    env = load_env_file(Path(args.env_file))
    sql = migration.read_text(encoding="utf-8")
    failures: list[str] = []
    with psycopg.connect(env["DATABASE_URL"]) as conn:
        try:
            conn.execute(sql)
            conn.commit()
        except Exception as exc:
            conn.rollback()
            failures.append(f"{type(exc).__name__}:{exc}")

    payload = {
        "phase": "manual_migration_file",
        "migration": args.migration,
        "env_file": args.env_file,
        "failures": failures,
        "exit_code": 1 if failures else 0,
    }
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
