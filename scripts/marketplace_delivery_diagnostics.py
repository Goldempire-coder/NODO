from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from capacity_real import (
    RealCapacityHarness,
    classify_request_error,
    parse_process_time_ms,
    parse_server_timing,
    redact_exception_message,
)
from local_hardening_common import DEFAULT_ENV_FILE, write_json
from app.shared.db.connection import connect


PROFILE_SAMPLE_LIMIT = 50
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


def schedule_flow_offsets(
    *,
    flows: int,
    traffic_shape: str,
    ramp_duration_seconds: int | None = None,
    target_rps: float | None = None,
    steps_per_flow: int = 4,
) -> list[float]:
    if flows <= 0:
        return []
    if traffic_shape == "burst":
        return [0.0 for _ in range(flows)]
    if traffic_shape == "ramp":
        duration = float(ramp_duration_seconds or 0)
        if flows == 1:
            return [0.0]
        return [round(index * duration / (flows - 1), 6) for index in range(flows)]
    if traffic_shape == "steady":
        if not target_rps or target_rps <= 0:
            raise ValueError("steady traffic requires --target-rps")
        flow_rate = max(target_rps / steps_per_flow, 0.0001)
        return [round(index / flow_rate, 6) for index in range(flows)]
    raise ValueError("traffic_shape must be burst, ramp, or steady")


def response_profile(body: dict[str, Any]) -> dict[str, Any] | None:
    data = body.get("data")
    if isinstance(data, dict) and isinstance(data.get("_profile"), dict):
        return data["_profile"]
    return None


@dataclass(frozen=True)
class FlowRequest:
    synthetic_user_id: str
    screen: str
    flow_step: str
    method: str
    path: str
    step_number: int = 0


class MarketplaceDeliveryRecorder:
    def __init__(self, *, sample_limit: int = PROFILE_SAMPLE_LIMIT) -> None:
        self.sample_limit = sample_limit
        self.records: list[dict[str, Any]] = []
        self.samples: list[dict[str, Any]] = []
        self.request_errors: list[dict[str, Any]] = []
        self.profile_stage_values: dict[str, list[float]] = defaultdict(list)
        self.cache_hits: Counter[str] = Counter()
        self.auth_modes: Counter[str] = Counter()

    def add_response(
        self,
        *,
        request: FlowRequest,
        index: int,
        status: int,
        client_total_ms: float,
        response: httpx.Response | None,
        ttfb_or_headers_ms: float | None = None,
        response_read_ms: float | None = None,
        queue_wait_ms: float | None = None,
        request_ready_at: float | None = None,
        request_start_monotonic: float | None = None,
        response_started_monotonic: float | None = None,
        request_end_monotonic: float | None = None,
        retry_attempt: int = 0,
        recovered_by_retry: bool = False,
        error_type: str | None = None,
    ) -> None:
        headers = response.headers if response is not None else {}
        server_timing = parse_server_timing(headers.get("Server-Timing"))
        backend_process_ms = parse_process_time_ms(headers.get("X-NODO-Process-Time-Ms")) or server_timing.get("app")
        response_bytes = len(response.content) if response is not None else 0
        profile = None
        if response is not None:
            try:
                body = response.json()
            except ValueError:
                body = {}
            profile = response_profile(body if isinstance(body, dict) else {})
            self._record_profile(profile)
        record = {
            "scenario": "marketplace_delivery_diagnostics",
            "synthetic_user_id": request.synthetic_user_id,
            "screen": request.screen,
            "step_number": request.step_number,
            "flow_step": request.flow_step,
            "endpoint": request.path.split("?", 1)[0],
            "method": request.method,
            "status": status,
            "client_total_ms": round(client_total_ms, 4),
            "backend_process_ms": backend_process_ms,
            "external_gap_ms": external_gap_ms(client_total_ms, backend_process_ms),
            "ttfb_or_headers_ms": round(ttfb_or_headers_ms, 4) if isinstance(ttfb_or_headers_ms, int | float) else None,
            "response_read_ms": round(response_read_ms, 4) if isinstance(response_read_ms, int | float) else None,
            "response_bytes": response_bytes,
            "queue_wait_ms": round(queue_wait_ms, 4) if isinstance(queue_wait_ms, int | float) else None,
            "request_ready_at": round(request_ready_at, 6) if isinstance(request_ready_at, int | float) else None,
            "request_started_at": round(request_start_monotonic, 6) if isinstance(request_start_monotonic, int | float) else None,
            "request_start_monotonic": round(request_start_monotonic, 6) if isinstance(request_start_monotonic, int | float) else None,
            "response_started": response is not None,
            "response_started_monotonic": round(response_started_monotonic, 6)
            if isinstance(response_started_monotonic, int | float)
            else None,
            "response_finished": response is not None,
            "request_end_monotonic": round(request_end_monotonic, 6) if isinstance(request_end_monotonic, int | float) else None,
            "request_id": headers.get("X-Request-Id"),
            "correlation_id": headers.get("X-Correlation-Id"),
            "operation_id": headers.get("X-NODO-Operation-Id"),
            "retry_attempt": retry_attempt,
            "recovered_by_retry": recovered_by_retry,
            "server_timing": server_timing,
            "railway_edge": headers.get("x-railway-edge"),
            "profile_present": profile is not None,
            "error_type": error_type,
        }
        self.records.append(record)
        if len(self.samples) < self.sample_limit:
            self.samples.append({"index": index, **record})

    def add_request_error(
        self,
        *,
        request: FlowRequest,
        index: int,
        client_total_ms: float,
        exc: httpx.RequestError,
        request_id: str,
        correlation_id: str,
        operation_id: str,
        queue_wait_ms: float | None = None,
        request_ready_at: float | None = None,
        request_start_monotonic: float | None = None,
        request_end_monotonic: float | None = None,
        retry_attempt: int = 0,
        recovered_by_retry: bool = False,
        record_as_response: bool = True,
    ) -> None:
        classification = classify_request_error(exc)
        self.request_errors.append(
            {
                "index": index,
                "synthetic_user_id": request.synthetic_user_id,
                "screen": request.screen,
                "step_number": request.step_number,
                "flow_step": request.flow_step,
                "endpoint": request.path.split("?", 1)[0],
                "method": request.method,
                "status": 599,
                "client_total_ms": round(client_total_ms, 4),
                "queue_wait_ms": round(queue_wait_ms, 4) if isinstance(queue_wait_ms, int | float) else None,
                "request_ready_at": round(request_ready_at, 6) if isinstance(request_ready_at, int | float) else None,
                "request_started_at": round(request_start_monotonic, 6) if isinstance(request_start_monotonic, int | float) else None,
                "request_start_monotonic": round(request_start_monotonic, 6)
                if isinstance(request_start_monotonic, int | float)
                else None,
                "request_end_monotonic": round(request_end_monotonic, 6) if isinstance(request_end_monotonic, int | float) else None,
                "request_id": request_id,
                "correlation_id": correlation_id,
                "operation_id": operation_id,
                "retry_attempt": retry_attempt,
                "recovered_by_retry": recovered_by_retry,
                "exception_class": type(exc).__name__,
                "exception_message_redacted": redact_exception_message(str(exc)),
                "classification": classification,
                "response_started": False,
            }
        )
        if not record_as_response:
            return
        self.add_response(
            request=request,
            index=index,
            status=599,
            client_total_ms=client_total_ms,
            response=None,
            queue_wait_ms=queue_wait_ms,
            request_ready_at=request_ready_at,
            request_start_monotonic=request_start_monotonic,
            request_end_monotonic=request_end_monotonic,
            retry_attempt=retry_attempt,
            recovered_by_retry=recovered_by_retry,
            error_type=classification,
        )

    def _record_profile(self, profile: dict[str, Any] | None) -> None:
        if not profile:
            return
        dependency = profile.get("dependency")
        if isinstance(dependency, dict):
            auth = dependency.get("auth")
            if isinstance(auth, dict):
                mode = auth.get("mode")
                if isinstance(mode, str):
                    self.auth_modes[mode] += 1
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
        if isinstance(name, str) and isinstance(elapsed, int | float):
            self.profile_stage_values[name].append(float(elapsed))
        metadata = stage.get("metadata")
        if name == "cache:hit" and isinstance(metadata, dict):
            hit_type = metadata.get("hit_type")
            if isinstance(hit_type, str):
                self.cache_hits[hit_type] += 1

    @staticmethod
    def _transport_error_summary(errors: list[dict[str, Any]]) -> dict[str, Any]:
        raw = len(errors)
        recovered = sum(1 for error in errors if error.get("recovered_by_retry"))
        return {
            "raw_transport_errors": raw,
            "recovered_transport_errors": recovered,
            "unrecovered_transport_errors": raw - recovered,
            "by_classification": dict(Counter(str(error["classification"]) for error in errors)),
        }

    def _summary_for(self, records: list[dict[str, Any]], errors: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        client_values = [float(record["client_total_ms"]) for record in records]
        backend_values = [float(record["backend_process_ms"]) for record in records if isinstance(record.get("backend_process_ms"), int | float)]
        gap_values = [float(record["external_gap_ms"]) for record in records if isinstance(record.get("external_gap_ms"), int | float)]
        ttfb_values = [float(record["ttfb_or_headers_ms"]) for record in records if isinstance(record.get("ttfb_or_headers_ms"), int | float)]
        read_values = [float(record["response_read_ms"]) for record in records if isinstance(record.get("response_read_ms"), int | float)]
        queue_wait_values = [float(record["queue_wait_ms"]) for record in records if isinstance(record.get("queue_wait_ms"), int | float)]
        response_values = [float(record["response_bytes"]) for record in records]
        users = {record["synthetic_user_id"] for record in records}
        status_counts = Counter(str(record["status"]) for record in records)
        error_counts = Counter(str(record["error_type"]) for record in records if record.get("error_type"))
        transport_errors = self._transport_error_summary(errors or [])
        return {
            "requests": len(records),
            "unique_synthetic_users": len(users),
            "request_count_per_synthetic_user": round(len(records) / len(users), 4) if users else 0.0,
            "transport_errors": transport_errors,
            "queue_wait": percentiles(queue_wait_values),
            "client": percentiles(client_values),
            "backend_process": percentiles(backend_values),
            "external_gap": percentiles(gap_values),
            "ttfb_or_headers": percentiles(ttfb_values),
            "response_read": percentiles(read_values),
            "response_bytes": percentiles(response_values),
            "response_kb_p95": round(percentiles(response_values)["p95_ms"] / 1024, 4),
            "status_counts": dict(status_counts),
            "error_counts": dict(error_counts),
        }

    def grouped_summary(self, key: str) -> dict[str, Any]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in self.records:
            grouped[str(record.get(key) or "unknown")].append(record)
        error_grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for error in self.request_errors:
            error_grouped[str(error.get(key) or "unknown")].append(error)
        return {name: self._summary_for(items, error_grouped.get(name, [])) for name, items in sorted(grouped.items())}

    def summary(self) -> dict[str, Any]:
        profile_stage_summary = {stage: percentiles(values) for stage, values in sorted(self.profile_stage_values.items())}
        total_cache_hits = sum(self.cache_hits.values())
        return {
            "overall": self._summary_for(self.records, self.request_errors),
            "by_screen": self.grouped_summary("screen"),
            "by_flow_step": self.grouped_summary("flow_step"),
            "by_endpoint": self.grouped_summary("endpoint"),
            "profile": {
                "captured_profiles": sum(1 for record in self.records if record.get("profile_present")),
                "stage_latency": profile_stage_summary,
                "cache_hit_counts": dict(self.cache_hits),
                "cache_hit_ratio": round((self.cache_hits.get("local", 0) + self.cache_hits.get("shared", 0)) / total_cache_hits, 6) if total_cache_hits else 0.0,
                "auth_mode_counts": dict(self.auth_modes),
                "db_acquire_p95_ms": profile_stage_summary.get("db:acquire", {}).get("p95_ms", 0.0),
                "db_query_p95_ms": profile_stage_summary.get("db:query:list_marketplace_ads_with_businesses", {}).get("p95_ms", 0.0),
                "cache_shared_get_p95_ms": profile_stage_summary.get("cache:shared_get", {}).get("p95_ms", 0.0),
            },
            "request_error_summary": {
                "total": len(self.request_errors),
                "raw_transport_errors": len(self.request_errors),
                "recovered_transport_errors": sum(1 for error in self.request_errors if error.get("recovered_by_retry")),
                "unrecovered_transport_errors": sum(1 for error in self.request_errors if not error.get("recovered_by_retry")),
                "by_classification": dict(Counter(error["classification"] for error in self.request_errors)),
                "by_endpoint": dict(Counter(error["endpoint"] for error in self.request_errors)),
                "by_flow_step": dict(Counter(error["flow_step"] for error in self.request_errors)),
            },
            "phase_timing_limitations": [
                "httpx public instrumentation measures total time, time to response headers, and body read time.",
                "pool_wait_ms, connect_ms, tls_ms, and request_send_ms are not available without lower-level transport instrumentation.",
            ],
        }


class MarketplaceDeliveryDiagnostics:
    def __init__(
        self,
        *,
        env_file: Path,
        remote_base_url: str,
        run_id: str,
        businesses: int,
        ads_per_business: int,
        synthetic_users: int,
        requests: int,
        concurrency: int,
        max_connections: int | None,
        profile_marketplace: bool,
        output: Path,
        profile_detail_limit: int,
        fixture_run_id: str | None = None,
        cache_mode: str = "cold",
        traffic_shape: str = "burst",
        ramp_duration_seconds: int | None = None,
        target_rps: float | None = None,
        per_step_concurrency_cap: int | None = None,
        step_jitter_ms: int = 0,
        flow_mode: str = "full",
        retry_transport_once: bool = False,
        retry_backoff_min_ms: int = 100,
        retry_backoff_max_ms: int = 250,
    ) -> None:
        if requests < 1:
            raise ValueError("requests must be >= 1")
        if concurrency < 1:
            raise ValueError("concurrency must be >= 1")
        if cache_mode not in {"cold", "warm"}:
            raise ValueError("cache_mode must be cold or warm")
        if traffic_shape not in {"burst", "ramp", "steady"}:
            raise ValueError("traffic_shape must be burst, ramp, or steady")
        if traffic_shape == "steady" and (target_rps is None or target_rps <= 0):
            raise ValueError("steady traffic requires target_rps")
        if per_step_concurrency_cap is not None and per_step_concurrency_cap < 1:
            raise ValueError("per_step_concurrency_cap must be >= 1")
        if step_jitter_ms < 0:
            raise ValueError("step_jitter_ms must be >= 0")
        if flow_mode not in {"full", "filtered_search_only"}:
            raise ValueError("flow_mode must be full or filtered_search_only")
        if retry_backoff_min_ms < 0 or retry_backoff_max_ms < retry_backoff_min_ms:
            raise ValueError("retry backoff bounds are invalid")
        self.env_file = env_file
        self.remote_base_url = remote_base_url.rstrip("/")
        self.run_id = run_id
        self.businesses = businesses
        self.ads_per_business = ads_per_business
        self.synthetic_users = synthetic_users
        self.requests = requests
        self.concurrency = concurrency
        self.max_connections = max_connections or max(20, concurrency)
        self.profile_marketplace = profile_marketplace
        self.output = output
        self.profile_detail_limit = profile_detail_limit
        self.fixture_run_id = fixture_run_id
        self.cache_mode = cache_mode
        self.flow_mode = flow_mode
        self.steps_per_user = 1 if flow_mode == "filtered_search_only" else 4
        self.synthetic_users_requested = synthetic_users
        self.synthetic_users_used = max(synthetic_users, math.ceil(requests / self.steps_per_user))
        self.request_consumption_mode = "auto_expand_users_to_target_requests"
        self.traffic_shape = traffic_shape
        self.ramp_duration_seconds = ramp_duration_seconds
        self.target_rps = target_rps
        self.per_step_concurrency_cap = per_step_concurrency_cap
        self.step_jitter_ms = step_jitter_ms
        self.retry_transport_once = retry_transport_once
        self.retry_backoff_min_ms = retry_backoff_min_ms
        self.retry_backoff_max_ms = retry_backoff_max_ms
        self.prewarm_result: dict[str, Any] = {
            "enabled": cache_mode == "warm",
            "prewarm_requests": 0,
            "prewarm_status_counts": {},
            "prewarm_duration_ms": 0.0,
            "prewarm_errors": [],
        }
        self.recorder = MarketplaceDeliveryRecorder(sample_limit=profile_detail_limit)
        self.harness = RealCapacityHarness(
            env_file=env_file,
            run_id=run_id,
            businesses=businesses,
            ads_per_business=ads_per_business,
            remitters=self.synthetic_users_used,
            marketplace_reads=0,
            order_creates=0,
            same_ad_race_requests=0,
            payment_confirms=0,
            marketplace_concurrency=concurrency,
            remote_base_url=remote_base_url,
            fixture_mode="db_seed_api_remote",
            profile_marketplace=profile_marketplace,
            profile_detail_limit=profile_detail_limit,
            auth_mode="fresh-claims",
            max_connections=self.max_connections,
            fixture_setup_mode="db_direct_ads",
        )

    def _load_existing_fixture(self) -> dict[str, Any]:
        fixture_run_id = self.fixture_run_id or self.run_id
        like = f"%{fixture_run_id}%"
        with connect(self.harness.smoke.db_url) as conn:
            business_rows = conn.execute(
                """
                select id
                from businesses
                where business_name ilike %s
                  and verification_status = 'approved'
                order by created_at, id
                """,
                (like,),
            ).fetchall()
            ad_rows = conn.execute(
                """
                select a.id, a.business_id
                from ads a
                join businesses b on b.id = a.business_id
                join business_payment_methods pm on pm.id = a.payment_method_id
                where b.business_name ilike %s
                  and b.verification_status = 'approved'
                  and a.status = 'active'
                  and a.expires_at > now()
                  and pm.active = true
                  and pm.verified_status = 'approved'
                order by a.created_at, a.id
                """,
                (like,),
            ).fetchall()
        if len(business_rows) < self.businesses or len(ad_rows) < self.businesses * self.ads_per_business:
            raise RuntimeError(
                "fixture_run_id does not contain enough approved businesses/active ads "
                f"(businesses={len(business_rows)}, ads={len(ad_rows)})"
            )
        remitters = [
            self.harness.smoke.fixture_login(
                self.harness.smoke.synthetic_telegram_id(20_000 + index),
                f"delivery_remitter_{index:04d}",
                role="remitter",
            )
            for index in range(self.synthetic_users_used)
        ]
        return {
            "businesses": [{"business_id": str(row[0])} for row in business_rows[: self.businesses]],
            "ads": [{"id": str(row[0]), "business_id": str(row[1])} for row in ad_rows[: self.businesses * self.ads_per_business]],
            "payment_ads": [],
            "remitters": remitters,
        }

    def _headers(self, *, index: int, token: str, flow_step: str) -> dict[str, str]:
        slug = f"{self.run_id}_{flow_step}_{index:05d}"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Request-Id": f"req_{slug}",
            "X-Correlation-Id": f"corr_{self.run_id}",
            "X-NODO-Operation-Id": f"op_{slug}",
            "X-NODO-Surface": "client_mini_app",
        }
        if self.profile_marketplace:
            headers["X-NODO-Profile"] = "1"
        return headers

    @staticmethod
    def _search_path(*, amount_slot: int | None = None, cursor: str | None = None, limit: int = 50) -> str:
        params: dict[str, str] = {"delivery_method": "pago_movil_ve", "limit": str(limit)}
        if amount_slot is None:
            params["sort"] = "trust"
        else:
            params.update(
                {
                    "amount_usd": f"{20 + amount_slot * 100}.00",
                    "payment_method": "zelle",
                }
            )
        if cursor:
            params["cursor"] = cursor
        return f"/api/v1/ads/search?{urlencode(params)}"

    @staticmethod
    def _first_ad_id(response: httpx.Response | None, fallback_ad_id: str) -> str:
        if response is None:
            return fallback_ad_id
        try:
            body = response.json()
        except ValueError:
            return fallback_ad_id
        data = body.get("data") if isinstance(body, dict) else None
        items = data.get("items") if isinstance(data, dict) else None
        if isinstance(items, list) and items:
            first = items[0]
            if isinstance(first, dict) and isinstance(first.get("id"), str):
                return first["id"]
        return fallback_ad_id

    @staticmethod
    def _next_cursor(response: httpx.Response | None) -> str | None:
        if response is None:
            return None
        try:
            body = response.json()
        except ValueError:
            return None
        data = body.get("data") if isinstance(body, dict) else None
        cursor = data.get("next_cursor") if isinstance(data, dict) else None
        return cursor if isinstance(cursor, str) and cursor else None

    async def _send(
        self,
        client: httpx.AsyncClient,
        request: FlowRequest,
        *,
        index: int,
        token: str,
        request_ready_at: float | None = None,
        retry_attempt: int = 0,
        recovered_by_retry: bool = False,
    ) -> httpx.Response | None:
        headers = self._headers(index=index, token=token, flow_step=request.flow_step)
        started = time.perf_counter()
        queue_wait_ms = ((started - request_ready_at) * 1000) if isinstance(request_ready_at, int | float) else None
        response: httpx.Response | None = None
        try:
            outbound = client.build_request(request.method, request.path, headers=headers)
            response = await client.send(outbound, stream=True)
            headers_received = time.perf_counter()
            read_started = time.perf_counter()
            await response.aread()
            read_finished = time.perf_counter()
        except httpx.RequestError as exc:
            finished = time.perf_counter()
            elapsed_ms = (finished - started) * 1000
            self.recorder.add_request_error(
                request=request,
                index=index,
                client_total_ms=elapsed_ms,
                exc=exc,
                request_id=headers["X-Request-Id"],
                correlation_id=headers["X-Correlation-Id"],
                operation_id=headers["X-NODO-Operation-Id"],
                queue_wait_ms=queue_wait_ms,
                request_ready_at=request_ready_at,
                request_start_monotonic=started,
                request_end_monotonic=finished,
                retry_attempt=retry_attempt,
                recovered_by_retry=False,
                record_as_response=not (
                    self.retry_transport_once and retry_attempt == 0 and request.method.upper() == "GET"
                ),
            )
            if self.retry_transport_once and retry_attempt == 0 and request.method.upper() == "GET":
                backoff_ms = random.uniform(self.retry_backoff_min_ms, self.retry_backoff_max_ms)
                await asyncio.sleep(backoff_ms / 1000)
                return await self._send(
                    client,
                    request,
                    index=index,
                    token=token,
                    request_ready_at=time.perf_counter(),
                    retry_attempt=1,
                    recovered_by_retry=True,
                )
            return None
        finally:
            if response is not None and not response.is_closed:
                await response.aclose()
        elapsed_ms = (read_finished - started) * 1000
        self.recorder.add_response(
            request=request,
            index=index,
            status=response.status_code,
            client_total_ms=elapsed_ms,
            response=response,
            ttfb_or_headers_ms=(headers_received - started) * 1000,
            response_read_ms=(read_finished - read_started) * 1000,
            queue_wait_ms=queue_wait_ms,
            request_ready_at=request_ready_at,
            request_start_monotonic=started,
            response_started_monotonic=headers_received,
            request_end_monotonic=read_finished,
            retry_attempt=retry_attempt,
            recovered_by_retry=recovered_by_retry,
        )
        return response

    async def _send_step(
        self,
        *,
        client: httpx.AsyncClient,
        request: FlowRequest,
        index: int,
        token: str,
        step_semaphores: dict[str, asyncio.Semaphore],
    ) -> httpx.Response | None:
        request_ready_at = time.perf_counter()
        semaphore = step_semaphores.get(request.flow_step)
        if semaphore is None:
            return await self._send(client, request, index=index, token=token, request_ready_at=request_ready_at)
        async with semaphore:
            return await self._send(client, request, index=index, token=token, request_ready_at=request_ready_at)

    async def _maybe_step_jitter(self) -> None:
        if self.step_jitter_ms <= 0:
            return
        await asyncio.sleep(random.uniform(0, self.step_jitter_ms) / 1000)

    async def _run_user_flow(
        self,
        *,
        client: httpx.AsyncClient,
        user_index: int,
        token: str,
        fallback_ad_id: str,
        next_index: asyncio.Queue[int],
        step_semaphores: dict[str, asyncio.Semaphore],
    ) -> None:
        synthetic_user_id = f"user_{user_index:05d}"

        async def take_index() -> int | None:
            try:
                return next_index.get_nowait()
            except asyncio.QueueEmpty:
                return None

        index = await take_index()
        if index is None:
            return
        if self.flow_mode == "filtered_search_only":
            filtered_only = FlowRequest(
                synthetic_user_id,
                "marketplace-search",
                "marketplace_filtered_search",
                "GET",
                self._search_path(amount_slot=user_index % self.ads_per_business, limit=20),
                1,
            )
            await self._send_step(client=client, request=filtered_only, index=index, token=token, step_semaphores=step_semaphores)
            return

        home = FlowRequest(synthetic_user_id, "marketplace-list", "marketplace_home", "GET", self._search_path(limit=50), 1)
        home_response = await self._send_step(client=client, request=home, index=index, token=token, step_semaphores=step_semaphores)
        await self._maybe_step_jitter()

        index = await take_index()
        if index is None:
            return
        filtered = FlowRequest(
            synthetic_user_id,
            "marketplace-search",
            "marketplace_filtered_search",
            "GET",
            self._search_path(amount_slot=user_index % self.ads_per_business, limit=20),
            2,
        )
        filtered_response = await self._send_step(client=client, request=filtered, index=index, token=token, step_semaphores=step_semaphores)
        await self._maybe_step_jitter()

        index = await take_index()
        if index is None:
            return
        ad_id = self._first_ad_id(filtered_response or home_response, fallback_ad_id)
        detail = FlowRequest(synthetic_user_id, "marketplace-detail", "marketplace_ad_detail", "GET", f"/api/v1/ads/{ad_id}", 3)
        await self._send_step(client=client, request=detail, index=index, token=token, step_semaphores=step_semaphores)
        await self._maybe_step_jitter()

        index = await take_index()
        if index is None:
            return
        cursor = self._next_cursor(home_response)
        page_path = self._search_path(cursor=cursor, limit=50) if cursor else self._search_path(limit=50)
        page = FlowRequest(synthetic_user_id, "marketplace-list", "marketplace_next_page", "GET", page_path, 4)
        await self._send_step(client=client, request=page, index=index, token=token, step_semaphores=step_semaphores)

    async def _prewarm(self, client: httpx.AsyncClient, *, token: str, fallback_ad_id: str) -> None:
        started = time.perf_counter()
        status_counts: Counter[str] = Counter()
        errors: list[dict[str, str]] = []
        request_count = 0

        async def one(path: str, operation: str) -> httpx.Response | None:
            nonlocal request_count
            request_count += 1
            try:
                response = await client.get(
                    path,
                    headers=self._headers(index=request_count, token=token, flow_step=f"prewarm_{operation}"),
                )
            except httpx.RequestError as exc:
                status_counts["599"] += 1
                errors.append(
                    {
                        "operation": operation,
                        "classification": classify_request_error(exc),
                        "exception_class": type(exc).__name__,
                        "exception_message_redacted": redact_exception_message(str(exc)),
                    }
                )
                return None
            else:
                status_counts[str(response.status_code)] += 1
                return response

        home_response = await one(self._search_path(limit=50), "marketplace_home")
        filtered_response = await one(self._search_path(amount_slot=0, limit=20), "marketplace_filtered_search")
        ad_id = self._first_ad_id(filtered_response or home_response, fallback_ad_id)
        await one(f"/api/v1/ads/{ad_id}", "marketplace_ad_detail")
        cursor = self._next_cursor(home_response)
        if cursor:
            await one(self._search_path(cursor=cursor, limit=50), "marketplace_next_page")

        self.prewarm_result = {
            "enabled": True,
            "prewarm_requests": request_count,
            "prewarm_status_counts": dict(status_counts),
            "prewarm_duration_ms": round((time.perf_counter() - started) * 1000, 4),
            "prewarm_errors": errors,
        }

    async def _run_flows(self, prepared: dict[str, Any]) -> None:
        remitters = self.harness._fresh_fixture_logins(prepared["remitters"])  # noqa: SLF001
        remitters = [self.harness._marketplace_auth_login(login) for login in remitters]  # noqa: SLF001
        ads = prepared["ads"]
        indexes: asyncio.Queue[int] = asyncio.Queue()
        for index in range(self.requests):
            indexes.put_nowait(index)
        limits = httpx.Limits(max_connections=self.max_connections, max_keepalive_connections=self.max_connections)
        semaphore = asyncio.Semaphore(self.concurrency)
        step_semaphores = (
            {
                "marketplace_home": asyncio.Semaphore(self.per_step_concurrency_cap),
                "marketplace_filtered_search": asyncio.Semaphore(self.per_step_concurrency_cap),
                "marketplace_ad_detail": asyncio.Semaphore(self.per_step_concurrency_cap),
                "marketplace_next_page": asyncio.Semaphore(self.per_step_concurrency_cap),
            }
            if self.per_step_concurrency_cap
            else {}
        )
        offsets = schedule_flow_offsets(
            flows=self.synthetic_users_used,
            traffic_shape=self.traffic_shape,
            ramp_duration_seconds=self.ramp_duration_seconds,
            target_rps=self.target_rps,
            steps_per_flow=self.steps_per_user,
        )
        async with httpx.AsyncClient(base_url=self.remote_base_url, timeout=30.0, limits=limits) as client:
            if self.cache_mode == "warm":
                first_login = remitters[0]
                await self._prewarm(client, token=str(first_login["access_token"]), fallback_ad_id=str(ads[0]["id"]))

            started = time.perf_counter()

            async def one(user_index: int, offset: float) -> None:
                delay = (started + offset) - time.perf_counter()
                if delay > 0:
                    await asyncio.sleep(delay)
                async with semaphore:
                    login = remitters[user_index % len(remitters)]
                    token = str(login["access_token"])
                    fallback_ad_id = str(ads[user_index % len(ads)]["id"])
                    await self._run_user_flow(
                        client=client,
                        user_index=user_index,
                        token=token,
                        fallback_ad_id=fallback_ad_id,
                        next_index=indexes,
                        step_semaphores=step_semaphores,
                    )

            await asyncio.gather(*(one(index, offset) for index, offset in enumerate(offsets)))

    @staticmethod
    def classify(summary: dict[str, Any], *, requested_requests: int, actual_requests: int) -> str:
        if actual_requests != requested_requests:
            return "REQUEST_TARGET_MISMATCH"
        overall = summary.get("overall", {})
        error_counts = overall.get("error_counts", {})
        if isinstance(error_counts, dict) and error_counts:
            return "MIXED"
        client_p95 = float(overall.get("client", {}).get("p95_ms", 0.0))
        backend_p95 = float(overall.get("backend_process", {}).get("p95_ms", 0.0))
        ttfb_p95 = float(overall.get("ttfb_or_headers", {}).get("p95_ms", 0.0))
        read_p95 = float(overall.get("response_read", {}).get("p95_ms", 0.0))
        response_kb_p95 = float(overall.get("response_kb_p95", 0.0))
        profile = summary.get("profile", {})
        stage_latency = profile.get("stage_latency", {}) if isinstance(profile, dict) else {}
        cache_lock_p95 = 0.0
        for stage_name in ("cache:lock_wait", "cache:coalescing_lock_wait"):
            stage = stage_latency.get(stage_name, {}) if isinstance(stage_latency, dict) else {}
            cache_lock_p95 = max(cache_lock_p95, float(stage.get("p95_ms", 0.0)))
        db_query_p95 = float(profile.get("db_query_p95_ms", 0.0)) if isinstance(profile, dict) else 0.0

        if backend_p95 >= 750 and cache_lock_p95 >= 100 and db_query_p95 < 250:
            return "BACKEND_COLD_CACHE"
        if backend_p95 >= 750 and (cache_lock_p95 >= 250 or db_query_p95 >= 250):
            return "DB_CACHE_BACKEND"
        if backend_p95 < 750 and response_kb_p95 < 100 and client_p95 > 3000:
            if read_p95 > max(ttfb_p95, backend_p95) * 1.5 and read_p95 > 1000:
                return "READ_DOWNLOAD_OR_PAYLOAD"
            if ttfb_p95 > max(read_p95, backend_p95) * 1.5 and ttfb_p95 > 1000:
                return "TTFB_EDGE_OR_RUNTIME_QUEUE"
            return "NETWORK_DELIVERY"
        if backend_p95 < 100 and client_p95 > 3000:
            return "NETWORK_DELIVERY"
        if backend_p95 >= 750:
            return "BACKEND_COLD_CACHE"
        return "INSUFFICIENT_EVIDENCE"

    def run(self) -> dict[str, Any]:
        started = time.perf_counter()
        setup_started = time.perf_counter()
        prepared = self._load_existing_fixture() if self.fixture_run_id else self.harness.prepare_dataset()
        setup_seconds = round(time.perf_counter() - setup_started, 4)
        load_started = time.perf_counter()
        asyncio.run(self._run_flows(prepared))
        load_seconds = round(time.perf_counter() - load_started, 4)
        summary = self.recorder.summary()
        total_errors = sum(count for status, count in summary["overall"]["status_counts"].items() if int(status) >= 400)
        actual_requests = int(summary["overall"]["requests"])
        classification = self.classify(summary, requested_requests=self.requests, actual_requests=actual_requests)
        request_target_mismatch = actual_requests != self.requests
        payload = {
            "slice": "slice_33A_marketplace_external_delivery_diagnostics",
            "phase": "tooling_only_marketplace_delivery_diagnostics",
            "run_id": self.run_id,
            "target": self.remote_base_url,
            "targets": {
                "businesses": self.businesses,
                "ads_per_business": self.ads_per_business,
                "synthetic_users_requested": self.synthetic_users_requested,
                "synthetic_users_used": self.synthetic_users_used,
                "requests": self.requests,
                "concurrency": self.concurrency,
                "max_connections": self.max_connections,
            },
            "request_target": {
                "requested_requests": self.requests,
                "actual_requests": actual_requests,
                "request_consumption_mode": self.request_consumption_mode,
                "steps_per_user": self.steps_per_user,
                "synthetic_users_requested": self.synthetic_users_requested,
                "synthetic_users_used": self.synthetic_users_used,
                "status": "REQUEST_TARGET_MISMATCH" if request_target_mismatch else "matched",
            },
            "cache_mode": self.cache_mode,
            "traffic": {
                "traffic_shape": self.traffic_shape,
                "ramp_duration_seconds": self.ramp_duration_seconds,
                "target_rps": self.target_rps,
                "keepalive": "on",
                "per_step_concurrency_cap": self.per_step_concurrency_cap,
                "step_jitter_ms": self.step_jitter_ms,
                "flow_mode": self.flow_mode,
                "retry_transport_once": self.retry_transport_once,
                "retry_backoff_min_ms": self.retry_backoff_min_ms,
                "retry_backoff_max_ms": self.retry_backoff_max_ms,
            },
            "prewarm": self.prewarm_result,
            "prepared": {
                "source": "fixture_run_id" if self.fixture_run_id else "inline_create",
                "fixture_run_id": self.fixture_run_id,
                "businesses": len(prepared["businesses"]),
                "ads": len(prepared["ads"]),
                "remitters": len(prepared["remitters"]),
            },
            "phase_timings": {
                "setup_seconds": setup_seconds,
                "measured_load_seconds": load_seconds,
                "total_seconds": round(time.perf_counter() - started, 4),
            },
            "staging_guardrails": {
                "checked": self.harness.guardrails is not None,
                "environment_kind": "staging" if self.harness.guardrails else None,
                "api_allowlist_checked": self.harness.guardrails is not None,
                "db_allowlist_checked": self.harness.guardrails is not None,
            },
            "summary": summary,
            "cost_units": {
                "unit": "operational_units_not_dollars",
                "measured_http_requests": len(self.recorder.records),
                "response_bytes_total": sum(int(record["response_bytes"]) for record in self.recorder.records),
                "response_kb_total": round(sum(int(record["response_bytes"]) for record in self.recorder.records) / 1024, 4),
                "profile_count": summary["profile"]["captured_profiles"],
                "synthetic_users": self.synthetic_users_used,
                "db_fixture_businesses": len(prepared["businesses"]),
                "db_fixture_ads": len(prepared["ads"]),
            },
            "classification": {
                "primary": classification,
                "request_target_mismatch": request_target_mismatch,
                "rules": [
                    "REQUEST_TARGET_MISMATCH when actual measured requests differ from requested requests.",
                    "Backend p95 below 750 ms with sub-100 KB payload and client p95 above 3000 ms is external delivery, not DB/backend.",
                    "Dominant headers latency maps to TTFB_EDGE_OR_RUNTIME_QUEUE; dominant body read maps to READ_DOWNLOAD_OR_PAYLOAD.",
                ],
            },
            "cleanup": {
                "required": True,
                "run_id": self.run_id,
                "recommended_command": (
                    f"python scripts\\staging_cleanup_synthetic_run.py --env-file <staging-env> "
                    f"--run-id {self.run_id} --apply --confirm-staging --output evidence\\slice_runs\\cleanup_{self.run_id}.json"
                ),
                "retained_by_design": {
                    "audit_logs": "Audit logs are append-only evidence and are not deleted by cleanup.",
                    "users": "Synthetic users may be retained when audit logs reference actor_user_id.",
                },
            },
            "samples": self.recorder.samples,
            "request_error_samples": self.recorder.request_errors[: self.profile_detail_limit],
            "exit_code": 1 if total_errors or request_target_mismatch else 0,
        }
        return payload


def output_contains_sensitive_marker(payload: dict[str, Any]) -> list[str]:
    def values_only(value: Any) -> Any:
        if isinstance(value, dict):
            return [values_only(item) for item in value.values()]
        if isinstance(value, list):
            return [values_only(item) for item in value]
        return value

    serialized = json.dumps(values_only(payload), ensure_ascii=False)
    return [marker for marker in SENSITIVE_OUTPUT_MARKERS if marker.lower() in serialized.lower()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--remote-base-url", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--businesses", type=int, default=250)
    parser.add_argument("--ads-per-business", type=int, default=6)
    parser.add_argument("--synthetic-users", type=int, default=1000)
    parser.add_argument("--requests", type=int, required=True)
    parser.add_argument("--concurrency", type=int, required=True)
    parser.add_argument("--max-connections", type=int, default=None)
    parser.add_argument("--profile-marketplace", action="store_true")
    parser.add_argument("--profile-detail-limit", type=int, default=PROFILE_SAMPLE_LIMIT)
    parser.add_argument("--fixture-run-id", default=None)
    parser.add_argument("--cache-mode", choices=["cold", "warm"], default="cold")
    parser.add_argument("--traffic-shape", choices=["burst", "ramp", "steady"], default="burst")
    parser.add_argument("--ramp-duration-seconds", type=int, default=None)
    parser.add_argument("--target-rps", type=float, default=None)
    parser.add_argument("--per-step-concurrency-cap", type=int, default=None)
    parser.add_argument("--step-jitter-ms", type=int, default=0)
    parser.add_argument("--flow-mode", choices=["full", "filtered_search_only"], default="full")
    parser.add_argument("--retry-transport-once", action="store_true")
    parser.add_argument("--retry-backoff-min-ms", type=int, default=100)
    parser.add_argument("--retry-backoff-max-ms", type=int, default=250)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = MarketplaceDeliveryDiagnostics(
        env_file=Path(args.env_file),
        remote_base_url=args.remote_base_url,
        run_id=args.run_id,
        businesses=args.businesses,
        ads_per_business=args.ads_per_business,
        synthetic_users=args.synthetic_users,
        requests=args.requests,
        concurrency=args.concurrency,
        max_connections=args.max_connections,
        profile_marketplace=args.profile_marketplace,
        output=Path(args.output),
        profile_detail_limit=args.profile_detail_limit,
        fixture_run_id=args.fixture_run_id,
        cache_mode=args.cache_mode,
        traffic_shape=args.traffic_shape,
        ramp_duration_seconds=args.ramp_duration_seconds,
        target_rps=args.target_rps,
        per_step_concurrency_cap=args.per_step_concurrency_cap,
        step_jitter_ms=args.step_jitter_ms,
        flow_mode=args.flow_mode,
        retry_transport_once=args.retry_transport_once,
        retry_backoff_min_ms=args.retry_backoff_min_ms,
        retry_backoff_max_ms=args.retry_backoff_max_ms,
    ).run()
    markers = output_contains_sensitive_marker(payload)
    if markers:
        payload["exit_code"] = 1
        payload["sensitive_marker_scan"] = {"status": "failed", "markers": markers}
    else:
        payload["sensitive_marker_scan"] = {"status": "passed", "markers": []}
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, default=str))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
