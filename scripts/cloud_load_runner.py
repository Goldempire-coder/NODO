from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import json
import math
import os
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from local_hardening_common import write_json


PRODUCT_GATE_MAX_CONCURRENCY = 50
RUN_PURPOSES = ("product-gate", "infra-probe")


@dataclass(frozen=True)
class RequestSpec:
    method: str
    path: str
    headers: dict[str, str]
    json: dict[str, Any] | None = None
    operation: str = "unknown"


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


def _signed_init_data(*, bot_token: str, telegram_id: int, username: str) -> str:
    payload = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": telegram_id, "username": username, "first_name": "Cloud"}, separators=(",", ":"), sort_keys=True),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


class CloudLoadRunner:
    def __init__(
        self,
        *,
        base_url: str,
        scenario: str,
        run_id: str,
        requests: int,
        concurrency: int,
        timeout_seconds: float,
        bot_token: str | None,
        remitters: int,
        amount_usd: str,
        payment_method: str,
        delivery_method: str,
        profile_marketplace: bool,
        order_ad_ids: list[str],
        run_purpose: str = "product-gate",
    ) -> None:
        validate_staging_concurrency_policy(concurrency=concurrency, run_purpose=run_purpose)
        self.base_url = base_url.rstrip("/")
        self.scenario = scenario
        self.run_id = run_id
        self.requests = requests
        self.concurrency = concurrency
        self.run_purpose = run_purpose
        self.timeout_seconds = timeout_seconds
        self.bot_token = bot_token
        self.remitters = remitters
        self.amount_usd = amount_usd
        self.payment_method = payment_method
        self.delivery_method = delivery_method
        self.profile_marketplace = profile_marketplace
        self.order_ad_ids = order_ad_ids
        self.client_latencies: list[float] = []
        self.server_latencies: list[float] = []
        self.statuses: Counter[str] = Counter()
        self.errors: Counter[str] = Counter()
        self.edges: Counter[str] = Counter()
        self.client_latencies_by_operation: dict[str, list[float]] = {}
        self.server_latencies_by_operation: dict[str, list[float]] = {}
        self.statuses_by_operation: dict[str, Counter[str]] = {}
        self.response_bytes_by_operation: Counter[str] = Counter()
        self.profiled_requests = 0
        self.profiled_requests_by_operation: Counter[str] = Counter()
        self.response_bytes_total = 0
        self.profile_stage_counts: Counter[str] = Counter()
        self.profile_stage_latencies: dict[str, list[float]] = {}
        self.profile_stage_latencies_by_operation: dict[str, dict[str, list[float]]] = {}
        self.profile_cache_hit_counts: Counter[str] = Counter()
        self.samples: list[dict[str, Any]] = []

    async def run(self) -> dict[str, Any]:
        started_at = time.perf_counter()
        limits = httpx.Limits(max_connections=max(20, self.concurrency), max_keepalive_connections=max(20, self.concurrency))
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds, limits=limits) as client:
            self._validate_scenario_inputs()
            tokens = await self._setup_tokens(client) if self._scenario_requires_auth() else []
            await self._run_requests(client, tokens=tokens)
        duration_seconds = round(time.perf_counter() - started_at, 4)
        total_errors = sum(count for status, count in self.statuses.items() if int(status) >= 400)
        cleanup_required = self._scenario_requires_auth()
        return {
            "phase": "cloud_load_runner",
            "run_id": self.run_id,
            "scenario": self.scenario,
            "target": self.base_url,
            "requests": self.requests,
            "concurrency": self.concurrency,
            "run_purpose": self.run_purpose,
            "staging_concurrency_policy": staging_concurrency_policy_payload(
                concurrency=self.concurrency,
                run_purpose=self.run_purpose,
            ),
            "duration_seconds": duration_seconds,
            "throughput_per_second": round(self.requests / duration_seconds, 4) if duration_seconds > 0 else 0.0,
            "total_errors": total_errors,
            "error_rate": round(total_errors / self.requests, 6) if self.requests else 0.0,
            "client_latency": _percentiles(self.client_latencies),
            "server_process_time": _percentiles(self.server_latencies),
            "status_counts": dict(self.statuses),
            "error_counts": dict(self.errors),
            "railway_edge_counts": dict(self.edges),
            "operations": self._operation_summary(),
            "cost_units": self._cost_units(setup_requests=len(tokens)),
            "cleanup": {
                "required": cleanup_required,
                "run_id": self.run_id if cleanup_required else None,
                "note": self._cleanup_note() if cleanup_required else None,
            },
            "samples": self.samples,
            "exit_code": 1 if total_errors else 0,
        }

    def _scenario_requires_auth(self) -> bool:
        return self.scenario in {"marketplace", "order-create", "mixed-read-order"}

    def _validate_scenario_inputs(self) -> None:
        if self.scenario == "order-create" and len(self.order_ad_ids) < self.requests:
            raise RuntimeError("order-create requires --order-ad-ids with at least one prepared synthetic ad id per request")
        if self.scenario == "mixed-read-order":
            required_order_ads = self._mixed_order_attempts()
            if len(self.order_ad_ids) < required_order_ads:
                raise RuntimeError("mixed-read-order requires enough prepared synthetic --order-ad-ids for its order attempts")

    def _cleanup_note(self) -> str:
        if self.scenario == "marketplace":
            return "Marketplace scenario creates synthetic auth users; clean later with staging cleanup by run_id."
        return "Order scenarios create synthetic auth users and mutate the explicit prepared ad ids; clean staging fixtures by the fixture run_id and this run_id."

    def _mixed_order_attempts(self) -> int:
        if self.scenario != "mixed-read-order":
            return 0
        return min(len(self.order_ad_ids), max(1, self.requests // 4))

    async def _setup_tokens(self, client: httpx.AsyncClient) -> list[str]:
        if not self.bot_token:
            raise RuntimeError("marketplace scenario requires BOT_TOKEN env or --bot-token-env")
        tokens: list[str] = []
        for index in range(self.remitters):
            telegram_id = 9_100_000_000 + (abs(hash(self.run_id)) % 100_000) * 1000 + index
            username = f"{self.run_id}_remitter_{index}"
            init_data = _signed_init_data(bot_token=self.bot_token, telegram_id=telegram_id, username=username)
            response = await client.post(
                "/api/v1/auth/telegram",
                headers={"X-Request-Id": f"req_{self.run_id}_login_{index}"},
                json={"init_data": init_data},
            )
            if response.status_code != 200:
                raise RuntimeError(f"auth setup failed with status {response.status_code}")
            data = response.json().get("data", {})
            token = data.get("access_token")
            if not isinstance(token, str):
                raise RuntimeError("auth setup response missing access_token")
            tokens.append(token)
        return tokens

    async def _run_requests(self, client: httpx.AsyncClient, *, tokens: list[str]) -> None:
        semaphore = asyncio.Semaphore(self.concurrency)

        async def one(index: int) -> None:
            async with semaphore:
                spec = self._request_spec(index, tokens=tokens)
                started = time.perf_counter()
                status = "599"
                error_code: str | None = None
                try:
                    response = await client.request(spec.method, spec.path, headers=spec.headers, json=spec.json)
                    status = str(response.status_code)
                    self._capture_headers(response, operation=spec.operation)
                    self._record_response_bytes(spec.operation, len(response.content))
                    self._capture_profile(response, operation=spec.operation)
                except httpx.RequestError as exc:
                    error_code = type(exc).__name__
                    self.errors[error_code] += 1
                elapsed_ms = (time.perf_counter() - started) * 1000
                self.client_latencies.append(elapsed_ms)
                self.client_latencies_by_operation.setdefault(spec.operation, []).append(elapsed_ms)
                self.statuses[status] += 1
                self.statuses_by_operation.setdefault(spec.operation, Counter())[status] += 1
                if len(self.samples) < 20:
                    self.samples.append({
                        "index": index,
                        "operation": spec.operation,
                        "method": spec.method,
                        "path": spec.path.split("?", 1)[0],
                        "status": status,
                        "elapsed_ms": round(elapsed_ms, 4),
                        "error": error_code,
                    })

        await asyncio.gather(*(one(index) for index in range(self.requests)))

    def _request_spec(self, index: int, *, tokens: list[str]) -> RequestSpec:
        headers = {"X-Request-Id": f"req_{self.run_id}_{index}"}
        if self.scenario == "health":
            return RequestSpec("GET", "/api/v1/health", headers, operation="health")
        if self.scenario == "ready":
            return RequestSpec("GET", "/api/v1/ready", headers, operation="ready")
        if self.scenario == "version":
            return RequestSpec("GET", "/api/v1/version", headers, operation="version")
        if self.scenario == "marketplace":
            return self._marketplace_request_spec(index, tokens=tokens, headers=headers)
        if self.scenario == "order-create":
            return self._order_request_spec(index, tokens=tokens, ad_id=self.order_ad_ids[index], headers=headers)
        if self.scenario == "mixed-read-order":
            order_attempts = self._mixed_order_attempts()
            if index < order_attempts:
                return self._order_request_spec(index, tokens=tokens, ad_id=self.order_ad_ids[index], headers=headers)
            return self._marketplace_request_spec(index, tokens=tokens, headers=headers)
        raise RuntimeError(f"unsupported scenario {self.scenario}")

    def _marketplace_request_spec(self, index: int, *, tokens: list[str], headers: dict[str, str]) -> RequestSpec:
        headers = dict(headers)
        headers["Authorization"] = f"Bearer {tokens[index % len(tokens)]}"
        if self.profile_marketplace:
            headers["X-NODO-Profile"] = "1"
        path = (
            "/api/v1/ads/search"
            f"?amount_usd={self.amount_usd}"
            f"&payment_method={self.payment_method}"
            f"&delivery_method={self.delivery_method}"
            "&limit=20"
        )
        return RequestSpec("GET", path, headers, operation="marketplace_read")

    def _order_request_spec(self, index: int, *, tokens: list[str], ad_id: str, headers: dict[str, str]) -> RequestSpec:
        headers = dict(headers)
        headers.update(
            {
                "Authorization": f"Bearer {tokens[index % len(tokens)]}",
                "Content-Type": "application/json",
                "Idempotency-Key": f"{self.run_id}_cloud_order_{index}",
            }
        )
        if self.profile_marketplace:
            headers["X-NODO-Profile"] = "1"
        return RequestSpec(
            "POST",
            "/api/v1/orders",
            headers,
            {
                "ad_id": ad_id,
                "amount_usd": self.amount_usd,
                "receiver_data": {
                    "bank": "Banco Local",
                    "phone": "+584121234567",
                    "document": f"C{index:08d}",
                    "holder": f"Cloud Receiver {index}",
                },
            },
            operation="order_create",
        )

    def _capture_profile(self, response: httpx.Response, *, operation: str = "unknown") -> None:
        if not self.profile_marketplace:
            return
        try:
            payload = response.json()
        except ValueError:
            return
        profile = ((payload.get("data") or {}).get("_profile") or {}) if isinstance(payload, dict) else {}
        if not isinstance(profile, dict):
            return
        stages = profile.get("stages")
        if isinstance(stages, list):
            self.profiled_requests += 1
            self.profiled_requests_by_operation[operation] += 1
            for stage in stages:
                if not isinstance(stage, dict):
                    continue
                name = stage.get("stage")
                if isinstance(name, str):
                    self.profile_stage_counts[name] += 1
                    self._record_profile_stage_latency(operation, name, stage.get("elapsed_ms"))
                meta = stage.get("meta") or stage.get("metadata")
                if isinstance(meta, dict) and meta.get("hit_type"):
                    self.profile_cache_hit_counts[str(meta["hit_type"])] += 1
        dependency = profile.get("dependency")
        auth_stages = (((dependency or {}).get("auth") or {}).get("stages") or []) if isinstance(dependency, dict) else []
        if isinstance(auth_stages, list):
            for stage in auth_stages:
                if isinstance(stage, dict) and isinstance(stage.get("stage"), str):
                    self.profile_stage_counts[stage["stage"]] += 1
                    self._record_profile_stage_latency(operation, stage["stage"], stage.get("elapsed_ms"))

    def _record_profile_stage_latency(self, operation: str, stage_name: str, elapsed_ms: Any) -> None:
        if isinstance(elapsed_ms, bool) or not isinstance(elapsed_ms, int | float):
            return
        elapsed = float(elapsed_ms)
        self.profile_stage_latencies.setdefault(stage_name, []).append(elapsed)
        operation_stages = self.profile_stage_latencies_by_operation.setdefault(operation, {})
        operation_stages.setdefault(stage_name, []).append(elapsed)

    def _capture_headers(self, response: httpx.Response, *, operation: str = "unknown") -> None:
        process_time = response.headers.get("x-nodo-process-time-ms")
        if process_time is not None:
            try:
                process_time_ms = float(process_time)
                self.server_latencies.append(process_time_ms)
                self.server_latencies_by_operation.setdefault(operation, []).append(process_time_ms)
            except ValueError:
                pass
        edge = response.headers.get("x-railway-edge")
        if edge:
            self.edges[edge] += 1

    def _record_response_bytes(self, operation: str, byte_count: int) -> None:
        self.response_bytes_total += byte_count
        self.response_bytes_by_operation[operation] += byte_count

    def _operation_summary(self) -> dict[str, Any]:
        operations = sorted(
            set(self.client_latencies_by_operation)
            | set(self.server_latencies_by_operation)
            | set(self.statuses_by_operation)
            | set(self.response_bytes_by_operation)
        )
        return {
            operation: {
                "requests": len(self.client_latencies_by_operation.get(operation, [])),
                "client_latency": _percentiles(self.client_latencies_by_operation.get(operation, [])),
                "server_process_time": _percentiles(self.server_latencies_by_operation.get(operation, [])),
                "status_counts": dict(self.statuses_by_operation.get(operation, Counter())),
                "response_bytes_total": int(self.response_bytes_by_operation.get(operation, 0)),
                "response_kb_total": round(self.response_bytes_by_operation.get(operation, 0) / 1024, 4),
                "profiled_requests": int(self.profiled_requests_by_operation.get(operation, 0)),
            }
            for operation in operations
        }

    def _cost_units(self, *, setup_requests: int) -> dict[str, Any]:
        measured_requests = len(self.client_latencies)
        backend_process_ms_total = round(sum(self.server_latencies), 4)
        return {
            "unit": "operational_units_not_dollars",
            "note": "Use provider billing exports to convert these units into dollars; this runner does not invent prices.",
            "scenario": self.scenario,
            "measured_http_requests": measured_requests,
            "setup_http_requests": setup_requests,
            "total_http_requests": measured_requests + setup_requests,
            "synthetic_users_created": setup_requests if self._scenario_requires_auth() else 0,
            "order_ad_ids_supplied": len(self.order_ad_ids),
            "response_bytes_total": self.response_bytes_total,
            "response_kb_total": round(self.response_bytes_total / 1024, 4),
            "client_ms_total": round(sum(self.client_latencies), 4),
            "backend_process_ms_total": backend_process_ms_total,
            "profiled_requests": self.profiled_requests,
            "profiled_requests_by_operation": dict(self.profiled_requests_by_operation),
            "profile_stage_counts": dict(self.profile_stage_counts),
            "profile_stage_latency": {
                stage: _percentiles(values)
                for stage, values in sorted(self.profile_stage_latencies.items())
            },
            "profile_stage_latency_by_operation": {
                operation: {
                    stage: _percentiles(values)
                    for stage, values in sorted(stage_values.items())
                }
                for operation, stage_values in sorted(self.profile_stage_latencies_by_operation.items())
            },
            "profile_cache_hit_counts": dict(self.profile_cache_hit_counts),
            "operations": {
                operation: {
                    "measured_http_requests": len(self.client_latencies_by_operation.get(operation, [])),
                    "response_kb_total": round(self.response_bytes_by_operation.get(operation, 0) / 1024, 4),
                    "client_ms_total": round(sum(self.client_latencies_by_operation.get(operation, [])), 4),
                    "backend_process_ms_total": round(sum(self.server_latencies_by_operation.get(operation, [])), 4),
                    "profiled_requests": int(self.profiled_requests_by_operation.get(operation, 0)),
                }
                for operation in sorted(
                    set(self.client_latencies_by_operation)
                    | set(self.server_latencies_by_operation)
                    | set(self.response_bytes_by_operation)
                    | set(self.profiled_requests_by_operation)
                )
            },
            "transport_error_counts": dict(self.errors),
        }

    def scalability_cost_row(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "concurrency": self.concurrency,
            "run_purpose": self.run_purpose,
            "requests": self.requests,
            "status_counts": dict(self.statuses),
            "client_p95_ms": _percentiles(self.client_latencies)["p95_ms"],
            "server_p95_ms": _percentiles(self.server_latencies)["p95_ms"],
            "response_kb_total": round(self.response_bytes_total / 1024, 4),
            "profiled_requests": self.profiled_requests,
            "cache_hits": dict(self.profile_cache_hit_counts),
            "transport_errors": dict(self.errors),
        }


def validate_staging_concurrency_policy(*, concurrency: int, run_purpose: str) -> None:
    if run_purpose not in RUN_PURPOSES:
        raise RuntimeError(f"unsupported run purpose {run_purpose}")
    if run_purpose == "product-gate" and concurrency > PRODUCT_GATE_MAX_CONCURRENCY:
        raise RuntimeError(
            "staging product gates are capped at c50; use --run-purpose infra-probe for c100+ transport diagnostics"
        )


def staging_concurrency_policy_payload(*, concurrency: int, run_purpose: str) -> dict[str, Any]:
    return {
        "product_gate_max_concurrency": PRODUCT_GATE_MAX_CONCURRENCY,
        "run_purpose": run_purpose,
        "classification": "product_gate" if run_purpose == "product-gate" else "infrastructure_transport_probe",
        "c100_plus_blocks_product": False,
        "c100_plus_requires_infra_probe": concurrency > PRODUCT_GATE_MAX_CONCURRENCY,
        "diagnosis": {
            "connection_transport_limit": "identified_locally",
            "github_actions_corroboration": "pending_blocked_by_github_actions_tooling",
            "marketplace_product": "not_primary_bottleneck",
            "db_cache_frontend": "not_primary_bottleneck",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--scenario", choices=["health", "ready", "version", "marketplace", "order-create", "mixed-read-order"], default="health")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--run-purpose", choices=RUN_PURPOSES, default="product-gate")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--run-id", default=f"cloud_load_{int(time.time())}")
    parser.add_argument("--output", required=True)
    parser.add_argument("--bot-token-env", default="BOT_TOKEN")
    parser.add_argument("--remitters", type=int, default=20)
    parser.add_argument("--amount-usd", default="50.00")
    parser.add_argument("--payment-method", default="zelle")
    parser.add_argument("--delivery-method", default="pago_movil_ve")
    parser.add_argument("--profile-marketplace", action="store_true")
    parser.add_argument("--order-ad-ids", default="", help="Comma-separated prepared synthetic ad ids. Required for mutating order scenarios.")
    args = parser.parse_args()
    bot_token = os.environ.get(args.bot_token_env)
    order_ad_ids = [item.strip() for item in args.order_ad_ids.split(",") if item.strip()]
    runner: CloudLoadRunner | None = None
    try:
        runner = CloudLoadRunner(
            base_url=args.base_url,
            scenario=args.scenario,
            run_id=args.run_id,
            requests=args.requests,
            concurrency=args.concurrency,
            timeout_seconds=args.timeout_seconds,
            bot_token=bot_token,
            remitters=args.remitters,
            amount_usd=args.amount_usd,
            payment_method=args.payment_method,
            delivery_method=args.delivery_method,
            profile_marketplace=args.profile_marketplace,
            order_ad_ids=order_ad_ids,
            run_purpose=args.run_purpose,
        )
        payload = asyncio.run(runner.run())
    except RuntimeError as exc:
        payload = {
            "phase": "cloud_load_runner",
            "run_id": args.run_id,
            "scenario": args.scenario,
            "target": args.base_url,
            "requests": args.requests,
            "concurrency": args.concurrency,
            "run_purpose": args.run_purpose,
            "staging_concurrency_policy": staging_concurrency_policy_payload(
                concurrency=args.concurrency,
                run_purpose=args.run_purpose,
            )
            if args.run_purpose in RUN_PURPOSES
            else {"run_purpose": args.run_purpose},
            "status_counts": {},
            "error_counts": {type(exc).__name__: 1},
            "failure": str(exc),
            "cost_units": runner._cost_units(setup_requests=0) if runner else {},
            "cleanup": {"required": False, "run_id": None, "note": None},
            "exit_code": 1,
        }
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
