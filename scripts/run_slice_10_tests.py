from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "evidence" / "slice_runs" / "slice_10_jobs_notifications_test_results.json"


def run(command: list[str]) -> dict:
    started = time.time()
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    api_path = str(ROOT / "apps" / "api")
    env["PYTHONPATH"] = api_path if not existing_pythonpath else f"{api_path}{os.pathsep}{existing_pythonpath}"
    completed = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "duration_seconds": round(time.time() - started, 3),
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def check_migration_contract() -> dict:
    up_sql = (ROOT / "database" / "migrations" / "0011_slice_10_jobs_notifications.up.sql").read_text(encoding="utf-8")
    forbidden = ["job_name", "event_type text"]
    required = [
        "notification_type text not null",
        "dedupe_key text not null",
        "lock_not_acquired",
        "duration_ms",
        "processed_count",
        "notification_jobs_dedupe_key_unique_idx",
    ]
    failures = [f"forbidden:{term}" for term in forbidden if term in up_sql]
    failures.extend(f"missing:{term}" for term in required if term not in up_sql)
    return {"command": "slice 10 migration contract scan", "exit_code": 1 if failures else 0, "failures": failures}


def scan_frontend_private_data() -> dict:
    forbidden_terms = [
        "BOT_TOKEN",
        "JWT_SECRET",
        "JWT_REFRESH_SECRET",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "sk_test_",
        "whsec_",
        "test-bot-token",
        "test-access-secret",
        "test-refresh-secret",
        "owner@example.com",
        "storage_path",
        "account_value",
        "payment_instructions_snapshot",
        "BEGIN PRIVATE KEY",
        "escrow",
        "fondos protegidos",
        "garantia de entrega",
        "NODO recibio tu dinero",
        "pago garantizado",
        "transaccion asegurada",
    ]
    scan_targets = [ROOT / "apps" / "web" / "src", ROOT / "apps" / "web" / ".next"]
    hits: list[str] = []
    for target in scan_targets:
        if not target.exists():
            continue
        for path in target.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".js", ".mjs", ".ts", ".tsx", ".json", ".html", ".css"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for term in forbidden_terms:
                if term in text:
                    hits.append(f"{path.relative_to(ROOT)}:{term}")
    return {"command": "frontend secret/private-data/scope scan", "exit_code": 1 if hits else 0, "hits": hits}


def main() -> int:
    checks = [
        run([sys.executable, "-m", "pytest", "apps/api/tests/test_jobs_notifications.py", "-q"]),
        run([sys.executable, "-m", "compileall", "apps/api", "scripts"]),
        check_migration_contract(),
        scan_frontend_private_data(),
    ]
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps({"slice": "slice_10_jobs_notifications", "checks": checks}, indent=2), encoding="utf-8")
    return 0 if all(check["exit_code"] == 0 for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
