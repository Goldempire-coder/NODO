from __future__ import annotations

import argparse
import socket
import time
from pathlib import Path
from urllib.parse import urlparse

from local_hardening_common import DEFAULT_ENV_FILE, configure_env, redacted, run_command, write_json


def _tcp_check(url: str, *, default_port: int) -> dict:
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or default_port
    started = time.time()
    try:
        with socket.create_connection((host, port), timeout=3):
            return {"ok": True, "host": host, "port": port, "duration_seconds": round(time.time() - started, 3)}
    except OSError as exc:
        return {"ok": False, "host": host, "port": port, "error": str(exc), "duration_seconds": round(time.time() - started, 3)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--require-services", action="store_true")
    parser.add_argument("--output", default="evidence/slice_runs/slice_11_local_infra_check.json")
    args = parser.parse_args()

    env = configure_env(Path(args.env_file))
    checks = {
        "docker_version": run_command(["docker", "--version"]),
        "docker_compose_version": run_command(["docker", "compose", "version"]),
        "postgres_tcp": _tcp_check(env["DATABASE_URL"], default_port=5432),
        "redis_tcp": _tcp_check(env["REDIS_URL"], default_port=6379),
        "env_redacted": redacted(env),
    }
    exit_code = 0
    if checks["docker_version"]["exit_code"] != 0 or checks["docker_compose_version"]["exit_code"] != 0:
        exit_code = 1
    if args.require_services and (not checks["postgres_tcp"]["ok"] or not checks["redis_tcp"]["ok"]):
        exit_code = 1
    payload = {"slice": "slice_11_hardening_deploy", "phase": "local_infra_check", "exit_code": exit_code, "checks": checks}
    write_json(Path(args.output), payload)
    print(payload)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
