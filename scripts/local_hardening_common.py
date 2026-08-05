from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = ROOT / ".env.local.example"
RESULTS_DIR = ROOT / "evidence" / "slice_runs"

SENSITIVE_KEY_PATTERNS = (
    "TOKEN",
    "SECRET",
    "KEY",
    "PASSWORD",
    "DATABASE_URL",
    "REDIS_URL",
    "WEBHOOK_SECRET",
    "PRIVATE",
    "CREDENTIAL",
)


def add_api_path() -> None:
    api_path = str(ROOT / "apps" / "api")
    if api_path not in sys.path:
        sys.path.insert(0, api_path)


def load_env_file(path: Path = DEFAULT_ENV_FILE) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        raise FileNotFoundError(f"env file not found: {path}")
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def configure_env(path: Path = DEFAULT_ENV_FILE, *, overrides: dict[str, str] | None = None) -> dict[str, str]:
    values = load_env_file(path)
    if overrides:
        values.update(overrides)
    for key, value in values.items():
        os.environ[key] = value
    add_api_path()
    return values


def _is_sensitive_key(key: str) -> bool:
    normalized_key = key.upper()
    return any(pattern in normalized_key for pattern in SENSITIVE_KEY_PATTERNS)


def redacted(values: dict[str, str]) -> dict[str, str]:
    return {
        key: "[REDACTED]" if _is_sensitive_key(key) else value
        for key, value in values.items()
    }


def assert_local_database_url(database_url: str) -> None:
    parsed = urlparse(database_url)
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("Refusing non-local DATABASE_URL for local hardening")
    if "local" not in parsed.path.lower():
        raise RuntimeError("Refusing DATABASE_URL whose database name is not local")


def run_command(command: list[str], *, env: dict[str, str] | None = None, timeout: int | None = None) -> dict[str, Any]:
    started = time.time()
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    existing_pythonpath = merged_env.get("PYTHONPATH")
    api_path = str(ROOT / "apps" / "api")
    merged_env["PYTHONPATH"] = api_path if not existing_pythonpath else f"{api_path}{os.pathsep}{existing_pythonpath}"
    completed = subprocess.run(command, cwd=ROOT, env=merged_env, text=True, capture_output=True, check=False, timeout=timeout)
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "duration_seconds": round(time.time() - started, 3),
        "stdout": completed.stdout[-6000:],
        "stderr": completed.stderr[-6000:],
    }


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * pct)))
    return round(ordered[index], 4)


@dataclass
class EndpointMetrics:
    latencies_ms: list[float] = field(default_factory=list)
    status_counts: dict[str, int] = field(default_factory=dict)

    def add(self, latency_ms: float, status_code: int) -> None:
        self.latencies_ms.append(latency_ms)
        key = str(status_code)
        self.status_counts[key] = self.status_counts.get(key, 0) + 1

    def summary(self) -> dict[str, Any]:
        total = len(self.latencies_ms)
        errors = sum(count for status, count in self.status_counts.items() if not status.startswith(("2", "3")))
        return {
            "count": total,
            "error_count": errors,
            "error_rate": round(errors / total, 4) if total else 0,
            "p50_ms": percentile(self.latencies_ms, 0.50),
            "p95_ms": percentile(self.latencies_ms, 0.95),
            "p99_ms": percentile(self.latencies_ms, 0.99),
            "avg_ms": round(statistics.mean(self.latencies_ms), 4) if self.latencies_ms else 0,
            "status_counts": self.status_counts,
        }


class MetricsRecorder:
    def __init__(self) -> None:
        self._items: dict[str, EndpointMetrics] = {}
        self._route_groups: dict[str, EndpointMetrics] = {}

    def record(self, name: str, status_code: int, started_at: float, *, route_group: str | None = None) -> float:
        latency_ms = (time.perf_counter() - started_at) * 1000
        self._items.setdefault(name, EndpointMetrics()).add(latency_ms, status_code)
        if route_group:
            self._route_groups.setdefault(route_group, EndpointMetrics()).add(latency_ms, status_code)
        return latency_ms

    def summary(self, *, started_at: float) -> dict[str, Any]:
        endpoints = {name: item.summary() for name, item in sorted(self._items.items())}
        route_groups = {name: item.summary() for name, item in sorted(self._route_groups.items())}
        total_count = sum(item["count"] for item in endpoints.values())
        error_count = sum(item["error_count"] for item in endpoints.values())
        all_latencies = [latency for item in self._items.values() for latency in item.latencies_ms]
        slowest_route_groups = sorted(
            (
                {"route": name, **summary}
                for name, summary in route_groups.items()
            ),
            key=lambda item: (item["p95_ms"], item["avg_ms"], item["count"]),
            reverse=True,
        )[:15]
        duration = time.perf_counter() - started_at
        return {
            "duration_seconds": round(duration, 3),
            "throughput_per_second": round(total_count / duration, 4) if duration else 0,
            "total_requests": total_count,
            "total_errors": error_count,
            "total_error_rate": round(error_count / total_count, 4) if total_count else 0,
            "p50_ms": percentile(all_latencies, 0.50),
            "p95_ms": percentile(all_latencies, 0.95),
            "p99_ms": percentile(all_latencies, 0.99),
            "endpoints": endpoints,
            "route_groups": route_groups,
            "slowest_route_groups": slowest_route_groups,
        }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
