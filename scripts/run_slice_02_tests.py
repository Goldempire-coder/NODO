from __future__ import annotations

import json
import pathlib
import os
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "evidence" / "slice_runs" / "slice_02_business_verification_test_results.json"


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


def main() -> int:
    checks = [
        run([sys.executable, "-m", "pytest", "apps/api/tests/test_business_verification.py", "-q"]),
        run([sys.executable, "-m", "compileall", "apps/api", "scripts"]),
    ]
    forbidden_scan_targets = [ROOT / "apps" / "web" / "src"]
    forbidden_terms = ["BOT_TOKEN", "JWT_SECRET", "JWT_REFRESH_SECRET"]
    scan_hits: list[str] = []
    for target in forbidden_scan_targets:
        for path in target.rglob("*"):
            if path.is_file() and path.suffix in {".ts", ".tsx", ".py"}:
                text = path.read_text(encoding="utf-8")
                for term in forbidden_terms:
                    if term in text and "test_business_verification.py" not in str(path):
                        scan_hits.append(f"{path.relative_to(ROOT)}:{term}")
    checks.append({"command": "secret/source scan", "exit_code": 1 if scan_hits else 0, "hits": scan_hits})
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps({"slice": "slice_02_business_verification", "checks": checks}, indent=2), encoding="utf-8")
    return 0 if all(check["exit_code"] == 0 for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
