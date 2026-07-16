from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from edge_header_correlation_probe import (
    DEFAULT_TIMEOUT_SECONDS,
    SENSITIVE_OUTPUT_MARKERS,
    derive_curl_phases,
    external_gap_ms,
    output_contains_sensitive_marker,
    parse_curl_write_out,
    parse_process_time_ms,
    parse_server_timing,
    percentiles,
)
from local_hardening_common import DEFAULT_ENV_FILE, write_json
from staging_guardrails import require_staging_guardrails


ENDPOINTS = {
    "version": "/api/v1/version",
    "health": "/api/v1/health",
    "ready": "/api/v1/ready",
}
PRODUCT_GATE_MAX_CONCURRENCY = 50


@dataclass(frozen=True)
class TrafficPlan:
    label: str
    endpoint: str
    path: str
    requests: int
    concurrency: int
    traffic_shape: str
    spacing_ms: int | None = None
    ramp_duration_seconds: int | None = None
    rps_target: int | None = None
    keepalive: str = "on"
    max_connections: int | None = None


def schedule_offsets(
    *,
    requests: int,
    traffic_shape: str,
    spacing_ms: int | None = None,
    ramp_duration_seconds: int | None = None,
    rps_target: int | None = None,
) -> list[float]:
    if requests <= 0:
        return []
    if traffic_shape == "burst":
        return [0.0 for _ in range(requests)]
    if traffic_shape == "spaced":
        spacing_seconds = (spacing_ms or 0) / 1000
        return [round(index * spacing_seconds, 6) for index in range(requests)]
    if traffic_shape == "ramp":
        duration = float(ramp_duration_seconds or 0)
        if requests == 1:
            return [0.0]
        return [round(index * duration / (requests - 1), 6) for index in range(requests)]
    if traffic_shape == "steady":
        if not rps_target or rps_target <= 0:
            raise ValueError("steady traffic requires positive rps_target")
        return [round(index / rps_target, 6) for index in range(requests)]
    raise ValueError(f"unsupported traffic_shape: {traffic_shape}")


def validate_run_purpose(*, concurrency: int, run_purpose: str) -> None:
    if concurrency > PRODUCT_GATE_MAX_CONCURRENCY and run_purpose != "infra-probe":
        raise ValueError("c100+ is an infra-probe only; product gates are capped at c50")


def default_plans() -> list[TrafficPlan]:
    plans: list[TrafficPlan] = []

    def add(
        endpoint: str,
        concurrency: int,
        requests: int,
        traffic_shape: str,
        suffix: str,
        *,
        spacing_ms: int | None = None,
        ramp_duration_seconds: int | None = None,
        rps_target: int | None = None,
        keepalive: str = "on",
    ) -> None:
        plans.append(
            TrafficPlan(
                label=f"{endpoint}_c{concurrency}_{suffix}",
                endpoint=endpoint,
                path=ENDPOINTS[endpoint],
                requests=requests,
                concurrency=concurrency,
                traffic_shape=traffic_shape,
                spacing_ms=spacing_ms,
                ramp_duration_seconds=ramp_duration_seconds,
                rps_target=rps_target,
                keepalive=keepalive,
                max_connections=concurrency,
            )
        )

    add("version", 100, 300, "burst", "burst_0ms")
    for spacing_ms in (10, 50, 100):
        add("version", 100, 300, "spaced", f"spacing_{spacing_ms}ms", spacing_ms=spacing_ms)
    for seconds in (30, 60):
        add("version", 100, 300, "ramp", f"ramp_{seconds}s", ramp_duration_seconds=seconds)
    for rps in (5, 10, 20):
        add("version", 100, 100 if rps < 20 else 200, "steady", f"steady_{rps}rps", rps_target=rps)

    for endpoint in ("health", "ready"):
        add(endpoint, 100, 300, "burst", "burst_0ms")
        add(endpoint, 100, 300, "spaced", "spacing_50ms", spacing_ms=50)
        add(endpoint, 100, 300, "ramp", "ramp_60s", ramp_duration_seconds=60)

    add("version", 50, 200, "burst", "burst_0ms")
    add("version", 50, 200, "ramp", "ramp_30s", ramp_duration_seconds=30)

    add("version", 100, 300, "burst", "burst_0ms_keepalive_off", keepalive="off")
    add("version", 100, 300, "ramp", "ramp_60s_keepalive_off", ramp_duration_seconds=60, keepalive="off")
    return plans


def request_headers(*, run_id: str, plan: TrafficPlan, index: int) -> dict[str, str]:
    slug = f"{run_id}_{plan.label}_{index:05d}"
    return {
        "X-Request-Id": f"req_{slug}",
        "X-Correlation-Id": f"corr_{run_id}",
        "X-NODO-Operation-Id": f"op_{slug}",
        "X-NODO-Surface": "admin_web",
    }


def classify_request_error(exc: httpx.RequestError) -> str:
    if isinstance(exc, httpx.ConnectTimeout):
        return "CONNECT_TIMEOUT"
    if isinstance(exc, httpx.ReadTimeout):
        return "READ_TIMEOUT"
    if isinstance(exc, httpx.WriteTimeout):
        return "WRITE_TIMEOUT"
    if isinstance(exc, httpx.PoolTimeout):
        return "POOL_TIMEOUT"
    if isinstance(exc, httpx.ConnectError):
        return "CONNECT_ERROR"
    if isinstance(exc, httpx.RemoteProtocolError):
        return "REMOTE_DISCONNECT"
    if isinstance(exc, httpx.ProtocolError):
        return "PROTOCOL_ERROR"
    return "UNKNOWN_CLIENT_ERROR"


def redact_exception_message(value: str) -> str:
    lowered = value.lower()
    if any(marker.lower() in lowered for marker in SENSITIVE_OUTPUT_MARKERS):
        return "[REDACTED]"
    return value[:240]


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    client = [float(item["client_total_ms"]) for item in records]
    backend = [float(item["backend_process_ms"]) for item in records if isinstance(item.get("backend_process_ms"), int | float)]
    gap = [float(item["external_gap_ms"]) for item in records if isinstance(item.get("external_gap_ms"), int | float)]
    ttfb = [float(item["ttfb_or_headers_ms"]) for item in records if isinstance(item.get("ttfb_or_headers_ms"), int | float)]
    read = [float(item["response_read_ms"]) for item in records if isinstance(item.get("response_read_ms"), int | float)]
    status_counts = Counter(str(item["status"]) for item in records)
    error_counts = Counter(str(item["error_type"]) for item in records if item.get("error_type"))
    edges = Counter(str(item.get("x_railway_edge") or "unknown") for item in records)
    return {
        "requests": len(records),
        "status_counts": dict(status_counts),
        "request_error_summary": dict(error_counts),
        "client_total": percentiles(client),
        "ttfb_or_headers": percentiles(ttfb),
        "response_read": percentiles(read),
        "backend_process": percentiles(backend),
        "external_gap": percentiles(gap),
        "x_railway_edge_distribution": dict(edges),
    }


def summarize_curl_phases(samples: list[dict[str, Any]]) -> dict[str, Any]:
    phase_names = ("dns_ms", "tcp_connect_ms", "tls_ms", "pretransfer_ms", "server_wait_ms", "download_ms", "total_ms")
    return {
        phase: percentiles([float(sample["phases"][phase]) for sample in samples if isinstance(sample.get("phases"), dict)])
        for phase in phase_names
    }


def classify_curl_row(row: dict[str, Any]) -> str:
    phases = row.get("phases", {})
    tcp = float(phases.get("tcp_connect_ms", {}).get("p95_ms", 0.0))
    tls = float(phases.get("tls_ms", {}).get("p95_ms", 0.0))
    wait = float(phases.get("server_wait_ms", {}).get("p95_ms", 0.0))
    if max(tcp, tls) > max(wait, 1.0) * 1.5 and max(tcp, tls) > 1000:
        return "TCP_CONNECT_OR_TLS_HIGH"
    if wait > max(tcp, tls, 1.0) * 1.5 and wait > 1000:
        return "SERVER_WAIT_HIGH"
    return "INSUFFICIENT_EVIDENCE"


class BurstSpacingProbe:
    def __init__(
        self,
        *,
        env_file: Path,
        run_id: str,
        remote_base_url: str | None,
        output: Path,
        run_purpose: str = "infra-probe",
        sample_limit: int = 20,
    ) -> None:
        self.guardrails = require_staging_guardrails(env_file=env_file, run_id=run_id, api_base_url=remote_base_url)
        self.run_id = run_id
        self.remote_base_url = (remote_base_url or self.guardrails.env["NODO_STAGING_API_BASE_URL"]).rstrip("/")
        self.output = output
        self.run_purpose = run_purpose
        self.sample_limit = sample_limit
        for plan in default_plans():
            validate_run_purpose(concurrency=plan.concurrency, run_purpose=run_purpose)

    async def request_once(self, client: httpx.AsyncClient, plan: TrafficPlan, index: int, scheduled_offset: float, run_started: float) -> dict[str, Any]:
        target_time = run_started + scheduled_offset
        delay = target_time - time.perf_counter()
        if delay > 0:
            await asyncio.sleep(delay)
        headers = request_headers(run_id=self.run_id, plan=plan, index=index)
        actual_start = time.perf_counter()
        response: httpx.Response | None = None
        try:
            request = client.build_request("GET", plan.path, headers=headers)
            response = await client.send(request, stream=True)
            headers_received = time.perf_counter()
            read_started = time.perf_counter()
            await response.aread()
            read_finished = time.perf_counter()
        except httpx.RequestError as exc:
            finished = time.perf_counter()
            return {
                "index": index,
                "status": 599,
                "scheduled_offset_ms": round(scheduled_offset * 1000, 4),
                "actual_start_offset_ms": round((actual_start - run_started) * 1000, 4),
                "client_total_ms": round((finished - actual_start) * 1000, 4),
                "ttfb_or_headers_ms": None,
                "response_read_ms": None,
                "backend_process_ms": None,
                "external_gap_ms": None,
                "x_railway_edge": None,
                "request_id": headers["X-Request-Id"],
                "correlation_id": headers["X-Correlation-Id"],
                "operation_id": headers["X-NODO-Operation-Id"],
                "error_type": classify_request_error(exc),
                "exception_class": type(exc).__name__,
                "exception_message_redacted": redact_exception_message(str(exc)),
            }
        try:
            server_timing = parse_server_timing(response.headers.get("Server-Timing"))
            backend_process_ms = parse_process_time_ms(response.headers.get("X-NODO-Process-Time-Ms")) or server_timing.get("app")
            client_total_ms = (read_finished - actual_start) * 1000
            return {
                "index": index,
                "status": response.status_code,
                "scheduled_offset_ms": round(scheduled_offset * 1000, 4),
                "actual_start_offset_ms": round((actual_start - run_started) * 1000, 4),
                "client_total_ms": round(client_total_ms, 4),
                "ttfb_or_headers_ms": round((headers_received - actual_start) * 1000, 4),
                "response_read_ms": round((read_finished - read_started) * 1000, 4),
                "backend_process_ms": backend_process_ms,
                "external_gap_ms": external_gap_ms(client_total_ms, backend_process_ms),
                "x_railway_edge": response.headers.get("X-Railway-Edge") or response.headers.get("x-railway-edge"),
                "request_id": response.headers.get("X-Request-Id"),
                "correlation_id": response.headers.get("X-Correlation-Id"),
                "operation_id": response.headers.get("X-NODO-Operation-Id"),
                "x_railway_request_id": response.headers.get("X-Railway-Request-Id") or response.headers.get("x-railway-request-id"),
                "error_type": None,
            }
        finally:
            await response.aclose()

    async def run_plan(self, plan: TrafficPlan) -> dict[str, Any]:
        max_connections = plan.max_connections or plan.concurrency
        keepalive_connections = max_connections if plan.keepalive == "on" else 0
        limits = httpx.Limits(max_connections=max_connections, max_keepalive_connections=keepalive_connections)
        semaphore = asyncio.Semaphore(plan.concurrency)
        offsets = schedule_offsets(
            requests=plan.requests,
            traffic_shape=plan.traffic_shape,
            spacing_ms=plan.spacing_ms,
            ramp_duration_seconds=plan.ramp_duration_seconds,
            rps_target=plan.rps_target,
        )
        records: list[dict[str, Any]] = []
        run_started = time.perf_counter()
        async with httpx.AsyncClient(
            base_url=self.remote_base_url,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            limits=limits,
        ) as client:

            async def one(index: int, offset: float) -> None:
                async with semaphore:
                    records.append(await self.request_once(client, plan, index, offset, run_started))

            await asyncio.gather(*(one(index, offset) for index, offset in enumerate(offsets)))
        duration_seconds = time.perf_counter() - run_started
        summary = summarize_records(records)
        actual_requests = len(records)
        return {
            "label": plan.label,
            "endpoint": plan.endpoint,
            "path": plan.path,
            "requested_requests": plan.requests,
            "actual_requests": actual_requests,
            "request_target_status": "matched" if actual_requests == plan.requests else "REQUEST_TARGET_MISMATCH",
            "traffic_shape": plan.traffic_shape,
            "spacing_ms": plan.spacing_ms,
            "ramp_duration_seconds": plan.ramp_duration_seconds,
            "rps_target": plan.rps_target,
            "concurrency": plan.concurrency,
            "max_connections": max_connections,
            "keepalive": plan.keepalive,
            "duration_seconds": round(duration_seconds, 4),
            "summary": summary,
            "samples": sorted(records, key=lambda item: item["index"])[: self.sample_limit],
            "request_error_samples": [item for item in records if item.get("error_type")][: self.sample_limit],
        }

    def run_curl_phase_samples(self, *, samples_per_endpoint: int = 10) -> dict[str, Any]:
        curl_path = shutil.which("curl")
        if not curl_path:
            return {"status": "CURL_COMMAND_NOT_AVAILABLE", "rows": [], "classification": {}}
        rows = []
        for endpoint, path in ENDPOINTS.items():
            samples: list[dict[str, Any]] = []
            plan = TrafficPlan(
                label=f"{endpoint}_curl",
                endpoint=endpoint,
                path=path,
                requests=samples_per_endpoint,
                concurrency=1,
                traffic_shape="steady",
                rps_target=1,
            )
            for index in range(samples_per_endpoint):
                curl_headers: list[str] = []
                for key, value in request_headers(run_id=self.run_id, plan=plan, index=index).items():
                    curl_headers.extend(["-H", f"{key}: {value}"])
                completed = subprocess.run(
                    [
                        curl_path,
                        "-sS",
                        "-o",
                        "NUL" if _is_windows() else "/dev/null",
                        "--max-time",
                        str(int(DEFAULT_TIMEOUT_SECONDS)),
                        *curl_headers,
                        "-w",
                        "@scripts/curl-format-ttfb.txt",
                        f"{self.remote_base_url}{path}",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=DEFAULT_TIMEOUT_SECONDS + 5,
                )
                if completed.returncode != 0:
                    samples.append({"status": "curl_error", "returncode": completed.returncode})
                    continue
                try:
                    parsed = parse_curl_write_out(completed.stdout.strip())
                except json.JSONDecodeError:
                    samples.append({"status": "parse_error"})
                    continue
                parsed["phases"] = derive_curl_phases(parsed)
                samples.append(parsed)
            row = {
                "endpoint": endpoint,
                "path": path,
                "samples": len(samples),
                "status_counts": dict(Counter(str(sample.get("http_code", sample.get("status", "unknown"))) for sample in samples)),
                "phases": summarize_curl_phases(samples),
            }
            row["classification"] = classify_curl_row(row)
            rows.append(row)
        return {"status": "completed", "rows": rows, "classification": {row["endpoint"]: row["classification"] for row in rows}}

    def build_payload(self) -> dict[str, Any]:
        async def run() -> list[dict[str, Any]]:
            rows = []
            for plan in default_plans():
                rows.append(await self.run_plan(plan))
            return rows

        rows = asyncio.run(run())
        curl_phase = self.run_curl_phase_samples()
        classification = classify_rows(rows)
        payload = {
            "slice": "slice_33I_burst_spacing_and_arrival_rate_policy",
            "run_id": self.run_id,
            "target": self.remote_base_url,
            "run_purpose": self.run_purpose,
            "guardrails": {
                "checked": True,
                "app_env": self.guardrails.env.get("APP_ENV"),
                "environment_kind": self.guardrails.env.get("NODO_ENVIRONMENT_KIND"),
                "staging_validation": self.guardrails.env.get("NODO_STAGING_VALIDATION"),
            },
            "rows": rows,
            "curl_phase": curl_phase,
            "classification": classification,
            "policy_recommendation": policy_recommendation(classification),
            "cleanup": {"required": False, "reason": "Light endpoint burst/spacing probe creates no synthetic data."},
            "exit_code": 0,
        }
        if any(row["request_target_status"] != "matched" for row in rows):
            payload["classification"] = {"primary": "INSUFFICIENT_EVIDENCE", "secondary": ["REQUEST_TARGET_MISMATCH"]}
            payload["exit_code"] = 1
        markers = output_contains_sensitive_marker(payload)
        payload["sensitive_marker_scan"] = {"status": "failed" if markers else "passed", "markers": markers}
        if markers:
            payload["exit_code"] = 1
        return payload


def _row_by_label(rows: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    return next((row for row in rows if row.get("label") == label), None)


def _ttfb_p95(row: dict[str, Any] | None) -> float:
    if not row:
        return 0.0
    return float(row.get("summary", {}).get("ttfb_or_headers", {}).get("p95_ms", 0.0))


def _errors(row: dict[str, Any] | None) -> int:
    if not row:
        return 0
    return sum(int(count) for count in row.get("summary", {}).get("request_error_summary", {}).values())


def _strong_improvement(baseline: float, candidate: float) -> bool:
    return baseline > 0 and candidate <= baseline * 0.4


def classify_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    secondary: set[str] = set()
    version_burst = _row_by_label(rows, "version_c100_burst_0ms")
    version_spacing_50 = _row_by_label(rows, "version_c100_spacing_50ms")
    version_spacing_100 = _row_by_label(rows, "version_c100_spacing_100ms")
    version_ramp_30 = _row_by_label(rows, "version_c100_ramp_30s")
    version_ramp_60 = _row_by_label(rows, "version_c100_ramp_60s")
    version_c50_burst = _row_by_label(rows, "version_c50_burst_0ms")
    version_keepalive_off_burst = _row_by_label(rows, "version_c100_burst_0ms_keepalive_off")
    version_keepalive_off_ramp = _row_by_label(rows, "version_c100_ramp_60s_keepalive_off")
    steady_rows = [row for row in rows if row.get("endpoint") == "version" and row.get("traffic_shape") == "steady"]

    burst_p95 = _ttfb_p95(version_burst)
    spacing_candidates = [candidate for candidate in (_ttfb_p95(version_spacing_50), _ttfb_p95(version_spacing_100)) if candidate]
    ramp_candidates = [candidate for candidate in (_ttfb_p95(version_ramp_30), _ttfb_p95(version_ramp_60)) if candidate]
    steady_candidates = [_ttfb_p95(row) for row in steady_rows if _ttfb_p95(row)]

    any_spacing_improves = any(_strong_improvement(burst_p95, value) for value in [*spacing_candidates, *ramp_candidates])
    any_ramp_acceptable = any(value < 1500 for value in ramp_candidates)
    all_ramp_or_steady_limited = bool(ramp_candidates or steady_candidates) and all(
        value >= 1500 for value in [*ramp_candidates, *steady_candidates]
    )
    c50_ok = 0 < _ttfb_p95(version_c50_burst) < 1500 and _errors(version_c50_burst) == 0
    c100_ramp_limited = bool(ramp_candidates) and min(ramp_candidates) >= 1500

    off_burst = _ttfb_p95(version_keepalive_off_burst)
    off_ramp = _ttfb_p95(version_keepalive_off_ramp)
    if off_burst > max(burst_p95, 1.0) * 1.5 or (ramp_candidates and off_ramp > max(min(ramp_candidates), 1.0) * 1.5):
        secondary.add("KEEPALIVE_REQUIRED")

    if any_spacing_improves:
        secondary.add("BURST_CONNECTION_CHURN_CONFIRMED")
        primary = "ARRIVAL_RATE_MITIGATES" if any_ramp_acceptable else "BURST_CONNECTION_CHURN_CONFIRMED"
    elif c50_ok and c100_ramp_limited:
        primary = "STAGING_ROUTE_LIMIT_CONFIRMED"
    elif all_ramp_or_steady_limited and burst_p95 >= 1500:
        primary = "STEADY_TRAFFIC_STILL_LIMITED"
    else:
        primary = "INSUFFICIENT_EVIDENCE"

    return {
        "primary": primary,
        "secondary": sorted(secondary),
        "inputs": {
            "version_c100_burst_ttfb_p95_ms": burst_p95,
            "version_c100_spacing_50_ttfb_p95_ms": _ttfb_p95(version_spacing_50),
            "version_c100_spacing_100_ttfb_p95_ms": _ttfb_p95(version_spacing_100),
            "version_c100_ramp_30_ttfb_p95_ms": _ttfb_p95(version_ramp_30),
            "version_c100_ramp_60_ttfb_p95_ms": _ttfb_p95(version_ramp_60),
            "version_c50_burst_ttfb_p95_ms": _ttfb_p95(version_c50_burst),
        },
    }


def policy_recommendation(classification: dict[str, Any]) -> dict[str, Any]:
    primary = classification.get("primary")
    product_shape = "ramp_or_steady" if primary in {"ARRIVAL_RATE_MITIGATES", "BURST_CONNECTION_CHURN_CONFIRMED"} else "c50_ramp_preferred"
    return {
        "product_gate_max_concurrency": 50,
        "product_gate_traffic_shape": product_shape,
        "c100_plus": "infra-probe only",
        "keepalive": "required for representative tests",
        "burst": "reserved for edge/transport stress",
    }


def build_summary(*, probe_path: Path, output: Path, run_id: str) -> dict[str, Any]:
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    rows = probe.get("rows", [])
    classification = probe.get("classification", {"primary": "INSUFFICIENT_EVIDENCE", "secondary": []})
    primary = classification.get("primary")
    if primary == "ARRIVAL_RATE_MITIGATES":
        state = "ARRIVAL_RATE_SOURCE_IDENTIFIED"
    elif primary == "BURST_CONNECTION_CHURN_CONFIRMED":
        state = "BURST_CHURN_CONFIRMED"
    elif primary in {"STEADY_TRAFFIC_STILL_LIMITED", "STAGING_ROUTE_LIMIT_CONFIRMED"}:
        state = "STEADY_TRAFFIC_LIMIT_CONFIRMED"
    else:
        state = "INSUFFICIENT_EVIDENCE"
    payload = {
        "slice": "slice_33I_burst_spacing_and_arrival_rate_policy",
        "state": state,
        "run_id": run_id,
        "classification": classification,
        "traffic_shape_table": compact_rows(rows),
        "edge_distribution": aggregate_edges(rows),
        "curl_phase": probe.get("curl_phase"),
        "policy_recommendation": probe.get("policy_recommendation"),
        "evidence": {"probe": str(probe_path), "summary": str(output)},
        "confirmations": {
            "product_changed": False,
            "frontend_changed": False,
            "migrations_changed": False,
            "infrastructure_changed": False,
            "deployed": False,
            "production_touched": False,
            "ready_for_real_use_declared": False,
        },
        "exit_code": 0,
    }
    markers = output_contains_sensitive_marker(payload)
    payload["sensitive_marker_scan"] = {"status": "failed" if markers else "passed", "markers": markers}
    if markers:
        payload["exit_code"] = 1
    write_json(output, payload)
    return payload


def compact_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact = []
    for row in rows:
        summary = row.get("summary", {})
        compact.append(
            {
                "label": row.get("label"),
                "endpoint": row.get("endpoint"),
                "traffic_shape": row.get("traffic_shape"),
                "spacing_ms": row.get("spacing_ms"),
                "ramp_duration_seconds": row.get("ramp_duration_seconds"),
                "rps_target": row.get("rps_target"),
                "concurrency": row.get("concurrency"),
                "keepalive": row.get("keepalive"),
                "requested_requests": row.get("requested_requests"),
                "actual_requests": row.get("actual_requests"),
                "status_counts": summary.get("status_counts"),
                "errors": summary.get("request_error_summary"),
                "client_p95_ms": summary.get("client_total", {}).get("p95_ms"),
                "client_p99_ms": summary.get("client_total", {}).get("p99_ms"),
                "ttfb_p95_ms": summary.get("ttfb_or_headers", {}).get("p95_ms"),
                "ttfb_p99_ms": summary.get("ttfb_or_headers", {}).get("p99_ms"),
                "response_read_p95_ms": summary.get("response_read", {}).get("p95_ms"),
                "backend_p95_ms": summary.get("backend_process", {}).get("p95_ms"),
                "edge_distribution": summary.get("x_railway_edge_distribution"),
                "duration_seconds": row.get("duration_seconds"),
            }
        )
    return compact


def aggregate_edges(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(row.get("summary", {}).get("x_railway_edge_distribution", {}))
    return dict(counts)


def _is_windows() -> bool:
    return "\\" in str(Path.cwd())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--remote-base-url", default=None)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mode", choices=["probe", "summary"], default="probe")
    parser.add_argument("--run-purpose", choices=["product-gate", "infra-probe"], default="infra-probe")
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    if args.mode == "summary":
        payload = build_summary(probe_path=Path(args.input), output=output, run_id=args.run_id)
        return int(payload.get("exit_code", 0))

    probe = BurstSpacingProbe(
        env_file=Path(args.env_file),
        run_id=args.run_id,
        remote_base_url=args.remote_base_url,
        output=output,
        run_purpose=args.run_purpose,
    )
    payload = probe.build_payload()
    write_json(output, payload)
    return int(payload.get("exit_code", 0))


if __name__ == "__main__":
    raise SystemExit(main())
