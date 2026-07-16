from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

import httpx

from capacity_real import create_access_token_at, parse_process_time_ms, parse_server_timing
from local_hardening_common import write_json
from staging_guardrails import StagingGuardrails, guardrail_payload, redact_text, require_staging_guardrails

PROFILE_SAMPLE_LIMIT = 50
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_SURFACE = "client_mini_app"
DEFAULT_ROLE = "remitter"
DEFAULT_STATUS = "active"


def _percentiles(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}
    ordered = sorted(values)

    def pct(percent: float) -> float:
        index = min(len(ordered) - 1, max(0, math.ceil((percent / 100.0) * len(ordered)) - 1))
        return round(ordered[index], 4)

    return {"count": len(values), "p50_ms": pct(50), "p95_ms": pct(95), "p99_ms": pct(99)}


def external_minus_backend_ms(external_duration_ms: float, backend_process_ms: float | None) -> float | None:
    if backend_process_ms is None:
        return None
    return round(max(0.0, external_duration_ms - backend_process_ms), 4)


def shared_limits_config(max_connections: int) -> dict[str, int]:
    if max_connections < 1:
        raise ValueError("max_connections must be >= 1")
    return {"max_connections": max_connections, "max_keepalive_connections": max_connections}


def make_shared_limits(max_connections: int) -> httpx.Limits:
    return httpx.Limits(**shared_limits_config(max_connections))


def _safe_response_json(response: httpx.Response) -> dict[str, Any]:
    try:
        parsed = response.json()
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _profile_from_body(body: dict[str, Any]) -> dict[str, Any] | None:
    data = body.get("data")
    if isinstance(data, dict) and isinstance(data.get("_profile"), dict):
        return data["_profile"]
    if isinstance(body.get("_profile"), dict):
        return body["_profile"]
    return None


class ProfileAggregator:
    def __init__(self) -> None:
        self._totals: list[float] = []
        self._stage_values: dict[str, list[float]] = defaultdict(list)
        self._auth_modes: Counter[str] = Counter()
        self._cache_hits: Counter[str] = Counter()

    def add(self, profile: dict[str, Any] | None) -> None:
        if not profile:
            return
        total_ms = profile.get("total_ms")
        if isinstance(total_ms, (int, float)):
            self._totals.append(float(total_ms))
        dependency = profile.get("dependency")
        if isinstance(dependency, dict):
            auth = dependency.get("auth")
            if isinstance(auth, dict):
                mode = auth.get("mode")
                if isinstance(mode, str):
                    self._auth_modes[mode] += 1
                stages = auth.get("stages")
                if isinstance(stages, list):
                    for stage in stages:
                        self._record_stage(stage)
        stages = profile.get("stages")
        if isinstance(stages, list):
            for stage in stages:
                self._record_stage(stage)

    def _record_stage(self, stage: Any) -> None:
        if not isinstance(stage, dict):
            return
        name = stage.get("stage")
        elapsed = stage.get("elapsed_ms")
        if isinstance(name, str) and isinstance(elapsed, (int, float)):
            self._stage_values[name].append(float(elapsed))
        metadata = stage.get("metadata")
        if name == "cache:hit" and isinstance(metadata, dict):
            hit_type = metadata.get("hit_type")
            if isinstance(hit_type, str):
                self._cache_hits[hit_type] += 1

    def summary(self) -> dict[str, Any]:
        stages = {stage: _percentiles(values) for stage, values in sorted(self._stage_values.items())}
        return {
            "captured_profiles": len(self._totals),
            "route_total": _percentiles(self._totals),
            "stages": stages,
            "auth_mode_counts": dict(self._auth_modes),
            "cache_hit_counts": dict(self._cache_hits),
            "db_acquire_p95_ms": stages.get("db:acquire", {}).get("p95_ms", 0.0),
            "db_query_p95_ms": stages.get("db:query:list_marketplace_ads_with_businesses", {}).get("p95_ms", 0.0),
            "route_total_p95_ms": _percentiles(self._totals)["p95_ms"],
        }


class LatencyRecorder:
    def __init__(self) -> None:
        self.external_ms: list[float] = []
        self.backend_process_ms: list[float] = []
        self.external_minus_backend_ms: list[float] = []
        self.response_bytes: list[float] = []
        self.status_counts: Counter[str] = Counter()
        self.error_counts: Counter[str] = Counter()
        self.server_timing: dict[str, list[float]] = defaultdict(list)
        self.samples: list[dict[str, Any]] = []
        self.profile = ProfileAggregator()

    def add_response(
        self,
        *,
        index: int,
        status_code: int,
        external_duration_ms: float,
        response: httpx.Response | None,
        error_code: str | None = None,
    ) -> None:
        self.external_ms.append(external_duration_ms)
        self.status_counts[str(status_code)] += 1
        if error_code:
            self.error_counts[error_code] += 1
        headers = response.headers if response is not None else {}
        process_time_ms = parse_process_time_ms(headers.get("X-NODO-Process-Time-Ms"))
        server_timing = parse_server_timing(headers.get("Server-Timing"))
        backend_time = process_time_ms if process_time_ms is not None else server_timing.get("app")
        if backend_time is not None:
            self.backend_process_ms.append(backend_time)
            delta = external_minus_backend_ms(external_duration_ms, backend_time)
            if delta is not None:
                self.external_minus_backend_ms.append(delta)
        for metric, value in server_timing.items():
            self.server_timing[metric].append(value)
        response_size = float(len(response.content)) if response is not None else 0.0
        self.response_bytes.append(response_size)
        body = _safe_response_json(response) if response is not None else {}
        profile = _profile_from_body(body)
        self.profile.add(profile)
        if len(self.samples) < PROFILE_SAMPLE_LIMIT:
            self.samples.append(
                {
                    "index": index,
                    "status": status_code,
                    "error": error_code,
                    "external_duration_ms": round(external_duration_ms, 4),
                    "backend_process_ms": backend_time,
                    "external_minus_backend_ms": external_minus_backend_ms(external_duration_ms, backend_time),
                    "response_bytes": int(response_size),
                    "request_id": headers.get("X-Request-Id"),
                    "correlation_id": headers.get("X-Correlation-Id"),
                    "operation_id": headers.get("X-NODO-Operation-Id"),
                    "server_timing": server_timing,
                    "profile_present": profile is not None,
                }
            )

    def summary(self) -> dict[str, Any]:
        return {
            "external": _percentiles(self.external_ms),
            "backend_process": _percentiles(self.backend_process_ms),
            "external_minus_backend": _percentiles(self.external_minus_backend_ms),
            "response_size_bytes": _percentiles(self.response_bytes),
            "server_timing": {metric: _percentiles(values) for metric, values in sorted(self.server_timing.items())},
            "status_counts": dict(self.status_counts),
            "error_counts": dict(self.error_counts),
            "profile_summary": self.profile.summary(),
        }


class ExternalLatencyProbe:
    def __init__(
        self,
        *,
        env_file: Path,
        remote_base_url: str,
        path: str,
        run_id: str,
        requests: int,
        concurrency: int,
        client_mode: str,
        max_connections: int,
        profile_marketplace: bool,
        output: Path,
        client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
    ) -> None:
        if not path.startswith("/"):
            raise ValueError("--path must start with /")
        if requests < 1:
            raise ValueError("--requests must be >= 1")
        if concurrency < 1:
            raise ValueError("--concurrency must be >= 1")
        if client_mode not in {"shared", "new-per-request"}:
            raise ValueError("client_mode must be shared or new-per-request")
        self.env_file = env_file
        self.remote_base_url = remote_base_url.rstrip("/")
        self.path = path
        self.run_id = run_id
        self.requests = requests
        self.concurrency = concurrency
        self.client_mode = client_mode
        self.max_connections = max_connections
        self.profile_marketplace = profile_marketplace
        self.output = output
        self.client_factory = client_factory
        self.guardrails = require_staging_guardrails(env_file=env_file, run_id=run_id, api_base_url=self.remote_base_url)
        self.recorder = LatencyRecorder()
        self._access_token = self._build_marketplace_token(self.guardrails)

    def _build_marketplace_token(self, guardrails: StagingGuardrails) -> str | None:
        if not self.path.startswith("/api/v1/ads/"):
            return None
        secret_key = "JWT" + "_SECRET"
        secret = guardrails.env.get(secret_key)
        if not secret:
            return None
        now = int(time.time())
        return create_access_token_at(
            user_id=f"probe-remitter-{self.run_id}",
            role=DEFAULT_ROLE,
            status=DEFAULT_STATUS,
            secret=secret,
            ttl_seconds=300,
            issued_at=now,
        )

    def _headers(self, index: int) -> dict[str, str]:
        suffix = f"{self.run_id}_{index:05d}"
        headers = {
            "X-Request-Id": f"req_{suffix}",
            "X-Correlation-Id": f"corr_{self.run_id}_{uuid.uuid4().hex[:12]}",
            "X-NODO-Operation-Id": f"op_{suffix}",
            "X-NODO-Surface": DEFAULT_SURFACE,
            "Accept": "application/json",
        }
        if self.profile_marketplace:
            headers["X-NODO-Profile"] = "1"
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    async def _send_with_client(self, client: httpx.AsyncClient, index: int) -> None:
        started = time.perf_counter()
        response: httpx.Response | None = None
        error_code: str | None = None
        status_code = 599
        try:
            response = await client.get(self.path, headers=self._headers(index))
            status_code = response.status_code
        except httpx.RequestError as exc:
            error_code = type(exc).__name__
        except Exception as exc:  # pragma: no cover - defensive containment for probe output
            error_code = type(exc).__name__
        elapsed_ms = (time.perf_counter() - started) * 1000
        self.recorder.add_response(
            index=index,
            status_code=status_code,
            external_duration_ms=elapsed_ms,
            response=response,
            error_code=redact_text(error_code) if error_code else None,
        )

    async def _run_shared(self) -> None:
        semaphore = asyncio.Semaphore(self.concurrency)
        limits = make_shared_limits(self.max_connections)
        async with self.client_factory(
            base_url=self.remote_base_url,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            limits=limits,
        ) as client:

            async def worker(index: int) -> None:
                async with semaphore:
                    await self._send_with_client(client, index)

            await asyncio.gather(*(worker(index) for index in range(self.requests)))

    async def _run_new_per_request(self) -> None:
        semaphore = asyncio.Semaphore(self.concurrency)

        async def worker(index: int) -> None:
            async with semaphore:
                async with self.client_factory(
                    base_url=self.remote_base_url,
                    timeout=DEFAULT_TIMEOUT_SECONDS,
                    limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
                ) as client:
                    await self._send_with_client(client, index)

        await asyncio.gather(*(worker(index) for index in range(self.requests)))

    async def run_async(self) -> dict[str, Any]:
        started = time.perf_counter()
        if self.client_mode == "shared":
            await self._run_shared()
        else:
            await self._run_new_per_request()
        duration_seconds = round(time.perf_counter() - started, 4)
        summary = self.recorder.summary()
        total_errors = sum(count for status, count in summary["status_counts"].items() if not status.startswith(("2", "3")))
        payload = {
            "slice": "slice_26E_external_latency_path_isolation",
            "phase": "external_latency_probe",
            "run_id": self.run_id,
            "target": {
                "base_url": self.remote_base_url,
                "path": self.path.split("?", 1)[0],
            },
            "guardrails": guardrail_payload(self.guardrails),
            "client": {
                "mode": self.client_mode,
                "requests": self.requests,
                "concurrency": self.concurrency,
                "max_connections": self.max_connections,
                "profile_marketplace": self.profile_marketplace,
            },
            "duration_seconds": duration_seconds,
            "throughput_per_second": round(self.requests / duration_seconds, 4) if duration_seconds else 0.0,
            "summary": summary,
            "samples": self.recorder.samples,
            "exit_code": 1 if total_errors else 0,
        }
        write_json(self.output, payload)
        return payload

    def run(self) -> dict[str, Any]:
        return asyncio.run(self.run_async())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Staging external latency path isolation probe")
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--remote-base-url", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--requests", type=int, required=True)
    parser.add_argument("--concurrency", type=int, required=True)
    parser.add_argument("--client-mode", choices=["shared", "new-per-request"], required=True)
    parser.add_argument("--max-connections", type=int, default=50)
    parser.add_argument("--profile-marketplace", action="store_true")
    parser.add_argument("--output", required=True)
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        probe = ExternalLatencyProbe(
            env_file=Path(args.env_file),
            remote_base_url=args.remote_base_url,
            path=args.path,
            run_id=args.run_id,
            requests=args.requests,
            concurrency=args.concurrency,
            client_mode=args.client_mode,
            max_connections=args.max_connections,
            profile_marketplace=args.profile_marketplace,
            output=Path(args.output),
        )
        payload = probe.run()
    except Exception as exc:
        payload = {
            "slice": "slice_26E_external_latency_path_isolation",
            "phase": "external_latency_probe",
            "ok": False,
            "error": {"type": type(exc).__name__, "message": redact_text(str(exc))},
            "exit_code": 1,
        }
        output = getattr(args, "output", None)
        if output:
            write_json(Path(output), payload)
        print(json.dumps(payload, indent=2, default=str))
        return 1
    print(json.dumps(payload, indent=2, default=str))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
