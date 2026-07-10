from __future__ import annotations

import argparse
from pathlib import Path

import psycopg

from local_hardening_common import DEFAULT_ENV_FILE, ROOT, assert_local_database_url, configure_env, write_json


def _migration_files() -> list[Path]:
    return sorted((ROOT / "database" / "migrations").glob("*.down.sql"), reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--output", default="evidence/slice_runs/slice_11_local_rollback.json")
    args = parser.parse_args()

    env = configure_env(Path(args.env_file))
    database_url = env["DATABASE_URL"]
    assert_local_database_url(database_url)

    rolled_back: list[dict[str, str | int]] = []
    failures: list[str] = []
    with psycopg.connect(database_url) as conn:
        for migration in _migration_files():
            sql = migration.read_text(encoding="utf-8")
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                conn.commit()
                rolled_back.append({"file": migration.name, "bytes": len(sql)})
            except Exception as exc:  # pragma: no cover - captured in JSON evidence
                conn.rollback()
                failures.append(f"{migration.name}:{type(exc).__name__}:{exc}")
                break

    expected = [f"{index:04d}" for index in range(11, 0, -1)]
    found = [item["file"][:4] for item in rolled_back]
    failures.extend(f"missing_prefix:{prefix}" for prefix in expected if prefix not in found)

    payload = {
        "slice": "slice_11_hardening_deploy",
        "phase": "local_rollback_drill",
        "rolled_back": rolled_back,
        "failures": failures,
        "exit_code": 1 if failures else 0,
    }
    write_json(Path(args.output), payload)
    print(payload)
    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
