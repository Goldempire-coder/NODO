from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "evidence" / "slice_runs" / "slice_14D_business_intake_bot_test_results.json"


def run(command: list[str], *, timeout: int | None = None) -> dict:
    started = time.time()
    env = os.environ.copy()
    api_path = str(ROOT / "apps" / "api")
    user_site = pathlib.Path.home() / "AppData" / "Roaming" / "Python" / "Python314" / "site-packages"
    paths = [api_path]
    if user_site.exists():
        paths.append(str(user_site))
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    completed = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=False, timeout=timeout)
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "duration_seconds": round(time.time() - started, 3),
        "stdout": completed.stdout[-6000:],
        "stderr": completed.stderr[-6000:],
    }


def main() -> int:
    checks = [
        run([sys.executable, "-m", "pytest", "apps/api/tests/test_business_intake_bot.py", "-q", "--tb=short"]),
        run([sys.executable, "-m", "ruff", "check", "apps/api/app/modules/business_intake", "apps/api/tests/test_business_intake_bot.py", "scripts/run_slice_14D_tests.py"]),
        run([sys.executable, "-m", "compileall", "apps/api/app/modules/business_intake", "apps/api/tests/test_business_intake_bot.py", "scripts/run_slice_14D_tests.py"]),
    ]
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps(
            {
                "slice": "slice_14D_business_intake_bot",
                "checks": checks,
                "passed": all(check["exit_code"] == 0 for check in checks),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0 if all(check["exit_code"] == 0 for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
