from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from capacity_real import classify_request_error, parse_process_time_ms, parse_server_timing, redact_exception_message
from cleanup_synthetic_run import validate_run_id
from local_hardening_common import DEFAULT_ENV_FILE, write_json
from local_smoke import LocalSmoke
from marketplace_delivery_diagnostics import SENSITIVE_OUTPUT_MARKERS, external_gap_ms, percentiles
from staging_guardrails import require_staging_guardrails
from app.shared.db.connection import connect


DEFAULT_LIGHT_REQUESTS = 300
DEFAULT_MARKETPLACE_REQUESTS = 300
DEFAULT_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class ProbeEndpoint:
    label: str
    method: str
    path: str
    group: str


def search_path(*, amount_slot: int | None = None, cursor: str | None = None, limit: int = 50) -> str:
    params: dict[str, str] = {"delivery_method": "pago_movil_ve", "limit": str(limit)}
    if amount_slot is None:
        params["sort"] = "trust"
    else:
        params.update({"amount_usd": f"{20 + amount_slot * 100}.00", "payment_method": "zelle"})
    if cursor:
        params["cursor"] = cursor
    return f"/api/v1/ads/search?{urlencode(params)}"


def response_next_cursor(response: httpx.Response | None) -> str | None:
    if response is None:
        return None
    try:
        body = response.json()
    except ValueError:
        return None
    data = body.get("data") if isinstance(body, dict) else None
    cursor = data.get("next_cursor") if isinstance(data, dict) else None
    return cursor if isinstance(cursor, str) and cursor else None


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


def classify_endpoint_summary(summary: dict[str, Any]) -> str:
    errors = summary.get("error_counts", {})
    if errors:
        return "MIXED"
    client_p95 = float(summary.get("client", {}).get("p95_ms", 0.0))
    backend_p95 = float(summary.get("backend_process", {}).get("p95_ms", 0.0))
    ttfb_p95 = float(summary.get("ttfb_or_headers", {}).get("p95_ms", 0.0))
    read_p95 = float(summary.get("response_read", {}).get("p95_ms", 0.0))
    response_kb = float(summary.get("response_kb_p95", 0.0))
    if backend_p95 < 750 and response_kb < 100 and client_p95 > 3000:
        if ttfb_p95 > max(read_p95, backend_p95) * 1.5:
            return "PUBLIC_ROUTE_OR_EDGE_QUEUE"
        return "NETWORK_DELIVERY"
    if backend_p95 >= 750:
        return "RUNTIME_QUEUE"
    return "INSUFFICIENT_EVIDENCE"


def detect_knee(rows: list[dict[str, Any]]) -> dict[str, Any]:
    first_ttfb = next((row for row in rows if row["summary"]["ttfb_or_headers"]["p95_ms"] > 1000), None)
    first_client = next((row for row in rows if row["summary"]["client"]["p95_ms"] > 3000), None)
    first_error = next((row for row in rows if row["summary"]["error_counts"]), None)
    return {
        "first_ttfb_p95_gt_1000": first_ttfb["concurrency"] if first_ttfb else None,
        "first_client_p95_gt_3000": first_client["concurrency"] if first_client else None,
        "first_transport_error": first_error["concurrency"] if first_error else None,
    }


def classify_pool_isolation(rows: list[dict[str, Any]]) -> str:
    by_conn = {int(row["max_connections"]): row for row in rows}
    if 10 not in by_conn or 100 not in by_conn:
        return "INSUFFICIENT_EVIDENCE"
    p10 = float(by_conn[10]["summary"]["ttfb_or_headers"]["p95_ms"])
    p100 = float(by_conn[100]["summary"]["ttfb_or_headers"]["p95_ms"])
    p200 = float(by_conn.get(200, by_conn[100])["summary"]["ttfb_or_headers"]["p95_ms"])
    if p10 > max(p100, 1.0) * 1.5 and p200 <= p100 * 1.25:
        return "HARNESS_POOL_LIMIT"
    return "INSUFFICIENT_EVIDENCE"


def classify_keepalive(rows: list[dict[str, Any]]) -> str:
    by_mode = {str(row["keepalive"]): row for row in rows}
    if "on" not in by_mode or "off" not in by_mode:
        return "INSUFFICIENT_EVIDENCE"
    on = float(by_mode["on"]["summary"]["ttfb_or_headers"]["p95_ms"])
    off = float(by_mode["off"]["summary"]["ttfb_or_headers"]["p95_ms"])
    if off > max(on, 1.0) * 1.5:
        return "CONNECTION_REUSE_IMPORTANT"
    return "INSUFFICIENT_EVIDENCE"


def classify_curl_summary(summary: dict[str, Any]) -> str:
    phases = summary.get("phases", {})
    dns = float(phases.get("dns_ms", {}).get("p95_ms", 0.0))
    tcp = float(phases.get("tcp_connect_ms", {}).get("p95_ms", 0.0))
    tls = float(phases.get("tls_ms", {}).get("p95_ms", 0.0))
    wait = float(phases.get("server_wait_ms", {}).get("p95_ms", 0.0))
    if max(dns, tcp, tls) > max(wait, 1.0) * 1.5 and max(dns, tcp, tls) > 1000:
        return "CURL_DNS_CONNECT_TLS_HIGH"
    if wait > max(dns, tcp, tls, 1.0) * 1.5 and wait > 1000:
        return "CURL_STARTTRANSFER_HIGH"
    return "INSUFFICIENT_EVIDENCE"


class ProbeRecorder:
    def __init__(self, *, sample_limit: int = 25) -> None:
        self.records: list[dict[str, Any]] = []
        self.samples: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []
        self.sample_limit = sample_limit

    def add_response(
        self,
        *,
        endpoint: ProbeEndpoint,
        index: int,
        status: int,
        client_total_ms: float,
        response: httpx.Response | None,
        ttfb_or_headers_ms: float | None = None,
        response_read_ms: float | None = None,
        error_type: str | None = None,
    ) -> None:
        headers = response.headers if response is not None else {}
        server_timing = parse_server_timing(headers.get("Server-Timing"))
        backend_process_ms = parse_process_time_ms(headers.get("X-NODO-Process-Time-Ms")) or server_timing.get("app")
        record = {
            "endpoint_label": endpoint.label,
            "endpoint": endpoint.path.split("?", 1)[0],
            "group": endpoint.group,
            "method": endpoint.method,
            "status": status,
            "client_total_ms": round(client_total_ms, 4),
            "backend_process_ms": backend_process_ms,
            "external_gap_ms": external_gap_ms(client_total_ms, backend_process_ms),
            "ttfb_or_headers_ms": round(ttfb_or_headers_ms, 4) if isinstance(ttfb_or_headers_ms, int | float) else None,
            "response_read_ms": round(response_read_ms, 4) if isinstance(response_read_ms, int | float) else None,
            "response_bytes": len(response.content) if response is not None else 0,
            "request_id": headers.get("X-Request-Id"),
            "correlation_id": headers.get("X-Correlation-Id"),
            "operation_id": headers.get("X-NODO-Operation-Id"),
            "server_timing": server_timing,
            "railway_edge": headers.get("x-railway-edge"),
            "error_type": error_type,
        }
        self.records.append(record)
        if len(self.samples) < self.sample_limit:
            self.samples.append({"index": index, **record})

    def add_error(self, *, endpoint: ProbeEndpoint, index: int, exc: httpx.RequestError, elapsed_ms: float, headers: dict[str, str]) -> None:
        classification = classify_request_error(exc)
        error = {
            "index": index,
            "endpoint_label": endpoint.label,
            "endpoint": endpoint.path.split("?", 1)[0],
            "group": endpoint.group,
            "method": endpoint.method,
            "status": 599,
            "client_total_ms": round(elapsed_ms, 4),
            "request_id": headers["X-Request-Id"],
            "correlation_id": headers["X-Correlation-Id"],
            "operation_id": headers["X-NODO-Operation-Id"],
            "exception_class": type(exc).__name__,
            "exception_message_redacted": redact_exception_message(str(exc)),
            "classification": classification,
            "response_started": False,
        }
        self.errors.append(error)
        self.add_response(
            endpoint=endpoint,
            index=index,
            status=599,
            client_total_ms=elapsed_ms,
            response=None,
            error_type=classification,
        )

    @staticmethod
    def _summary_for(records: list[dict[str, Any]]) -> dict[str, Any]:
        client = [float(item["client_total_ms"]) for item in records]
        backend = [float(item["backend_process_ms"]) for item in records if isinstance(item.get("backend_process_ms"), int | float)]
        gap = [float(item["external_gap_ms"]) for item in records if isinstance(item.get("external_gap_ms"), int | float)]
        ttfb = [float(item["ttfb_or_headers_ms"]) for item in records if isinstance(item.get("ttfb_or_headers_ms"), int | float)]
        read = [float(item["response_read_ms"]) for item in records if isinstance(item.get("response_read_ms"), int | float)]
        response_bytes = [float(item["response_bytes"]) for item in records]
        status_counts = Counter(str(item["status"]) for item in records)
        error_counts = Counter(str(item["error_type"]) for item in records if item.get("error_type"))
        summary = {
            "requests": len(records),
            "status_counts": dict(status_counts),
            "error_counts": dict(error_counts),
            "client": percentiles(client),
            "backend_process": percentiles(backend),
            "external_gap": percentiles(gap),
            "ttfb_or_headers": percentiles(ttfb),
            "response_read": percentiles(read),
            "response_bytes": percentiles(response_bytes),
            "response_kb_p95": round(percentiles(response_bytes)["p95_ms"] / 1024, 4),
        }
        summary["classification"] = classify_endpoint_summary(summary)
        return summary

    def summary(self) -> dict[str, Any]:
        by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in self.records:
            by_label[str(record["endpoint_label"])].append(record)
        return {
            "overall": self._summary_for(self.records),
            "by_endpoint_label": {label: self._summary_for(items) for label, items in sorted(by_label.items())},
            "request_error_summary": {
                "total": len(self.errors),
                "by_classification": dict(Counter(error["classification"] for error in self.errors)),
                "by_endpoint_label": dict(Counter(error["endpoint_label"] for error in self.errors)),
            },
            "samples": self.samples,
            "request_error_samples": self.errors[: self.sample_limit],
        }


class TTFBQueueProbe:
    def __init__(
        self,
        *,
        env_file: Path,
        remote_base_url: str | None,
        run_id: str,
        output: Path,
        fixture_run_id: str | None = None,
        sample_limit: int = 25,
    ) -> None:
        validate_run_id(run_id)
        self.env_file = env_file
        self.run_id = run_id
        self.output = output
        self.fixture_run_id = fixture_run_id
        self.guardrails = require_staging_guardrails(env_file=env_file, run_id=run_id, api_base_url=remote_base_url)
        self.remote_base_url = (remote_base_url or self.guardrails.env["NODO_STAGING_API_BASE_URL"]).rstrip("/")
        self.sample_limit = sample_limit
        self._smoke: LocalSmoke | None = None
        self._marketplace_login: dict[str, Any] | None = None
        self._marketplace_auth_created = False

    def fixture_ad_id(self) -> str | None:
        if not self.fixture_run_id:
            return None
        like = f"%{self.fixture_run_id}%"
        with connect(self.guardrails.env["DATABASE_URL"]) as conn:
            row = conn.execute(
                """
                select a.id
                from ads a
                join businesses b on b.id = a.business_id
                where b.business_name ilike %s
                  and b.verification_status = 'approved'
                  and a.status = 'active'
                  and a.expires_at > now()
                order by a.created_at, a.id
                limit 1
                """,
                (like,),
            ).fetchone()
        return str(row[0]) if row else None

    def endpoints(self, *, include_marketplace: bool = True) -> list[ProbeEndpoint]:
        endpoints = [
            ProbeEndpoint("health", "GET", "/api/v1/health", "light"),
            ProbeEndpoint("ready", "GET", "/api/v1/ready", "light"),
            ProbeEndpoint("version", "GET", "/api/v1/version", "light"),
        ]
        if include_marketplace:
            endpoints.extend(
                [
                    ProbeEndpoint("marketplace_home", "GET", search_path(limit=50), "marketplace"),
                    ProbeEndpoint("marketplace_filtered_search", "GET", search_path(amount_slot=0, limit=20), "marketplace"),
                ]
            )
            ad_id = self.fixture_ad_id()
            if ad_id:
                endpoints.append(ProbeEndpoint("marketplace_ad_detail", "GET", f"/api/v1/ads/{ad_id}", "marketplace"))
        return endpoints

    def headers(self, *, endpoint: ProbeEndpoint, index: int) -> dict[str, str]:
        slug = f"{self.run_id}_{endpoint.label}_{index:05d}"
        headers = {
            "X-Request-Id": f"req_{slug}",
            "X-Correlation-Id": f"corr_{self.run_id}",
            "X-NODO-Operation-Id": f"op_{slug}",
            "X-NODO-Surface": "client_mini_app" if endpoint.group == "marketplace" else "admin_web",
        }
        if endpoint.group == "marketplace":
            headers["Authorization"] = f"Bearer {self.marketplace_access_token()}"
        return headers

    def marketplace_access_token(self) -> str:
        if self._marketplace_login is None:
            if self._smoke is None:
                self._smoke = LocalSmoke(env_file=self.env_file, run_id=self.run_id)
            self._marketplace_login = self._smoke.fixture_login(
                self._smoke.synthetic_telegram_id(33_000),
                "ttfb_probe_remitter",
                role="remitter",
            )
            self._marketplace_auth_created = True
        token = self._marketplace_login.get("access_token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("marketplace auth fixture did not produce an access token")
        return token

    async def send_one(self, client: httpx.AsyncClient, recorder: ProbeRecorder, endpoint: ProbeEndpoint, index: int) -> None:
        headers = self.headers(endpoint=endpoint, index=index)
        started = time.perf_counter()
        response: httpx.Response | None = None
        try:
            request = client.build_request(endpoint.method, endpoint.path, headers=headers)
            response = await client.send(request, stream=True)
            headers_received = time.perf_counter()
            read_started = time.perf_counter()
            await response.aread()
            read_finished = time.perf_counter()
        except httpx.RequestError as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            recorder.add_error(endpoint=endpoint, index=index, exc=exc, elapsed_ms=elapsed_ms, headers=headers)
        else:
            recorder.add_response(
                endpoint=endpoint,
                index=index,
                status=response.status_code,
                client_total_ms=(read_finished - started) * 1000,
                response=response,
                ttfb_or_headers_ms=(headers_received - started) * 1000,
                response_read_ms=(read_finished - read_started) * 1000,
            )
        finally:
            if response is not None and not response.is_closed:
                await response.aclose()

    async def run_load(
        self,
        *,
        endpoint: ProbeEndpoint,
        requests: int,
        concurrency: int,
        max_connections: int,
        keepalive: str = "on",
        http2: bool = False,
    ) -> dict[str, Any]:
        recorder = ProbeRecorder(sample_limit=self.sample_limit)
        keepalive_connections = max_connections if keepalive == "on" else 0
        limits = httpx.Limits(max_connections=max_connections, max_keepalive_connections=keepalive_connections)
        semaphore = asyncio.Semaphore(concurrency)
        started = time.perf_counter()
        async with httpx.AsyncClient(
            base_url=self.remote_base_url,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            limits=limits,
            http2=http2,
        ) as client:

            async def one(index: int) -> None:
                async with semaphore:
                    await self.send_one(client, recorder, endpoint, index)

            await asyncio.gather(*(one(index) for index in range(requests)))
        summary = recorder.summary()
        return {
            "endpoint": endpoint.label,
            "path": endpoint.path,
            "group": endpoint.group,
            "requests": requests,
            "concurrency": concurrency,
            "max_connections": max_connections,
            "keepalive": keepalive,
            "http2": http2,
            "duration_ms": round((time.perf_counter() - started) * 1000, 4),
            "summary": summary["overall"],
            "request_error_summary": summary["request_error_summary"],
            "samples": summary["samples"],
            "request_error_samples": summary["request_error_samples"],
        }

    def run_preflight(self) -> dict[str, Any]:
        endpoints = self.endpoints(include_marketplace=False)

        async def run() -> list[dict[str, Any]]:
            return [
                await self.run_load(endpoint=endpoint, requests=1, concurrency=1, max_connections=1)
                for endpoint in endpoints
            ]

        rows = asyncio.run(run())
        return self._payload("preflight", {"rows": rows, "exit_code": 0 if all(row["summary"]["status_counts"].get("200") == 1 for row in rows) else 1})

    def run_endpoint_isolation(self) -> dict[str, Any]:
        endpoints = self.endpoints(include_marketplace=True)

        async def run() -> list[dict[str, Any]]:
            rows = []
            for endpoint in endpoints:
                requests = DEFAULT_LIGHT_REQUESTS if endpoint.group == "light" else DEFAULT_MARKETPLACE_REQUESTS
                rows.append(await self.run_load(endpoint=endpoint, requests=requests, concurrency=100, max_connections=100))
            return rows

        rows = asyncio.run(run())
        light_slow = [
            row["endpoint"]
            for row in rows
            if row["group"] == "light" and row["summary"]["ttfb_or_headers"]["p95_ms"] > 1000
        ]
        marketplace_slow = [
            row["endpoint"]
            for row in rows
            if row["group"] == "marketplace" and row["summary"]["ttfb_or_headers"]["p95_ms"] > 1000
        ]
        classification = "HEALTH_READY_TTFB_QUEUE" if light_slow else "MARKETPLACE_ONLY_TTFB_QUEUE" if marketplace_slow else "INSUFFICIENT_EVIDENCE"
        return self._payload("endpoint_isolation", {"rows": rows, "classification": classification, "exit_code": 0})

    def run_concurrency_ramp(self) -> dict[str, Any]:
        plans = [(1, 50), (5, 100), (10, 200), (25, 300), (50, 500), (100, 500)]
        endpoints = [ProbeEndpoint("health", "GET", "/api/v1/health", "light"), ProbeEndpoint("marketplace_home", "GET", search_path(limit=50), "marketplace")]

        async def run() -> list[dict[str, Any]]:
            rows = []
            for endpoint in endpoints:
                for concurrency, requests in plans:
                    rows.append(
                        await self.run_load(
                            endpoint=endpoint,
                            requests=requests,
                            concurrency=concurrency,
                            max_connections=100,
                        )
                    )
            return rows

        rows = asyncio.run(run())
        knees = {
            endpoint.label: detect_knee([row for row in rows if row["endpoint"] == endpoint.label])
            for endpoint in endpoints
        }
        return self._payload("concurrency_ramp", {"rows": rows, "knees": knees, "exit_code": 0})

    def run_pool_isolation(self) -> dict[str, Any]:
        endpoints = [ProbeEndpoint("health", "GET", "/api/v1/health", "light"), ProbeEndpoint("marketplace_home", "GET", search_path(limit=50), "marketplace")]

        async def run() -> list[dict[str, Any]]:
            rows = []
            for endpoint in endpoints:
                for max_connections in (10, 100, 200):
                    rows.append(
                        await self.run_load(
                            endpoint=endpoint,
                            requests=500,
                            concurrency=100,
                            max_connections=max_connections,
                        )
                    )
            return rows

        rows = asyncio.run(run())
        classifications = {
            endpoint.label: classify_pool_isolation([row for row in rows if row["endpoint"] == endpoint.label])
            for endpoint in endpoints
        }
        return self._payload("pool_isolation", {"rows": rows, "classification": classifications, "exit_code": 0})

    def run_keepalive_isolation(self) -> dict[str, Any]:
        endpoints = [ProbeEndpoint("health", "GET", "/api/v1/health", "light"), ProbeEndpoint("marketplace_home", "GET", search_path(limit=50), "marketplace")]

        async def run() -> list[dict[str, Any]]:
            rows = []
            for endpoint in endpoints:
                for keepalive in ("on", "off"):
                    rows.append(
                        await self.run_load(
                            endpoint=endpoint,
                            requests=500,
                            concurrency=100,
                            max_connections=100,
                            keepalive=keepalive,
                        )
                    )
            return rows

        rows = asyncio.run(run())
        classifications = {
            endpoint.label: classify_keepalive([row for row in rows if row["endpoint"] == endpoint.label])
            for endpoint in endpoints
        }
        return self._payload("keepalive_isolation", {"rows": rows, "classification": classifications, "exit_code": 0})

    def run_http2_probe(self) -> dict[str, Any]:
        endpoints = [ProbeEndpoint("health", "GET", "/api/v1/health", "light"), ProbeEndpoint("marketplace_home", "GET", search_path(limit=50), "marketplace")]

        async def run() -> list[dict[str, Any]]:
            rows = []
            for endpoint in endpoints:
                for http2 in (False, True):
                    rows.append(
                        await self.run_load(
                            endpoint=endpoint,
                            requests=300,
                            concurrency=100,
                            max_connections=100,
                            http2=http2,
                        )
                    )
            return rows

        try:
            rows = asyncio.run(run())
        except ImportError as exc:
            return self._payload(
                "http2_probe",
                {"status": "HTTP2_PROBE_UNAVAILABLE", "reason": redact_exception_message(str(exc)), "rows": [], "exit_code": 0},
            )
        classifications: dict[str, str] = {}
        for endpoint in endpoints:
            endpoint_rows = [row for row in rows if row["endpoint"] == endpoint.label]
            by_mode = {bool(row["http2"]): row for row in endpoint_rows}
            if True in by_mode and False in by_mode:
                h1 = float(by_mode[False]["summary"]["ttfb_or_headers"]["p95_ms"])
                h2 = float(by_mode[True]["summary"]["ttfb_or_headers"]["p95_ms"])
                classifications[endpoint.label] = "HTTP2_MULTIPLEXING_HELPFUL" if h2 < h1 * 0.7 else "INSUFFICIENT_EVIDENCE"
        return self._payload("http2_probe", {"status": "completed", "rows": rows, "classification": classifications, "exit_code": 0})

    def run_sequential_probe(self) -> dict[str, Any]:
        endpoints = self.endpoints(include_marketplace=True)
        endpoints = [endpoint for endpoint in endpoints if endpoint.label in {"health", "ready", "marketplace_home", "marketplace_ad_detail"}]

        async def run() -> list[dict[str, Any]]:
            rows = []
            for endpoint in endpoints:
                rows.append(await self.run_load(endpoint=endpoint, requests=20, concurrency=1, max_connections=1))
            return rows

        rows = asyncio.run(run())
        has_error = any(row["summary"]["error_counts"] for row in rows)
        classification = "EXTERNAL_INSTABILITY_SEQUENTIAL" if has_error else "INSUFFICIENT_EVIDENCE"
        return self._payload("sequential_probe", {"rows": rows, "classification": classification, "exit_code": 0})

    def run_curl_phase_probe(self, *, curl_format: Path) -> dict[str, Any]:
        curl_path = shutil.which("curl")
        if not curl_path:
            return self._payload(
                "curl_phase_probe",
                {"status": "CURL_COMMAND_NOT_AVAILABLE", "rows": [], "exit_code": 0},
            )
        endpoints = self.endpoints(include_marketplace=True)
        endpoints = [endpoint for endpoint in endpoints if endpoint.label in {"health", "ready", "marketplace_home", "marketplace_ad_detail"}]
        rows = []
        for endpoint in endpoints:
            samples: list[dict[str, Any]] = []
            for index in range(20):
                curl_headers: list[str] = []
                for key, value in self.headers(endpoint=endpoint, index=index).items():
                    curl_headers.extend(["-H", f"{key}: {value}"])
                completed = subprocess.run(
                    [
                        curl_path,
                        "-sS",
                        "-o",
                        "NUL",
                        "--max-time",
                        str(int(DEFAULT_TIMEOUT_SECONDS)),
                        *curl_headers,
                        "-w",
                        f"@{curl_format}",
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
            phase_names = ("dns_ms", "tcp_connect_ms", "tls_ms", "pretransfer_ms", "server_wait_ms", "download_ms", "total_ms")
            phases = {
                name: percentiles([float(sample["phases"][name]) for sample in samples if isinstance(sample.get("phases"), dict)])
                for name in phase_names
            }
            status_counts = Counter(str(sample.get("http_code", sample.get("status", "unknown"))) for sample in samples)
            row = {
                "endpoint": endpoint.label,
                "path": endpoint.path,
                "samples": len(samples),
                "status_counts": dict(status_counts),
                "phases": phases,
            }
            row["classification"] = classify_curl_summary(row)
            rows.append(row)
        classifications = {row["endpoint"]: row["classification"] for row in rows}
        return self._payload("curl_phase_probe", {"status": "completed", "rows": rows, "classification": classifications, "exit_code": 0})

    def _payload(self, phase: str, data: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "slice": "slice_33A6_ttfb_queue_source_isolation",
            "phase": phase,
            "run_id": self.run_id,
            "target": self.remote_base_url,
            "fixture_run_id": self.fixture_run_id,
            "guardrails": {
                "checked": True,
                "app_env": self.guardrails.env.get("APP_ENV"),
                "environment_kind": self.guardrails.env.get("NODO_ENVIRONMENT_KIND"),
                "staging_validation": self.guardrails.env.get("NODO_STAGING_VALIDATION"),
            },
            "cleanup": {
                "fixture_cleanup_required": self.fixture_run_id is not None,
                "fixture_run_id": self.fixture_run_id,
                "diagnostic_cleanup_required": self._marketplace_auth_created,
                "diagnostic_run_id": self.run_id if self._marketplace_auth_created else None,
            },
            **data,
        }
        markers = output_contains_sensitive_marker(payload)
        payload["sensitive_marker_scan"] = {
            "status": "failed" if markers else "passed",
            "markers": markers,
        }
        if markers:
            payload["exit_code"] = 1
        return payload


def write_curl_format(path: Path) -> None:
    path.write_text(
        (
            "{"
            '"http_code":%{http_code},'
            '"time_namelookup":%{time_namelookup},'
            '"time_connect":%{time_connect},'
            '"time_appconnect":%{time_appconnect},'
            '"time_pretransfer":%{time_pretransfer},'
            '"time_starttransfer":%{time_starttransfer},'
            '"time_total":%{time_total},'
            '"size_download":%{size_download}'
            "}\\n"
        ),
        encoding="ascii",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--remote-base-url", default=None)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--fixture-run-id", default=None)
    parser.add_argument("--mode", required=True, choices=[
        "preflight",
        "endpoint-isolation",
        "concurrency-ramp",
        "pool-isolation",
        "keepalive-isolation",
        "http2-probe",
        "curl-phase-probe",
        "sequential-probe",
    ])
    parser.add_argument("--curl-format", default="scripts/curl-format-ttfb.txt")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    probe = TTFBQueueProbe(
        env_file=Path(args.env_file),
        remote_base_url=args.remote_base_url,
        run_id=args.run_id,
        fixture_run_id=args.fixture_run_id,
        output=output,
    )
    if args.mode == "preflight":
        payload = probe.run_preflight()
    elif args.mode == "endpoint-isolation":
        payload = probe.run_endpoint_isolation()
    elif args.mode == "concurrency-ramp":
        payload = probe.run_concurrency_ramp()
    elif args.mode == "pool-isolation":
        payload = probe.run_pool_isolation()
    elif args.mode == "keepalive-isolation":
        payload = probe.run_keepalive_isolation()
    elif args.mode == "http2-probe":
        payload = probe.run_http2_probe()
    elif args.mode == "curl-phase-probe":
        curl_format = Path(args.curl_format)
        if not curl_format.exists():
            write_curl_format(curl_format)
        payload = probe.run_curl_phase_probe(curl_format=curl_format)
    else:
        payload = probe.run_sequential_probe()

    write_json(output, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return int(payload.get("exit_code", 0))


if __name__ == "__main__":
    raise SystemExit(main())
