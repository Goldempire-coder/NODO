from __future__ import annotations

import argparse
import asyncio
import json
import math
import shutil
import subprocess
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from local_hardening_common import DEFAULT_ENV_FILE, write_json
from staging_guardrails import require_staging_guardrails


DEFAULT_TIMEOUT_SECONDS = 30.0
LIGHT_ENDPOINTS = (
    ("health", "/api/v1/health"),
    ("ready", "/api/v1/ready"),
    ("version", "/api/v1/version"),
)
SENSITIVE_OUTPUT_MARKERS = (
    "DATABASE_URL",
    "REDIS_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "BOT_TOKEN",
    "BUSINESS_INTAKE_BOT_TOKEN",
    "JWT_SECRET",
    "access_token",
    "refresh_token",
    "storage_path",
    "account_value",
    "signed_url",
    "private_key",
    "seed phrase",
    "mnemonic",
)


@dataclass(frozen=True)
class Endpoint:
    label: str
    path: str


def percentiles(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}
    ordered = sorted(values)

    def pct(percent: float) -> float:
        index = min(len(ordered) - 1, max(0, math.ceil((percent / 100) * len(ordered)) - 1))
        return round(ordered[index], 4)

    return {"count": len(values), "p50_ms": pct(50), "p95_ms": pct(95), "p99_ms": pct(99)}


def parse_process_time_ms(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_server_timing(value: str | None) -> dict[str, float]:
    if not value:
        return {}
    parsed: dict[str, float] = {}
    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue
        pieces = [piece.strip() for piece in part.split(";") if piece.strip()]
        metric = pieces[0]
        for piece in pieces[1:]:
            if piece.startswith("dur="):
                try:
                    parsed[metric] = float(piece.removeprefix("dur="))
                except ValueError:
                    pass
    return parsed


def external_gap_ms(client_total_ms: float, backend_process_ms: float | None) -> float | None:
    if backend_process_ms is None:
        return None
    return round(max(0.0, client_total_ms - backend_process_ms), 4)


def parse_curl_write_out(line: str) -> dict[str, Any]:
    return json.loads(line)


def derive_curl_phases(sample: dict[str, Any]) -> dict[str, float]:
    lookup = float(sample.get("time_namelookup", 0.0))
    connect = float(sample.get("time_connect", 0.0))
    appconnect = float(sample.get("time_appconnect", 0.0))
    pretransfer = float(sample.get("time_pretransfer", 0.0))
    starttransfer = float(sample.get("time_starttransfer", 0.0))
    total = float(sample.get("time_total", 0.0))
    tls_start = appconnect if appconnect > 0 else connect
    return {
        "dns_ms": round(max(0.0, lookup) * 1000, 4),
        "tcp_connect_ms": round(max(0.0, connect - lookup) * 1000, 4),
        "tls_ms": round(max(0.0, appconnect - connect) * 1000, 4) if appconnect > 0 else 0.0,
        "pretransfer_ms": round(max(0.0, pretransfer - tls_start) * 1000, 4),
        "server_wait_ms": round(max(0.0, starttransfer - pretransfer) * 1000, 4),
        "download_ms": round(max(0.0, total - starttransfer) * 1000, 4),
        "total_ms": round(max(0.0, total) * 1000, 4),
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


def output_contains_sensitive_marker(payload: dict[str, Any]) -> list[str]:
    def values_only(value: Any) -> Any:
        if isinstance(value, dict):
            return [values_only(item) for item in value.values()]
        if isinstance(value, list):
            return [values_only(item) for item in value]
        return value

    serialized = json.dumps(values_only(payload), ensure_ascii=False)
    return [marker for marker in SENSITIVE_OUTPUT_MARKERS if marker.lower() in serialized.lower()]


def request_headers(*, run_id: str, endpoint: Endpoint, index: int) -> dict[str, str]:
    slug = f"{run_id}_{endpoint.label}_{index:05d}"
    return {
        "X-Request-Id": f"req_{slug}",
        "X-Correlation-Id": f"corr_{run_id}",
        "X-NODO-Operation-Id": f"op_{slug}",
        "X-NODO-Surface": "admin_web",
    }


def parse_request_start(value: str | None) -> dict[str, Any]:
    if not value:
        return {"raw": None, "epoch_ms": None, "status": "missing"}
    raw = value.strip()
    normalized = raw.removeprefix("t=").strip()
    try:
        numeric = float(normalized)
    except ValueError:
        return {"raw": raw, "epoch_ms": None, "status": "unparseable"}
    epoch_ms = numeric if numeric > 10_000_000_000 else numeric * 1000
    return {"raw": raw, "epoch_ms": round(epoch_ms, 4), "status": "parsed"}


def parse_railway_headers(headers: httpx.Headers | dict[str, str]) -> dict[str, Any]:
    server_timing = parse_server_timing(headers.get("Server-Timing"))
    request_start = parse_request_start(headers.get("X-Request-Start"))
    return {
        "x_railway_edge": headers.get("X-Railway-Edge") or headers.get("x-railway-edge"),
        "x_railway_request_id": headers.get("X-Railway-Request-Id") or headers.get("x-railway-request-id"),
        "x_request_start": request_start,
        "x_nodo_process_time_ms": parse_process_time_ms(headers.get("X-NODO-Process-Time-Ms")),
        "server_timing": server_timing,
        "x_request_id": headers.get("X-Request-Id"),
        "x_correlation_id": headers.get("X-Correlation-Id"),
        "x_nodo_operation_id": headers.get("X-NODO-Operation-Id"),
    }


def correlate_request_start(
    *,
    request_start: dict[str, Any],
    client_start_epoch_ms: float,
    headers_received_epoch_ms: float,
) -> dict[str, Any]:
    epoch_ms = request_start.get("epoch_ms")
    if not isinstance(epoch_ms, int | float):
        return {
            "status": "CLOCK_SKEW_LIMITATION",
            "reason": f"X-Request-Start {request_start.get('status', 'missing')}",
            "client_start_to_railway_start_ms": None,
            "railway_start_to_headers_ms": None,
        }
    client_to_railway = round(epoch_ms - client_start_epoch_ms, 4)
    railway_to_headers = round(headers_received_epoch_ms - epoch_ms, 4)
    if abs(client_to_railway) > 60_000 or railway_to_headers < -5_000:
        status = "CLOCK_SKEW_LIMITATION"
    else:
        status = "ok"
    return {
        "status": status,
        "client_start_to_railway_start_ms": client_to_railway,
        "railway_start_to_headers_ms": railway_to_headers,
    }


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    client = [float(item["client_total_ms"]) for item in records]
    backend = [float(item["backend_process_ms"]) for item in records if isinstance(item.get("backend_process_ms"), int | float)]
    gap = [float(item["external_gap_ms"]) for item in records if isinstance(item.get("external_gap_ms"), int | float)]
    ttfb = [float(item["ttfb_or_headers_ms"]) for item in records if isinstance(item.get("ttfb_or_headers_ms"), int | float)]
    read = [float(item["response_read_ms"]) for item in records if isinstance(item.get("response_read_ms"), int | float)]
    response_bytes = [float(item["response_bytes"]) for item in records]
    railway_start_to_headers = [
        float(item["request_start_correlation"]["railway_start_to_headers_ms"])
        for item in records
        if isinstance(item.get("request_start_correlation"), dict)
        and isinstance(item["request_start_correlation"].get("railway_start_to_headers_ms"), int | float)
        and item["request_start_correlation"].get("status") == "ok"
    ]
    client_to_railway = [
        float(item["request_start_correlation"]["client_start_to_railway_start_ms"])
        for item in records
        if isinstance(item.get("request_start_correlation"), dict)
        and isinstance(item["request_start_correlation"].get("client_start_to_railway_start_ms"), int | float)
        and item["request_start_correlation"].get("status") == "ok"
    ]
    status_counts = Counter(str(item["status"]) for item in records)
    error_counts = Counter(str(item["error_type"]) for item in records if item.get("error_type"))
    clock_skew_count = sum(
        1 for item in records if item.get("request_start_correlation", {}).get("status") == "CLOCK_SKEW_LIMITATION"
    )
    return {
        "requests": len(records),
        "status_counts": dict(status_counts),
        "request_error_summary": dict(error_counts),
        "client_total": percentiles(client),
        "backend_process": percentiles(backend),
        "external_gap": percentiles(gap),
        "ttfb_or_headers": percentiles(ttfb),
        "response_read": percentiles(read),
        "response_bytes": percentiles(response_bytes),
        "response_kb_p95": round(percentiles(response_bytes)["p95_ms"] / 1024, 4),
        "request_start_correlation": {
            "client_start_to_railway_start": percentiles(client_to_railway),
            "railway_start_to_headers": percentiles(railway_start_to_headers),
            "clock_skew_limited_count": clock_skew_count,
            "valid_count": len(railway_start_to_headers),
        },
    }


def summarize_by_edge(records: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("x_railway_edge") or "unknown")].append(record)
    return {edge: summarize_records(items) for edge, items in sorted(grouped.items())}


def summarize_curl_phases(samples: list[dict[str, Any]]) -> dict[str, Any]:
    phase_names = ("dns_ms", "tcp_connect_ms", "tls_ms", "pretransfer_ms", "server_wait_ms", "download_ms", "total_ms")
    return {
        phase: percentiles([float(sample["phases"][phase]) for sample in samples if isinstance(sample.get("phases"), dict)])
        for phase in phase_names
    }


def classify_curl_summary(summary: dict[str, Any]) -> str:
    phases = summary.get("phases", {})
    dns = float(phases.get("dns_ms", {}).get("p95_ms", 0.0))
    tcp = float(phases.get("tcp_connect_ms", {}).get("p95_ms", 0.0))
    tls = float(phases.get("tls_ms", {}).get("p95_ms", 0.0))
    wait = float(phases.get("server_wait_ms", {}).get("p95_ms", 0.0))
    if max(dns, tcp, tls) > max(wait, 1.0) * 1.5 and max(dns, tcp, tls) > 1000:
        return "BEFORE_RAILWAY_EDGE_LIKELY"
    if wait > max(dns, tcp, tls, 1.0) * 1.5 and wait > 1000:
        return "RAILWAY_EDGE_OR_INGRESS_LIKELY"
    return "INSUFFICIENT_EVIDENCE"


def classify_phase(summary: dict[str, Any], curl_phase: dict[str, Any] | None = None) -> dict[str, Any]:
    overall = summary.get("overall", {})
    backend_p95 = float(overall.get("backend_process", {}).get("p95_ms", 0.0))
    ttfb_p95 = float(overall.get("ttfb_or_headers", {}).get("p95_ms", 0.0))
    railway_to_headers_p95 = float(
        overall.get("request_start_correlation", {}).get("railway_start_to_headers", {}).get("p95_ms", 0.0)
    )
    clock_skew_count = int(overall.get("request_start_correlation", {}).get("clock_skew_limited_count", 0))
    secondary: list[str] = []
    if clock_skew_count:
        secondary.append("CLOCK_SKEW_LIMITED")
    if backend_p95 > 1000:
        return {"primary": "APP_RUNTIME_LIKELY", "secondary": sorted(set(secondary))}
    curl_classes = set((curl_phase or {}).get("classification", {}).values())
    if "BEFORE_RAILWAY_EDGE_LIKELY" in curl_classes and backend_p95 < 750:
        return {"primary": "BEFORE_RAILWAY_EDGE_LIKELY", "secondary": sorted(set(secondary))}
    if railway_to_headers_p95 > 1000 and backend_p95 < 750:
        return {"primary": "RAILWAY_EDGE_OR_INGRESS_LIKELY", "secondary": sorted(set(secondary))}
    if ttfb_p95 > 3000 and backend_p95 < 750:
        return {"primary": "RAILWAY_EDGE_OR_INGRESS_LIKELY", "secondary": sorted(set(secondary))}
    if secondary:
        return {"primary": "CLOCK_SKEW_LIMITED", "secondary": []}
    return {"primary": "INSUFFICIENT_EVIDENCE", "secondary": []}


class EdgeHeaderCorrelationProbe:
    def __init__(
        self,
        *,
        env_file: Path,
        run_id: str,
        remote_base_url: str | None,
        output: Path,
    ) -> None:
        self.guardrails = require_staging_guardrails(env_file=env_file, run_id=run_id, api_base_url=remote_base_url)
        self.run_id = run_id
        self.remote_base_url = (remote_base_url or self.guardrails.env["NODO_STAGING_API_BASE_URL"]).rstrip("/")
        self.output = output

    @property
    def endpoints(self) -> list[Endpoint]:
        return [Endpoint(label, path) for label, path in LIGHT_ENDPOINTS]

    async def request_once(self, client: httpx.AsyncClient, endpoint: Endpoint, index: int) -> dict[str, Any]:
        headers = request_headers(run_id=self.run_id, endpoint=endpoint, index=index)
        client_start_monotonic = time.perf_counter()
        client_start_epoch_ms = time.time() * 1000
        response: httpx.Response | None = None
        try:
            request = client.build_request("GET", endpoint.path, headers=headers)
            response = await client.send(request, stream=True)
            headers_received_monotonic = time.perf_counter()
            headers_received_epoch_ms = time.time() * 1000
            read_started_monotonic = time.perf_counter()
            await response.aread()
            response_done_monotonic = time.perf_counter()
        except httpx.RequestError as exc:
            response_done_monotonic = time.perf_counter()
            elapsed_ms = (response_done_monotonic - client_start_monotonic) * 1000
            return {
                "endpoint": endpoint.label,
                "path": endpoint.path,
                "status": 599,
                "client_start_monotonic": round(client_start_monotonic, 6),
                "headers_received_monotonic": None,
                "response_done_monotonic": round(response_done_monotonic, 6),
                "client_total_ms": round(elapsed_ms, 4),
                "ttfb_or_headers_ms": None,
                "response_read_ms": None,
                "response_bytes": 0,
                "backend_process_ms": None,
                "external_gap_ms": None,
                "x_railway_edge": None,
                "x_railway_request_id": None,
                "x_request_start": {"raw": None, "epoch_ms": None, "status": "missing"},
                "x_request_id": headers["X-Request-Id"],
                "x_correlation_id": headers["X-Correlation-Id"],
                "x_nodo_operation_id": headers["X-NODO-Operation-Id"],
                "server_timing": {},
                "request_start_correlation": {"status": "CLOCK_SKEW_LIMITATION", "reason": "response headers unavailable"},
                "error_type": classify_request_error(exc),
                "exception_class": type(exc).__name__,
                "exception_message_redacted": redact_exception_message(str(exc)),
                "response_started": False,
            }
        try:
            railway_headers = parse_railway_headers(response.headers)
            backend_process_ms = railway_headers["x_nodo_process_time_ms"] or railway_headers["server_timing"].get("app")
            client_total_ms = (response_done_monotonic - client_start_monotonic) * 1000
            request_start_correlation = correlate_request_start(
                request_start=railway_headers["x_request_start"],
                client_start_epoch_ms=client_start_epoch_ms,
                headers_received_epoch_ms=headers_received_epoch_ms,
            )
            return {
                "endpoint": endpoint.label,
                "path": endpoint.path,
                "status": response.status_code,
                "client_start_monotonic": round(client_start_monotonic, 6),
                "headers_received_monotonic": round(headers_received_monotonic, 6),
                "response_done_monotonic": round(response_done_monotonic, 6),
                "client_total_ms": round(client_total_ms, 4),
                "ttfb_or_headers_ms": round((headers_received_monotonic - client_start_monotonic) * 1000, 4),
                "response_read_ms": round((response_done_monotonic - read_started_monotonic) * 1000, 4),
                "response_bytes": len(response.content),
                "backend_process_ms": backend_process_ms,
                "external_gap_ms": external_gap_ms(client_total_ms, backend_process_ms),
                "x_railway_edge": railway_headers["x_railway_edge"],
                "x_railway_request_id": railway_headers["x_railway_request_id"],
                "x_request_start": railway_headers["x_request_start"],
                "x_nodo_process_time_ms": railway_headers["x_nodo_process_time_ms"],
                "server_timing": railway_headers["server_timing"],
                "x_request_id": railway_headers["x_request_id"],
                "x_correlation_id": railway_headers["x_correlation_id"],
                "x_nodo_operation_id": railway_headers["x_nodo_operation_id"],
                "request_start_correlation": request_start_correlation,
                "error_type": None,
                "response_started": True,
            }
        finally:
            await response.aclose()

    async def run_endpoint_load(self, *, endpoint: Endpoint, requests: int, concurrency: int) -> dict[str, Any]:
        limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
        semaphore = asyncio.Semaphore(concurrency)
        records: list[dict[str, Any]] = []
        started = time.perf_counter()
        async with httpx.AsyncClient(
            base_url=self.remote_base_url,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            limits=limits,
        ) as client:

            async def one(index: int) -> None:
                async with semaphore:
                    records.append(await self.request_once(client, endpoint, index))

            await asyncio.gather(*(one(index) for index in range(requests)))
        return {
            "endpoint": endpoint.label,
            "path": endpoint.path,
            "concurrency": concurrency,
            "requested_requests": requests,
            "actual_requests": len(records),
            "request_target_status": "matched" if len(records) == requests else "REQUEST_TARGET_MISMATCH",
            "duration_ms": round((time.perf_counter() - started) * 1000, 4),
            "summary": summarize_records(records),
            "by_railway_edge": summarize_by_edge(records),
            "records": records,
        }

    def run_load_mode(self, *, mode: str) -> dict[str, Any]:
        if mode == "sequential":
            requests = 20
            concurrency = 1
        elif mode == "c50":
            requests = 200
            concurrency = 50
        elif mode == "c100":
            requests = 300
            concurrency = 100
        else:
            raise ValueError(f"unsupported mode: {mode}")

        async def run() -> list[dict[str, Any]]:
            rows = []
            for endpoint in self.endpoints:
                rows.append(await self.run_endpoint_load(endpoint=endpoint, requests=requests, concurrency=concurrency))
            return rows

        rows = asyncio.run(run())
        summary = self.summarize_rows(rows)
        curl_phase = self.run_curl_phase_samples(samples_per_endpoint=20)
        payload = self._payload(
            phase=mode,
            data={
                "mode": mode,
                "concurrency": concurrency,
                "requests_per_endpoint": requests,
                "rows": rows,
                "summary": summary,
                "curl_phase": curl_phase,
                "exit_code": 0,
            },
        )
        payload["classification"] = classify_phase(summary, curl_phase)
        if any(row["request_target_status"] != "matched" for row in rows):
            payload["classification"] = {"primary": "INSUFFICIENT_EVIDENCE", "secondary": ["REQUEST_TARGET_MISMATCH"]}
            payload["exit_code"] = 1
        markers = output_contains_sensitive_marker(payload)
        payload["sensitive_marker_scan"] = {"status": "failed" if markers else "passed", "markers": markers}
        if markers:
            payload["exit_code"] = 1
        return payload

    @staticmethod
    def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
        all_records = [record for row in rows for record in row.get("records", [])]
        return {
            "overall": summarize_records(all_records),
            "by_endpoint": {row["endpoint"]: row["summary"] for row in rows},
            "by_railway_edge": summarize_by_edge(all_records),
        }

    def run_curl_phase_samples(self, *, samples_per_endpoint: int = 20) -> dict[str, Any]:
        curl_path = shutil.which("curl")
        if not curl_path:
            return {"status": "CURL_COMMAND_NOT_AVAILABLE", "rows": [], "classification": {}}
        rows: list[dict[str, Any]] = []
        for endpoint in self.endpoints:
            samples: list[dict[str, Any]] = []
            for index in range(samples_per_endpoint):
                headers: list[str] = []
                for key, value in request_headers(run_id=self.run_id, endpoint=endpoint, index=index).items():
                    headers.extend(["-H", f"{key}: {value}"])
                completed = subprocess.run(
                    [
                        curl_path,
                        "-sS",
                        "-o",
                        "NUL" if _is_windows() else "/dev/null",
                        "--max-time",
                        str(int(DEFAULT_TIMEOUT_SECONDS)),
                        *headers,
                        "-w",
                        "@scripts/curl-format-ttfb.txt",
                        f"{self.remote_base_url}{endpoint.path}",
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
                "endpoint": endpoint.label,
                "path": endpoint.path,
                "samples": len(samples),
                "status_counts": dict(Counter(str(sample.get("http_code", sample.get("status", "unknown"))) for sample in samples)),
                "phases": summarize_curl_phases(samples),
            }
            row["classification"] = classify_curl_summary(row)
            rows.append(row)
        return {"status": "completed", "rows": rows, "classification": {row["endpoint"]: row["classification"] for row in rows}}

    def _payload(self, *, phase: str, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "slice": "slice_33F_edge_header_correlation",
            "phase": phase,
            "run_id": self.run_id,
            "target": self.remote_base_url,
            "guardrails": {
                "checked": True,
                "app_env": self.guardrails.env.get("APP_ENV"),
                "environment_kind": self.guardrails.env.get("NODO_ENVIRONMENT_KIND"),
                "staging_validation": self.guardrails.env.get("NODO_STAGING_VALIDATION"),
            },
            "cleanup": {"required": False, "reason": "Light endpoint probe creates no synthetic data."},
            **data,
        }


def build_summary(*, sequential_path: Path, c50_path: Path, c100_path: Path, output: Path, run_id: str) -> dict[str, Any]:
    sequential = _read_payload(sequential_path)
    c50 = _read_payload(c50_path)
    c100 = _read_payload(c100_path)
    payloads = [item for item in (sequential, c50, c100) if item]
    primary = _choose_primary(payloads)
    state = "EDGE_CORRELATION_SOURCE_IDENTIFIED"
    if primary in {"CLOCK_SKEW_LIMITED", "INSUFFICIENT_EVIDENCE"}:
        state = primary
    payload = {
        "slice": "slice_33F_edge_header_correlation",
        "state": state,
        "run_id": run_id,
        "classification": {
            "primary": primary,
            "secondary": sorted(
                {
                    secondary
                    for item in payloads
                    for secondary in item.get("classification", {}).get("secondary", [])
                }
            ),
        },
        "sequential": _compact_payload(sequential),
        "c50": _compact_payload(c50),
        "c100": _compact_payload(c100),
        "evidence": {
            "sequential": str(sequential_path),
            "c50": str(c50_path),
            "c100": str(c100_path),
            "summary": str(output),
        },
        "recommendation": _recommendation(primary),
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


def _read_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _choose_primary(payloads: list[dict[str, Any]]) -> str:
    primaries = [item.get("classification", {}).get("primary") for item in payloads]
    for candidate in ("APP_RUNTIME_LIKELY", "BEFORE_RAILWAY_EDGE_LIKELY", "RAILWAY_EDGE_OR_INGRESS_LIKELY"):
        if candidate in primaries:
            return candidate
    if "CLOCK_SKEW_LIMITED" in primaries:
        return "CLOCK_SKEW_LIMITED"
    return "INSUFFICIENT_EVIDENCE"


def _compact_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {"status": "missing"}
    rows = payload.get("rows", [])
    return {
        "status": "completed",
        "classification": payload.get("classification"),
        "mode": payload.get("mode"),
        "summary": payload.get("summary"),
        "endpoint_table": [
            {
                "endpoint": row.get("endpoint"),
                "status_counts": row.get("summary", {}).get("status_counts"),
                "client_p95_ms": row.get("summary", {}).get("client_total", {}).get("p95_ms"),
                "ttfb_p95_ms": row.get("summary", {}).get("ttfb_or_headers", {}).get("p95_ms"),
                "backend_p95_ms": row.get("summary", {}).get("backend_process", {}).get("p95_ms"),
                "request_start_valid": row.get("summary", {}).get("request_start_correlation", {}).get("valid_count"),
                "railway_edges": sorted(row.get("by_railway_edge", {}).keys()),
                "errors": row.get("summary", {}).get("request_error_summary"),
            }
            for row in rows
        ],
        "curl_phase": payload.get("curl_phase"),
    }


def _recommendation(primary: str) -> str:
    if primary == "BEFORE_RAILWAY_EDGE_LIKELY":
        return "Continue with connection pattern and burst spacing probes before changing product or infrastructure."
    if primary == "RAILWAY_EDGE_OR_INGRESS_LIKELY":
        return "Collect Railway HTTP logs and edge request IDs for provider-side correlation."
    if primary == "APP_RUNTIME_LIKELY":
        return "Investigate app runtime queue only after confirming X-NODO process time remains high."
    return "Run the smallest follow-up probe needed to separate clock skew, edge timing, and client transport phases."


def _is_windows() -> bool:
    return "\\" in str(Path.cwd())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--remote-base-url", default=None)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mode", choices=["sequential", "c50", "c100", "summary"], required=True)
    parser.add_argument("--sequential-input", default=None)
    parser.add_argument("--c50-input", default=None)
    parser.add_argument("--c100-input", default=None)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    if args.mode == "summary":
        payload = build_summary(
            sequential_path=Path(args.sequential_input),
            c50_path=Path(args.c50_input),
            c100_path=Path(args.c100_input),
            output=output,
            run_id=args.run_id,
        )
        return int(payload.get("exit_code", 0))

    probe = EdgeHeaderCorrelationProbe(
        env_file=Path(args.env_file),
        remote_base_url=args.remote_base_url,
        run_id=args.run_id,
        output=output,
    )
    payload = probe.run_load_mode(mode=args.mode)
    write_json(output, payload)
    return int(payload.get("exit_code", 0))


if __name__ == "__main__":
    raise SystemExit(main())
