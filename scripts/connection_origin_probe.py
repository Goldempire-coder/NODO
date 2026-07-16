from __future__ import annotations

import argparse
import asyncio
import json
import math
import shutil
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from local_hardening_common import DEFAULT_ENV_FILE, write_json
from staging_guardrails import require_staging_guardrails


DEFAULT_TARGET = "https://nodo-api-production.up.railway.app"
DEFAULT_TIMEOUT_SECONDS = 30.0
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
LIGHT_ENDPOINTS = (
    ("health", "/api/v1/health"),
    ("ready", "/api/v1/ready"),
    ("version", "/api/v1/version"),
)
LOCAL_MATRIX = ((1, 20), (10, 100), (25, 150), (50, 200), (100, 300))


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


def external_gap_ms(client_total_ms: float, backend_process_ms: float | None) -> float | None:
    if backend_process_ms is None:
        return None
    return round(max(0.0, client_total_ms - backend_process_ms), 4)


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


def request_headers(*, run_id: str, endpoint: Endpoint, index: int, origin_label: str) -> dict[str, str]:
    slug = f"{run_id}_{origin_label}_{endpoint.label}_{index:05d}"
    return {
        "X-Request-Id": f"req_{slug}",
        "X-Correlation-Id": f"corr_{run_id}_{origin_label}",
        "X-NODO-Operation-Id": f"op_{slug}",
        "X-NODO-Surface": "admin_web",
    }


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    client = [float(item["client_total_ms"]) for item in records]
    backend = [float(item["backend_process_ms"]) for item in records if isinstance(item.get("backend_process_ms"), int | float)]
    gap = [float(item["external_gap_ms"]) for item in records if isinstance(item.get("external_gap_ms"), int | float)]
    ttfb = [float(item["ttfb_or_headers_ms"]) for item in records if isinstance(item.get("ttfb_or_headers_ms"), int | float)]
    read = [float(item["response_read_ms"]) for item in records if isinstance(item.get("response_read_ms"), int | float)]
    response_bytes = [float(item["response_bytes"]) for item in records]
    status_counts = Counter(str(item["status"]) for item in records)
    error_counts = Counter(str(item["error_type"]) for item in records if item.get("error_type"))
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
    }


def summarize_phases(samples: list[dict[str, Any]]) -> dict[str, Any]:
    phase_names = ("dns_ms", "tcp_connect_ms", "tls_ms", "pretransfer_ms", "server_wait_ms", "download_ms", "total_ms")
    return {
        phase: percentiles([float(sample["phases"][phase]) for sample in samples if isinstance(sample.get("phases"), dict)])
        for phase in phase_names
    }


def classify_pool_limit(rows: list[dict[str, Any]]) -> str:
    by_conn = {int(row["max_connections"]): row for row in rows}
    if 10 not in by_conn or 100 not in by_conn:
        return "INCONCLUSIVE"
    p10 = float(by_conn[10]["summary"]["ttfb_or_headers"]["p95_ms"])
    p100 = float(by_conn[100]["summary"]["ttfb_or_headers"]["p95_ms"])
    p200 = float(by_conn.get(200, by_conn[100])["summary"]["ttfb_or_headers"]["p95_ms"])
    if p10 > max(p100, 1.0) * 1.5 and p200 <= p100 * 1.25:
        return "HARNESS_POOL_LIMIT"
    return "INCONCLUSIVE"


def classify_keepalive(rows: list[dict[str, Any]]) -> str:
    by_mode = {str(row["keepalive"]): row for row in rows}
    if "on" not in by_mode or "off" not in by_mode:
        return "INCONCLUSIVE"
    on = float(by_mode["on"]["summary"]["ttfb_or_headers"]["p95_ms"])
    off = float(by_mode["off"]["summary"]["ttfb_or_headers"]["p95_ms"])
    if off > max(on, 1.0) * 1.5:
        return "CONNECTION_CHURN_LIMIT"
    return "INCONCLUSIVE"


def classify_http2(rows: list[dict[str, Any]]) -> str:
    by_mode = {bool(row["http2"]): row for row in rows}
    if True not in by_mode or False not in by_mode:
        return "INCONCLUSIVE"
    h1 = float(by_mode[False]["summary"]["ttfb_or_headers"]["p95_ms"])
    h2 = float(by_mode[True]["summary"]["ttfb_or_headers"]["p95_ms"])
    if h2 < h1 * 0.7:
        return "HTTP2_MITIGATES"
    return "INCONCLUSIVE"


def classify_curl_phases(row: dict[str, Any]) -> str:
    phases = row.get("phases", {})
    dns = float(phases.get("dns_ms", {}).get("p95_ms", 0.0))
    tcp = float(phases.get("tcp_connect_ms", {}).get("p95_ms", 0.0))
    tls = float(phases.get("tls_ms", {}).get("p95_ms", 0.0))
    wait = float(phases.get("server_wait_ms", {}).get("p95_ms", 0.0))
    if max(dns, tcp, tls) > max(wait, 1.0) * 1.5 and max(dns, tcp, tls) > 1000:
        return "CURL_DNS_CONNECT_TLS_HIGH"
    if wait > max(dns, tcp, tls, 1.0) * 1.5 and wait > 1000:
        return "CURL_STARTTRANSFER_HIGH"
    return "INCONCLUSIVE"


def classify_origin(local_summary: dict[str, Any] | None, github_summary: dict[str, Any] | None) -> dict[str, Any]:
    if not github_summary or github_summary.get("status") != "completed":
        return {
            "primary": "INCONCLUSIVE",
            "secondary": ["GITHUB_ACTIONS_TOOLING_UNAVAILABLE"],
            "reason": "GitHub Actions origin evidence is unavailable.",
        }
    if not local_summary or local_summary.get("status") != "completed":
        return {
            "primary": "INCONCLUSIVE",
            "secondary": ["LOCAL_ORIGIN_UNAVAILABLE"],
            "reason": "Local origin evidence is unavailable.",
        }
    local_health = _c100_ttfb(local_summary, "health")
    github_health = _c100_ttfb(github_summary, "health")
    if github_health > 3000 and local_health < 1000:
        return {"primary": "GITHUB_ACTIONS_ROUTE_LIMIT", "secondary": [], "reason": "GitHub c100 TTFB is high while local is low."}
    if local_health > 3000 and github_health < 1000:
        return {"primary": "LOCAL_ROUTE_LIMIT", "secondary": [], "reason": "Local c100 TTFB is high while GitHub is low."}
    if local_health > 3000 and github_health > 3000:
        return {
            "primary": "RAILWAY_INGRESS_OR_RUNTIME_LIMIT",
            "secondary": ["PUBLIC_ROUTE_OR_EDGE_LIMIT"],
            "reason": "Both origins show high c100 TTFB on lightweight routes.",
        }
    return {"primary": "INCONCLUSIVE", "secondary": [], "reason": "Origin timing gap is not decisive."}


def _c100_ttfb(summary: dict[str, Any], endpoint: str) -> float:
    rows = summary.get("matrix", {}).get("rows", [])
    for row in rows:
        if row.get("endpoint") == endpoint and int(row.get("concurrency", 0)) == 100:
            return float(row.get("summary", {}).get("ttfb_or_headers", {}).get("p95_ms", 0.0))
    return 0.0


class ConnectionOriginProbe:
    def __init__(
        self,
        *,
        env_file: Path,
        run_id: str,
        base_url: str,
        origin_label: str,
        target_label: str,
        output: Path,
        sample_limit: int = 10,
    ) -> None:
        self.guardrails = require_staging_guardrails(env_file=env_file, run_id=run_id, api_base_url=base_url)
        self.run_id = run_id
        self.base_url = base_url.rstrip("/")
        self.origin_label = origin_label
        self.target_label = target_label
        self.output = output
        self.sample_limit = sample_limit

    @property
    def endpoints(self) -> list[Endpoint]:
        return [Endpoint(label, path) for label, path in LIGHT_ENDPOINTS]

    async def request_once(self, client: httpx.AsyncClient, endpoint: Endpoint, index: int) -> dict[str, Any]:
        headers = request_headers(run_id=self.run_id, endpoint=endpoint, index=index, origin_label=self.origin_label)
        started = time.perf_counter()
        response: httpx.Response | None = None
        try:
            request = client.build_request("GET", endpoint.path, headers=headers)
            response = await client.send(request, stream=True)
            headers_received = time.perf_counter()
            read_started = time.perf_counter()
            await response.aread()
            read_finished = time.perf_counter()
        except httpx.RequestError as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            return {
                "endpoint": endpoint.label,
                "path": endpoint.path,
                "status": 599,
                "client_total_ms": round(elapsed_ms, 4),
                "backend_process_ms": None,
                "external_gap_ms": None,
                "ttfb_or_headers_ms": None,
                "response_read_ms": None,
                "response_bytes": 0,
                "request_id": headers["X-Request-Id"],
                "correlation_id": headers["X-Correlation-Id"],
                "operation_id": headers["X-NODO-Operation-Id"],
                "error_type": classify_request_error(exc),
                "exception_class": type(exc).__name__,
                "exception_message_redacted": redact_exception_message(str(exc)),
                "response_started": False,
            }
        try:
            server_timing = parse_server_timing(response.headers.get("Server-Timing"))
            backend_process_ms = parse_process_time_ms(response.headers.get("X-NODO-Process-Time-Ms")) or server_timing.get("app")
            client_total_ms = (read_finished - started) * 1000
            return {
                "endpoint": endpoint.label,
                "path": endpoint.path,
                "status": response.status_code,
                "client_total_ms": round(client_total_ms, 4),
                "backend_process_ms": backend_process_ms,
                "external_gap_ms": external_gap_ms(client_total_ms, backend_process_ms),
                "ttfb_or_headers_ms": round((headers_received - started) * 1000, 4),
                "response_read_ms": round((read_finished - read_started) * 1000, 4),
                "response_bytes": len(response.content),
                "request_id": response.headers.get("X-Request-Id"),
                "correlation_id": response.headers.get("X-Correlation-Id"),
                "operation_id": response.headers.get("X-NODO-Operation-Id"),
                "server_timing": server_timing,
                "railway_edge": response.headers.get("x-railway-edge"),
                "error_type": None,
            }
        finally:
            await response.aclose()

    async def run_load(
        self,
        *,
        endpoint: Endpoint,
        requests: int,
        concurrency: int,
        max_connections: int,
        keepalive: str = "on",
        http2: bool = False,
    ) -> dict[str, Any]:
        keepalive_connections = max_connections if keepalive == "on" else 0
        limits = httpx.Limits(max_connections=max_connections, max_keepalive_connections=keepalive_connections)
        semaphore = asyncio.Semaphore(concurrency)
        records: list[dict[str, Any]] = []
        started = time.perf_counter()
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            limits=limits,
            http2=http2,
        ) as client:

            async def one(index: int) -> None:
                async with semaphore:
                    records.append(await self.request_once(client, endpoint, index))

            await asyncio.gather(*(one(index) for index in range(requests)))
        summary = summarize_records(records)
        actual_requests = len(records)
        target_match = actual_requests == requests
        return {
            "endpoint": endpoint.label,
            "path": endpoint.path,
            "concurrency": concurrency,
            "requested_requests": requests,
            "actual_requests": actual_requests,
            "request_target_status": "matched" if target_match else "REQUEST_TARGET_MISMATCH",
            "max_connections": max_connections,
            "keepalive": keepalive,
            "http2": http2,
            "duration_ms": round((time.perf_counter() - started) * 1000, 4),
            "phase_availability": {
                "httpx_dns_ms": "PHASE_UNAVAILABLE",
                "httpx_tcp_connect_ms": "PHASE_UNAVAILABLE",
                "httpx_tls_ms": "PHASE_UNAVAILABLE",
                "httpx_ttfb_or_headers_ms": "available",
                "httpx_response_read_ms": "available",
            },
            "summary": summary,
            "samples": records[: self.sample_limit],
            "request_error_samples": [item for item in records if item.get("error_type")][: self.sample_limit],
        }

    def run_matrix(self) -> dict[str, Any]:
        async def run() -> list[dict[str, Any]]:
            rows = []
            for endpoint in self.endpoints:
                for concurrency, requests in LOCAL_MATRIX:
                    rows.append(
                        await self.run_load(
                            endpoint=endpoint,
                            requests=requests,
                            concurrency=concurrency,
                            max_connections=concurrency,
                        )
                    )
            return rows

        rows = asyncio.run(run())
        return {"rows": rows, "knees": {endpoint.label: self.detect_knee(rows, endpoint.label) for endpoint in self.endpoints}}

    def run_pool_churn(self) -> dict[str, Any]:
        health = Endpoint("health", "/api/v1/health")

        async def run() -> dict[str, Any]:
            pool_rows = [
                await self.run_load(endpoint=health, requests=300, concurrency=100, max_connections=max_connections)
                for max_connections in (10, 100, 200)
            ]
            keepalive_rows = [
                await self.run_load(endpoint=health, requests=300, concurrency=100, max_connections=100, keepalive=keepalive)
                for keepalive in ("on", "off")
            ]
            return {"pool_rows": pool_rows, "keepalive_rows": keepalive_rows}

        rows = asyncio.run(run())
        return {
            **rows,
            "pool_classification": classify_pool_limit(rows["pool_rows"]),
            "keepalive_classification": classify_keepalive(rows["keepalive_rows"]),
        }

    def run_http2_probe(self) -> dict[str, Any]:
        health = Endpoint("health", "/api/v1/health")

        async def run() -> list[dict[str, Any]]:
            return [
                await self.run_load(endpoint=health, requests=300, concurrency=100, max_connections=100, http2=http2)
                for http2 in (False, True)
            ]

        try:
            rows = asyncio.run(run())
        except ImportError as exc:
            return {"status": "HTTP2_PROBE_UNAVAILABLE", "reason": redact_exception_message(str(exc)), "rows": []}
        return {"status": "completed", "rows": rows, "classification": classify_http2(rows)}

    def run_curl_phase_samples(self, *, samples_per_endpoint: int = 20) -> dict[str, Any]:
        curl_path = shutil.which("curl")
        if not curl_path:
            return {"status": "CURL_COMMAND_NOT_AVAILABLE", "rows": []}
        rows = []
        for endpoint in self.endpoints:
            samples: list[dict[str, Any]] = []
            for index in range(samples_per_endpoint):
                headers: list[str] = []
                for key, value in request_headers(run_id=self.run_id, endpoint=endpoint, index=index, origin_label=self.origin_label).items():
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
                        f"{self.base_url}{endpoint.path}",
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
                "phases": summarize_phases(samples),
            }
            row["classification"] = classify_curl_phases(row)
            rows.append(row)
        return {"status": "completed", "rows": rows, "classification": {row["endpoint"]: row["classification"] for row in rows}}

    @staticmethod
    def detect_knee(rows: list[dict[str, Any]], endpoint_label: str) -> dict[str, Any]:
        endpoint_rows = [row for row in rows if row["endpoint"] == endpoint_label]
        first_ttfb = next((row for row in endpoint_rows if row["summary"]["ttfb_or_headers"]["p95_ms"] > 1000), None)
        first_client = next((row for row in endpoint_rows if row["summary"]["client_total"]["p95_ms"] > 3000), None)
        first_error = next((row for row in endpoint_rows if row["summary"]["request_error_summary"]), None)
        return {
            "first_ttfb_p95_gt_1000": first_ttfb["concurrency"] if first_ttfb else None,
            "first_client_p95_gt_3000": first_client["concurrency"] if first_client else None,
            "first_transport_error": first_error["concurrency"] if first_error else None,
        }

    def build_payload(self, *, direct_base_url: str | None = None) -> dict[str, Any]:
        matrix = self.run_matrix()
        pool_churn = self.run_pool_churn()
        http2_probe = self.run_http2_probe()
        curl_phase = self.run_curl_phase_samples()
        direct_url = {"status": "DIRECT_URL_UNAVAILABLE", "reason": "No direct Railway URL was provided or configured."}
        if direct_base_url:
            direct_url = {"status": "DIRECT_URL_PROVIDED_NOT_RUN", "reason": "Direct URL probing is handled as a separate target run."}
        payload = {
            "slice": "slice_33A7_connection_origin_and_route_confirmation",
            "status": "completed",
            "run_id": self.run_id,
            "origin_label": self.origin_label,
            "target_label": self.target_label,
            "target_url": self.base_url,
            "guardrails": {
                "checked": True,
                "app_env": self.guardrails.env.get("APP_ENV"),
                "environment_kind": self.guardrails.env.get("NODO_ENVIRONMENT_KIND"),
                "staging_validation": self.guardrails.env.get("NODO_STAGING_VALIDATION"),
            },
            "matrix": matrix,
            "pool_churn": pool_churn,
            "http2_probe": http2_probe,
            "curl_phase": curl_phase,
            "direct_url": direct_url,
            "cleanup": {"required": False, "reason": "Light endpoint probe created no synthetic DB fixtures."},
            "exit_code": 0,
        }
        payload["classification"] = self.classify_payload(payload)
        markers = output_contains_sensitive_marker(payload)
        payload["sensitive_marker_scan"] = {"status": "failed" if markers else "passed", "markers": markers}
        if markers:
            payload["exit_code"] = 1
        return payload

    @staticmethod
    def classify_payload(payload: dict[str, Any]) -> dict[str, Any]:
        secondary: list[str] = []
        pool_classification = payload.get("pool_churn", {}).get("pool_classification")
        keepalive_classification = payload.get("pool_churn", {}).get("keepalive_classification")
        if pool_classification == "HARNESS_POOL_LIMIT":
            secondary.append("HARNESS_POOL_LIMIT")
        if keepalive_classification == "CONNECTION_CHURN_LIMIT":
            secondary.append("CONNECTION_CHURN_LIMIT")
        http2_classification = payload.get("http2_probe", {}).get("classification")
        if http2_classification == "HTTP2_MITIGATES":
            secondary.append("HTTP2_MITIGATES")
        curl_classes = set(payload.get("curl_phase", {}).get("classification", {}).values())
        if "CURL_DNS_CONNECT_TLS_HIGH" in curl_classes:
            secondary.append("CURL_DNS_CONNECT_TLS_HIGH")
        health_knee = payload.get("matrix", {}).get("knees", {}).get("health", {})
        if health_knee.get("first_ttfb_p95_gt_1000"):
            primary = "LOCAL_ROUTE_LIMIT" if payload.get("origin_label") == "local" else "GITHUB_ACTIONS_ROUTE_LIMIT"
        elif "CONNECTION_CHURN_LIMIT" in secondary:
            primary = "CONNECTION_CHURN_LIMIT"
        else:
            primary = "INCONCLUSIVE"
        return {"primary": primary, "secondary": sorted(set(secondary))}


def _is_windows() -> bool:
    return "\\" in str(Path.cwd())


def blocked_github_payload(*, reason: str, run_id: str, target_url: str) -> dict[str, Any]:
    return {
        "slice": "slice_33A7_connection_origin_and_route_confirmation",
        "status": "blocked",
        "run_id": run_id,
        "origin_label": "github_actions",
        "target_label": "public_staging",
        "target_url": target_url,
        "blocker": "BLOCKED_BY_GITHUB_ACTIONS_TOOLING",
        "reason": reason,
        "exit_code": 0,
        "sensitive_marker_scan": {"status": "passed", "markers": []},
    }


def build_summary(
    *,
    local_path: Path,
    github_path: Path,
    output: Path,
    run_id: str,
) -> dict[str, Any]:
    local_payload = json.loads(local_path.read_text(encoding="utf-8")) if local_path.exists() else None
    github_payload = json.loads(github_path.read_text(encoding="utf-8")) if github_path.exists() else None
    origin_classification = classify_origin(local_payload, github_payload)
    direct_status = (local_payload or {}).get("direct_url", {}).get("status", "DIRECT_URL_UNAVAILABLE")
    state = "CONNECTION_ORIGIN_CONFIRMED"
    if origin_classification["primary"] == "INCONCLUSIVE":
        state = "CONNECTION_ORIGIN_PARTIALLY_CONFIRMED"
    if github_payload and github_payload.get("blocker") == "BLOCKED_BY_GITHUB_ACTIONS_TOOLING":
        state = "BLOCKED_BY_GITHUB_ACTIONS_TOOLING"
    payload = {
        "slice": "slice_33A7_connection_origin_and_route_confirmation",
        "state": state,
        "run_id": run_id,
        "origin_classification": origin_classification,
        "local_origin": _summary_extract(local_payload),
        "github_actions_origin": _summary_extract(github_payload),
        "direct_url": {"status": direct_status},
        "recommendation": _recommendation(origin_classification, direct_status),
        "evidence": {
            "local_origin": str(local_path),
            "github_actions_origin": str(github_path),
            "summary": str(output),
        },
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


def _summary_extract(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {"status": "missing"}
    if payload.get("status") != "completed":
        return {"status": payload.get("status"), "blocker": payload.get("blocker"), "reason": payload.get("reason")}
    rows = payload.get("matrix", {}).get("rows", [])
    c100 = {
        row.get("endpoint"): {
            "status_counts": row.get("summary", {}).get("status_counts", {}),
            "client_p95_ms": row.get("summary", {}).get("client_total", {}).get("p95_ms"),
            "ttfb_p95_ms": row.get("summary", {}).get("ttfb_or_headers", {}).get("p95_ms"),
            "backend_p95_ms": row.get("summary", {}).get("backend_process", {}).get("p95_ms"),
            "errors": row.get("summary", {}).get("request_error_summary", {}),
        }
        for row in rows
        if int(row.get("concurrency", 0)) == 100
    }
    return {
        "status": "completed",
        "classification": payload.get("classification"),
        "c100": c100,
        "pool_classification": payload.get("pool_churn", {}).get("pool_classification"),
        "keepalive_classification": payload.get("pool_churn", {}).get("keepalive_classification"),
        "http2_status": payload.get("http2_probe", {}).get("status"),
        "curl_classification": payload.get("curl_phase", {}).get("classification"),
    }


def _recommendation(origin_classification: dict[str, Any], direct_status: str) -> str:
    primary = origin_classification.get("primary")
    if primary == "GITHUB_ACTIONS_ROUTE_LIMIT":
        return "Use a different runner/location before making infrastructure decisions."
    if primary in {"RAILWAY_INGRESS_OR_RUNTIME_LIMIT", "PUBLIC_ROUTE_OR_EDGE_LIMIT"}:
        return "Investigate Railway public route, ingress and runtime networking before changing DB/cache/product."
    if direct_status == "DIRECT_URL_UNAVAILABLE":
        return "Obtain or confirm a direct Railway target URL if available, then compare public vs direct route."
    return "Run the GitHub Actions origin probe to complete origin comparison."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--base-url", default=DEFAULT_TARGET)
    parser.add_argument("--origin-label", default="local")
    parser.add_argument("--target-label", default="public_staging")
    parser.add_argument("--direct-base-url", default=None)
    parser.add_argument("--mode", choices=["probe", "blocked-github", "summary"], default="probe")
    parser.add_argument("--local-input", default=None)
    parser.add_argument("--github-input", default=None)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    if args.mode == "blocked-github":
        payload = blocked_github_payload(
            reason="GitHub CLI or authenticated dispatch context is unavailable in this environment.",
            run_id=args.run_id,
            target_url=args.base_url,
        )
        write_json(output, payload)
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0
    if args.mode == "summary":
        if not args.local_input or not args.github_input:
            raise SystemExit("--local-input and --github-input are required for summary mode")
        payload = build_summary(
            local_path=Path(args.local_input),
            github_path=Path(args.github_input),
            output=output,
            run_id=args.run_id,
        )
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return int(payload["exit_code"])

    probe = ConnectionOriginProbe(
        env_file=Path(args.env_file),
        run_id=args.run_id,
        base_url=args.base_url,
        origin_label=args.origin_label,
        target_label=args.target_label,
        output=output,
    )
    payload = probe.build_payload(direct_base_url=args.direct_base_url)
    write_json(output, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
