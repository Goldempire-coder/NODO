from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "evidence" / "slice_runs" / "slice_11_hardening_deploy_test_results.json"


def run(command: list[str], *, timeout: int | None = None) -> dict:
    started = time.time()
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    api_path = str(ROOT / "apps" / "api")
    env["PYTHONPATH"] = api_path if not existing_pythonpath else f"{api_path}{os.pathsep}{existing_pythonpath}"
    completed = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=False, timeout=timeout)
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "duration_seconds": round(time.time() - started, 3),
        "stdout": completed.stdout[-6000:],
        "stderr": completed.stderr[-6000:],
    }


def scan_frontend_private_data() -> dict:
    forbidden_terms = [
        "BOT_TOKEN",
        "JWT_SECRET",
        "JWT_REFRESH_SECRET",
        "DATABASE_URL=",
        "REDIS_URL=",
        "STRIPE_SECRET",
        "sk_live_",
        "whsec_live",
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
    targets = [ROOT / "apps" / "web" / "src", ROOT / "apps" / "web" / ".next"]
    hits: list[str] = []
    for target in targets:
        if not target.exists():
            continue
        for path in target.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".js", ".mjs", ".ts", ".tsx", ".json", ".html", ".css"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for term in forbidden_terms:
                if term in text:
                    hits.append(f"{path.relative_to(ROOT)}:{term}")
    return {"command": "frontend secret/private-data/scope scan", "exit_code": 1 if hits else 0, "hits": hits}


def main() -> int:
    corepack = "corepack.cmd" if os.name == "nt" else "corepack"
    checks = [
        run([sys.executable, "-m", "pytest", "apps/api/tests/test_hardening_local.py", "-q"]),
        run([sys.executable, "scripts/local_infra_check.py", "--env-file", ".env.local.example"]),
        run([sys.executable, "scripts/validate_local_schema.py", "--env-file", ".env.local.example"]),
        run([sys.executable, "scripts/concurrency_local.py", "--env-file", ".env.local.example", "--searches", "10", "--duplicate-requests", "5", "--unique-orders", "5"]),
        run([
            sys.executable,
            "scripts/capacity_real.py",
            "--env-file",
            ".env.local.example",
            "--scenario",
            "all",
            "--businesses",
            "2",
            "--ads-per-business",
            "4",
            "--remitters",
            "8",
            "--marketplace-reads",
            "12",
            "--order-creates",
            "4",
            "--same-ad-race-requests",
            "5",
            "--payment-confirms",
            "4",
            "--run-id",
            f"slice11_capacity_smoke_{int(time.time())}",
            "--output",
            "evidence/slice_runs/slice_11_capacity_smoke.json",
        ]),
        run([corepack, "pnpm", "--filter", "@nodo/web", "build"], timeout=120),
        run([sys.executable, "-m", "ruff", "check", "apps/api", "scripts"]),
        run([sys.executable, "-m", "compileall", "apps/api", "scripts"]),
        scan_frontend_private_data(),
    ]
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps({"slice": "slice_11_hardening_deploy", "checks": checks}, indent=2), encoding="utf-8")
    return 0 if all(check["exit_code"] == 0 for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
