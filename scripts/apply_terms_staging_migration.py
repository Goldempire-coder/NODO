from __future__ import annotations

import json
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".local" / "staging_real_services_smoke_LOCAL_ONLY.env"
OUTPUT = ROOT / "evidence" / "slice_runs" / "supabase_staging_terms_migration_20260706.json"


def _load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key] = value
    return env


def main() -> int:
    env = _load_env()
    sql = (ROOT / "database" / "migrations" / "0012_terms_acceptance.up.sql").read_text(encoding="utf-8")
    with psycopg.connect(env["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            cur.execute(
                """
                select column_name
                from information_schema.columns
                where table_schema = 'public'
                  and table_name = 'users'
                  and column_name in ('terms_accepted_at', 'terms_version')
                order by column_name
                """
            )
            columns = [row[0] for row in cur.fetchall()]
        conn.commit()

    expected = ["terms_accepted_at", "terms_version"]
    failures = [] if columns == expected else ["missing_terms_columns"]
    payload = {
        "phase": "supabase_staging_terms_migration",
        "migration": "0012_terms_acceptance.up.sql",
        "columns": columns,
        "failures": failures,
        "exit_code": 1 if failures else 0,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(payload)
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
