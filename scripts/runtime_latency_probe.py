from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from collections import Counter
from pathlib import Path
from typing import Any

import httpx

from local_hardening_common import write_json


def _percentiles(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "avg_ms": 0.0}
    ordered = sorted(values)

    def pct(percent: float) -> float:
        index = min(len(ordered) - 1, max(0, math.ceil((percent / 100.0) * len(ordered)) - 1))
        return round(ordered[index], 4)

    return {
        "count": len(values),
        "p50_ms": pct(50),
        "p95_ms": pct(95),
        "p99_ms": pct(99),
        "avg_ms": round(sum(values) / len(values), 4),
    }


async def _run_probe(
    *,
    base_url: str,
    path: str,
    requests: int,
    concurrency: int,
    timeout_seconds: float,
    http2: bool,
    run_id: str,
) -> dict[str, Any]:
    semaphore = asyncio.Semaphore(concurrency)
    durations: list[float] = []
    server_durations: list[float] = []
    statuses: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    samples: list[dict[str, Any]] = []
    limits = httpx.Limits(max_connections=max(20, concurrency), max_keepalive_connections=max(20, concurrency))
    started_at = time.perf_counter()
    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout_seconds, limits=limits, http2=http2) as client:

        async def one(index: int) -> None:
            async with semaphore:
                started = time.perf_counter()
                status = "599"
                error_code: str | None = None
                try:
                    response = await client.get(path, headers={"X-Request-Id": f"req_{run_id}_{index}"})
                    status = str(response.status_code)
                    server_elapsed = response.headers.get("x-nodo-process-time-ms")
                    if server_elapsed is not None:
                        try:
                            server_durations.append(float(server_elapsed))
                        except ValueError:
                            pass
                except httpx.RequestError as exc:
                    error_code = type(exc).__name__
                    errors[error_code] += 1
                elapsed_ms = (time.perf_counter() - started) * 1000
                durations.append(elapsed_ms)
                statuses[status] += 1
                if len(samples) < 20:
                    samples.append({"index": index, "status": status, "elapsed_ms": round(elapsed_ms, 4), "error": error_code})

        await asyncio.gather(*(one(index) for index in range(requests)))
    duration_seconds = round(time.perf_counter() - started_at, 4)
    total_errors = sum(count for status, count in statuses.items() if int(status) >= 400)
    return {
        "phase": "runtime_latency_probe",
        "run_id": run_id,
        "target": base_url.rstrip("/") + path,
        "http2": http2,
        "requests": requests,
        "concurrency": concurrency,
        "duration_seconds": duration_seconds,
        "throughput_per_second": round(requests / duration_seconds, 4) if duration_seconds > 0 else 0.0,
        "total_errors": total_errors,
        "error_rate": round(total_errors / requests, 6) if requests else 0.0,
        "latency": _percentiles(durations),
        "server_process_time": _percentiles(server_durations),
        "status_counts": dict(statuses),
        "error_counts": dict(errors),
        "samples": samples,
        "exit_code": 1 if total_errors else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--path", default="/api/v1/health")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--run-id", default=f"runtime_probe_{int(time.time())}")
    parser.add_argument("--output", required=True)
    parser.add_argument("--http2", action="store_true")
    args = parser.parse_args()
    if not args.path.startswith("/"):
        raise SystemExit("--path must start with /")
    payload = asyncio.run(
        _run_probe(
            base_url=args.base_url,
            path=args.path,
            requests=args.requests,
            concurrency=args.concurrency,
            timeout_seconds=args.timeout_seconds,
            http2=args.http2,
            run_id=args.run_id,
        )
    )
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
