from __future__ import annotations

import argparse
import asyncio
import ctypes
import json
import os
import time
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx
import psycopg

from local_hardening_common import (
    DEFAULT_ENV_FILE,
    assert_local_database_url,
    percentile,
    write_json,
)
from p2p_baseline_local import P2PBaselineLocal, RECEIVER_DETAILS

from app.shared.db.connection import connect


PRODUCT_GATE_LEVELS = frozenset({50, 100})
INFRA_PROBE_LEVELS = frozenset({250, 500, 1000})
SUPPORTED_LEVELS = PRODUCT_GATE_LEVELS | INFRA_PROBE_LEVELS
DEFAULT_OUTPUT_DIR = Path(".local/47p1")
EXPECTED_AD_CONFLICT = "AD_NOT_AVAILABLE"
EXPECTED_AD_GUARD_CONFLICT = "AD_LIMIT_NOT_ALLOWED"
PRIVATE_RESPONSE_KEYS = frozenset(
    {
        "storage_path",
        "signed_url",
        "account_value",
        "receiver_details",
        "wallet",
        "phone",
        "document",
        "holder",
    }
)
FORBIDDEN_REPORT_KEYS = frozenset(
    {
        "response_body",
        "storage_path",
        "signed_url",
        "account_value",
        "receiver_phone",
        "wallet",
        "phone",
        "document",
        "holder",
        "order_id",
        "business_id",
        "ad_id",
        "user_id",
        "token",
    }
)


@dataclass(frozen=True)
class AttemptResult:
    status_code: int | None
    error_code: str | None
    latency_ms: float
    exception_type: str | None = None
    private_field_exposed: bool = False


@dataclass(frozen=True)
class RequestSpec:
    name: str
    method: str
    path: str
    headers: dict[str, str]
    json_payload: dict[str, Any] | None = None
    inspect_private_fields: bool = False


class InFlightTracker:
    def __init__(self) -> None:
        self.active = 0
        self.peak = 0
        self._lock = asyncio.Lock()

    async def enter(self) -> None:
        async with self._lock:
            self.active += 1
            self.peak = max(self.peak, self.active)

    async def leave(self) -> None:
        async with self._lock:
            self.active -= 1


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ulong),
        ("memory_load", ctypes.c_ulong),
        ("total_physical", ctypes.c_ulonglong),
        ("available_physical", ctypes.c_ulonglong),
        ("total_page_file", ctypes.c_ulonglong),
        ("available_page_file", ctypes.c_ulonglong),
        ("total_virtual", ctypes.c_ulonglong),
        ("available_virtual", ctypes.c_ulonglong),
        ("available_extended_virtual", ctypes.c_ulonglong),
    ]


def level_kind(level: int) -> str:
    if level in PRODUCT_GATE_LEVELS:
        return "PRODUCT_GATE"
    if level in INFRA_PROBE_LEVELS:
        return "INFRA_PROBE"
    raise ValueError(f"unsupported local concurrency level: {level}")


def summarize_attempts(
    attempts: list[AttemptResult],
    *,
    requested_concurrency: int,
    effective_concurrency: int,
    expected_error_codes: set[str] | frozenset[str] = frozenset(),
    expected_status_codes: set[int] | frozenset[int] = frozenset(),
    duration_seconds: float,
) -> dict[str, Any]:
    status_counts = Counter(
        str(attempt.status_code) if attempt.status_code is not None else "EXCEPTION"
        for attempt in attempts
    )
    exception_counts = Counter(
        attempt.exception_type
        for attempt in attempts
        if attempt.exception_type is not None
    )
    latencies = [attempt.latency_ms for attempt in attempts]
    expected_errors = 0
    unexpected_errors = 0
    for attempt in attempts:
        if attempt.exception_type is not None:
            unexpected_errors += 1
            continue
        if attempt.status_code is None or attempt.status_code >= 400:
            if (
                attempt.error_code in expected_error_codes
                or attempt.status_code in expected_status_codes
            ):
                expected_errors += 1
            else:
                unexpected_errors += 1
    return {
        "requested_concurrency": requested_concurrency,
        "effective_concurrency": effective_concurrency,
        "requests_total": len(attempts),
        "status_counts": dict(sorted(status_counts.items())),
        "successful_requests": sum(
            attempt.status_code is not None and 200 <= attempt.status_code < 300
            for attempt in attempts
        ),
        "expected_errors": expected_errors,
        "unexpected_errors": unexpected_errors,
        "exception_counts": dict(sorted(exception_counts.items())),
        "private_field_violations": sum(
            attempt.private_field_exposed for attempt in attempts
        ),
        "p50_ms": percentile(latencies, 0.50),
        "p95_ms": percentile(latencies, 0.95),
        "p99_ms": percentile(latencies, 0.99),
        "duration_seconds": round(duration_seconds, 4),
    }


def assert_safe_report(value: Any, *, path: str = "report") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in FORBIDDEN_REPORT_KEYS:
                raise ValueError(f"unsafe report field at {path}: {key}")
            assert_safe_report(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            assert_safe_report(item, path=f"{path}[{index}]")


def write_ndjson(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for record in records:
        assert_safe_report(record)
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _contains_private_response_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            key.lower() in PRIVATE_RESPONSE_KEYS
            or _contains_private_response_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_private_response_key(item) for item in value)
    return False


def _memory_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "logical_cpus": os.cpu_count(),
        "process_cpu_seconds": round(time.process_time(), 4),
    }
    if os.name != "nt":
        snapshot["memory_probe"] = "NOT_TESTED_NON_WINDOWS"
        return snapshot
    status = _MemoryStatusEx()
    status.length = ctypes.sizeof(_MemoryStatusEx)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        gib = 1024**3
        snapshot.update(
            {
                "memory_total_gib": round(status.total_physical / gib, 3),
                "memory_available_gib": round(status.available_physical / gib, 3),
                "memory_load_percent": int(status.memory_load),
            }
        )
    else:
        snapshot["memory_probe"] = "UNAVAILABLE"
    return snapshot


def _resource_usage(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    duration_seconds: float,
) -> dict[str, Any]:
    cpu_seconds = max(
        0.0,
        float(after["process_cpu_seconds"]) - float(before["process_cpu_seconds"]),
    )
    cpu_count = int(after.get("logical_cpus") or 1)
    cpu_percent = (
        (cpu_seconds / (duration_seconds * cpu_count)) * 100
        if duration_seconds > 0
        else 0.0
    )
    return {
        "logical_cpus": after.get("logical_cpus"),
        "process_cpu_seconds": round(cpu_seconds, 4),
        "process_cpu_percent_of_machine": round(cpu_percent, 3),
        "memory_available_gib_before": before.get("memory_available_gib"),
        "memory_available_gib_after": after.get("memory_available_gib"),
        "memory_load_percent_after": after.get("memory_load_percent"),
    }


def _parse_levels(raw: str) -> list[int]:
    try:
        levels = sorted({int(item.strip()) for item in raw.split(",") if item.strip()})
    except ValueError as exc:
        raise argparse.ArgumentTypeError("levels must be comma-separated integers") from exc
    unsupported = set(levels) - SUPPORTED_LEVELS
    if not levels or unsupported:
        raise argparse.ArgumentTypeError(
            f"levels must be selected from {sorted(SUPPORTED_LEVELS)}"
        )
    return levels


class P2PConcurrency47P1(P2PBaselineLocal):
    """Local-only PostgreSQL concurrency probes with aggregate evidence."""

    def __init__(
        self,
        *,
        env_file: Path,
        run_id: str,
        levels: list[int],
        chat_orders: int,
        messages_per_order: int,
    ) -> None:
        super().__init__(
            env_file=env_file,
            run_id=run_id,
            same_ad_requests=min(levels),
        )
        assert_local_database_url(self.db_url)
        self.levels = levels
        self.chat_orders = chat_orders
        self.messages_per_order = messages_per_order

    async def _execute_specs(
        self,
        specs: list[RequestSpec],
    ) -> tuple[list[AttemptResult], int, float]:
        gate = asyncio.Event()
        tracker = InFlightTracker()
        transport = httpx.ASGITransport(app=self.client.app)

        async def execute(client: httpx.AsyncClient, spec: RequestSpec) -> AttemptResult:
            await gate.wait()
            await tracker.enter()
            started_at = time.perf_counter()
            try:
                response = await self._async_request(
                    client,
                    name=spec.name,
                    method=spec.method,
                    path=spec.path,
                    headers=spec.headers,
                    json=spec.json_payload,
                )
                latency_ms = (time.perf_counter() - started_at) * 1000
                private_exposed = False
                if spec.inspect_private_fields:
                    try:
                        private_exposed = _contains_private_response_key(
                            response.json()
                        )
                    except ValueError:
                        private_exposed = True
                return AttemptResult(
                    status_code=response.status_code,
                    error_code=self._safe_error_code(response),
                    latency_ms=round(latency_ms, 4),
                    private_field_exposed=private_exposed,
                )
            except Exception as exc:  # noqa: BLE001 - safe aggregate probe
                return AttemptResult(
                    status_code=None,
                    error_code=None,
                    latency_ms=round((time.perf_counter() - started_at) * 1000, 4),
                    exception_type=type(exc).__name__,
                )
            finally:
                await tracker.leave()

        started_at = time.perf_counter()
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            timeout=60.0,
        ) as client:
            tasks = [asyncio.create_task(execute(client, spec)) for spec in specs]
            await asyncio.sleep(0)
            gate.set()
            attempts = await asyncio.gather(*tasks)
        return attempts, tracker.peak, time.perf_counter() - started_at

    def _aggregate_order_counts(self, ad_ids: list[str]) -> dict[str, Any]:
        with connect(self.db_url, row_factory=psycopg.rows.dict_row) as conn:
            order_row = conn.execute(
                """
                select count(*) as total,
                       count(*) filter (
                           where status in (
                               'waiting_payment', 'payment_reported',
                               'payment_confirmed', 'delivered', 'disputed'
                           )
                       ) as open_total
                from orders
                where ad_id = any(%s::uuid[])
                """,
                (ad_ids,),
            ).fetchone()
            reservation_rows = conn.execute(
                """
                select reservation.status,
                       count(*) as total,
                       coalesce(sum(reservation.amount_usd), 0.00) as amount_usd
                from business_capacity_reservations reservation
                join orders on orders.id = reservation.order_id
                where orders.ad_id = any(%s::uuid[])
                group by reservation.status
                """,
                (ad_ids,),
            ).fetchall()
            state_events = conn.execute(
                """
                select count(*) as total
                from order_state_events event
                join orders on orders.id = event.order_id
                where orders.ad_id = any(%s::uuid[])
                  and event.event_type = 'order_created'
                """,
                (ad_ids,),
            ).fetchone()["total"]
            audit_events = conn.execute(
                """
                select count(*) as total
                from audit_logs audit
                join orders on orders.id = audit.resource_id
                where orders.ad_id = any(%s::uuid[])
                  and audit.event_type = 'order_created'
                """,
                (ad_ids,),
            ).fetchone()["total"]
            notification_jobs = conn.execute(
                """
                select count(*) as total
                from notification_jobs job
                join orders on orders.id = job.order_id
                where orders.ad_id = any(%s::uuid[])
                  and job.notification_type = 'order_created_business'
                """,
                (ad_ids,),
            ).fetchone()["total"]
        reservation_counts = {
            row["status"]: {
                "count": int(row["total"]),
                "amount_usd": str(Decimal(str(row["amount_usd"]))),
            }
            for row in reservation_rows
        }
        return {
            "postgres_counts": {
                "orders": int(order_row["total"]),
                "open_orders": int(order_row["open_total"]),
                "order_created_events": int(state_events),
                "order_created_audits": int(audit_events),
                "notification_jobs": int(notification_jobs),
            },
            "reservation_counts": reservation_counts,
        }

    def _global_db_snapshot(self) -> dict[str, Any]:
        scalar_queries = {
            "orders": "select count(*) from orders",
            "payment_reports": "select count(*) from payment_reports",
            "messages": "select count(*) from messages",
            "receiver_details": "select count(*) from order_receiver_details",
            "order_state_events": "select count(*) from order_state_events",
            "audit_logs": "select count(*) from audit_logs",
            "notification_jobs": "select count(*) from notification_jobs",
            "credit_consumptions": (
                "select count(*) from credits_ledger where type = 'consume'"
            ),
        }
        with connect(self.db_url) as conn:
            snapshot = {
                name: int(conn.execute(query).fetchone()[0])
                for name, query in scalar_queries.items()
            }
            reservation_rows = conn.execute(
                """
                select status, count(*)
                from business_capacity_reservations
                group by status
                """
            ).fetchall()
        snapshot["business_capacity_reservations"] = {
            str(status): int(count) for status, count in reservation_rows
        }
        return snapshot

    @staticmethod
    def _snapshot_delta(
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> tuple[dict[str, int], dict[str, int]]:
        postgres_counts = {
            key: int(after[key]) - int(before[key])
            for key in before
            if key != "business_capacity_reservations"
        }
        statuses = set(before["business_capacity_reservations"]) | set(
            after["business_capacity_reservations"]
        )
        reservation_counts = {
            status: int(after["business_capacity_reservations"].get(status, 0))
            - int(before["business_capacity_reservations"].get(status, 0))
            for status in sorted(statuses)
        }
        return postgres_counts, reservation_counts

    @staticmethod
    def _scenario_record(
        *,
        name: str,
        gate: str,
        attempts: list[AttemptResult],
        requested_concurrency: int,
        effective_concurrency: int,
        expected_error_codes: set[str] | frozenset[str] = frozenset(),
        expected_status_codes: set[int] | frozenset[int] = frozenset(),
        duration_seconds: float,
        passed: bool,
        status: str,
        postgres_counts: dict[str, Any],
        reservation_counts: dict[str, Any],
        invariant_violations: list[str],
        resource_usage: dict[str, Any],
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "scenario": name,
            "gate": gate,
            "status": status,
            "passed": passed,
            **summarize_attempts(
                attempts,
                requested_concurrency=requested_concurrency,
                effective_concurrency=effective_concurrency,
                expected_error_codes=expected_error_codes,
                expected_status_codes=expected_status_codes,
                duration_seconds=duration_seconds,
            ),
            "postgres_counts": postgres_counts,
            "reservation_counts": reservation_counts,
            "invariant_violations": invariant_violations,
            "resource_usage": resource_usage,
            "details": details or {},
        }

    async def _same_ad_contention(
        self,
        *,
        admin: dict[str, Any],
        level: int,
    ) -> dict[str, Any]:
        label = f"same_ad_c{level}"
        fixture = self._business_fixture(
            admin=admin,
            label=label,
            method_types=("zelle",),
            declared_capacity_usd=Decimal("50.00"),
            credits=3,
        )
        ad = self._create_ad(
            phase="setup",
            owner=fixture["owner"],
            payment_method_id=self._method_id(fixture, "zelle"),
            payment_method="zelle",
            label=label,
        )
        remitters = [
            self._actor(
                offset=300_000 + level * 1_000 + index,
                label=f"{label}_client_{index}",
            )
            for index in range(level)
        ]
        specs = [
            RequestSpec(
                name=f"concurrency:orders:{label}",
                method="POST",
                path="/api/v1/orders",
                headers=self.headers(
                    remitter,
                    f"47p1_{label}_{index}",
                    content_type=True,
                ),
                json_payload={"ad_id": ad["id"], "amount_usd": "50.00"},
            )
            for index, remitter in enumerate(remitters)
        ]
        before_resource = _memory_snapshot()
        attempts, peak, duration = await self._execute_specs(specs)
        after_resource = _memory_snapshot()
        counts = self._aggregate_order_counts([ad["id"]])
        winners = sum(attempt.status_code == 201 for attempt in attempts)
        expected_conflicts = sum(
            attempt.status_code == 409
            and attempt.error_code == EXPECTED_AD_CONFLICT
            for attempt in attempts
        )
        orders = counts["postgres_counts"]["orders"]
        reserved = counts["reservation_counts"].get("reserved", {}).get("count", 0)
        integrity_violation = winners > 1 or orders > 1 or reserved > 1
        strict_pass = (
            winners == 1
            and expected_conflicts == level - 1
            and orders == 1
            and reserved == 1
            and all(attempt.exception_type is None for attempt in attempts)
        )
        gate = level_kind(level)
        if strict_pass:
            status = "PASS"
        elif gate == "INFRA_PROBE" and not integrity_violation:
            status = "LOCAL_RESOURCE_LIMIT"
        elif integrity_violation:
            status = "INTEGRITY_VIOLATION"
        else:
            status = "FAILED_PRODUCT_GATE"
        violations = ["same_ad_more_than_one_winner"] if integrity_violation else []
        return self._scenario_record(
            name=f"same_ad_contention_c{level}",
            gate=gate,
            attempts=attempts,
            requested_concurrency=level,
            effective_concurrency=peak,
            expected_error_codes={EXPECTED_AD_CONFLICT},
            duration_seconds=duration,
            passed=strict_pass,
            status=status,
            postgres_counts=counts["postgres_counts"],
            reservation_counts=counts["reservation_counts"],
            invariant_violations=violations,
            resource_usage=_resource_usage(
                before_resource,
                after_resource,
                duration_seconds=duration,
            ),
            details={"winner_count": winners},
        )

    async def _two_order_race(
        self,
        *,
        admin: dict[str, Any],
        label: str,
        active_order_limit: int,
        declared_capacity_usd: Decimal,
        expected_winners: int,
    ) -> dict[str, Any]:
        fixture = self._business_fixture(
            admin=admin,
            label=label,
            method_types=("zelle", "usdt_trc20"),
            declared_capacity_usd=declared_capacity_usd,
            credits=4,
            active_order_limit=active_order_limit,
        )
        ads = [
            self._create_ad(
                phase="setup",
                owner=fixture["owner"],
                payment_method_id=self._method_id(fixture, method),
                payment_method=method,
                label=f"{label}_{method}",
                amount_max_usd="50.00",
            )
            for method in ("zelle", "usdt_trc20")
        ]
        remitters = [
            self._actor(
                offset=510_000 + self._fixture_sequence * 10 + index,
                label=f"{label}_client_{index}",
            )
            for index in range(2)
        ]
        specs = [
            RequestSpec(
                name=f"concurrency:orders:{label}",
                method="POST",
                path="/api/v1/orders",
                headers=self.headers(
                    remitters[index],
                    f"47p1_{label}_{index}",
                    content_type=True,
                ),
                json_payload={"ad_id": ads[index]["id"], "amount_usd": "50.00"},
            )
            for index in range(2)
        ]
        before_resource = _memory_snapshot()
        attempts, peak, duration = await self._execute_specs(specs)
        after_resource = _memory_snapshot()
        counts = self._aggregate_order_counts([ad["id"] for ad in ads])
        winners = sum(attempt.status_code == 201 for attempt in attempts)
        expected_conflicts = sum(
            attempt.status_code == 409
            and attempt.error_code == EXPECTED_AD_CONFLICT
            for attempt in attempts
        )
        reserved = counts["reservation_counts"].get("reserved", {})
        reserved_count = int(reserved.get("count", 0))
        reserved_amount = Decimal(str(reserved.get("amount_usd", "0.00")))
        capacity_safe = reserved_amount <= declared_capacity_usd
        passed = (
            winners == expected_winners
            and reserved_count == expected_winners
            and counts["postgres_counts"]["orders"] == expected_winners
            and capacity_safe
            and all(attempt.exception_type is None for attempt in attempts)
            and (
                expected_winners == 2
                or expected_conflicts == 2 - expected_winners
            )
        )
        violations = []
        if winners > expected_winners:
            violations.append("active_order_limit_exceeded")
        if not capacity_safe:
            violations.append("shared_capacity_exceeded")
        scenario_name = (
            "active_order_limit" if active_order_limit == 1 else "shared_capacity_orders"
        )
        return self._scenario_record(
            name=scenario_name,
            gate="PRODUCT_GATE",
            attempts=attempts,
            requested_concurrency=2,
            effective_concurrency=peak,
            expected_error_codes={EXPECTED_AD_CONFLICT},
            duration_seconds=duration,
            passed=passed,
            status="PASS" if passed else "FAILED_PRODUCT_GATE",
            postgres_counts=counts["postgres_counts"],
            reservation_counts=counts["reservation_counts"],
            invariant_violations=violations,
            resource_usage=_resource_usage(
                before_resource,
                after_resource,
                duration_seconds=duration,
            ),
            details={
                "winner_count": winners,
                "declared_capacity_usd": str(declared_capacity_usd),
                "reserved_amount_usd": str(reserved_amount),
            },
        )

    async def _ad_publication_case(
        self,
        *,
        admin: dict[str, Any],
        label: str,
        methods: tuple[str, str],
        amount_max_usd: str,
    ) -> dict[str, Any]:
        fixture = self._business_fixture(
            admin=admin,
            label=label,
            method_types=methods,
            declared_capacity_usd=Decimal("100.00"),
            credits=4,
        )
        method_offsets: dict[str, int] = {}
        specs: list[RequestSpec] = []
        for index, method in enumerate(methods):
            method_index = method_offsets.get(method, 0)
            method_offsets[method] = method_index + 1
            specs.append(
                RequestSpec(
                    name=f"concurrency:ads:{label}",
                    method="POST",
                    path="/api/v1/business/ads",
                    headers=self.headers(
                        fixture["owner"],
                        f"47p1_{label}_{index}",
                        content_type=True,
                    ),
                    json_payload={
                        "payment_method_id": self._method_id(
                            fixture,
                            method,
                            index=method_index,
                        ),
                        "payment_method": method,
                        "delivery_method": "pago_movil_ve",
                        "rate_bs_per_usd": "39.5000",
                        "amount_min_usd": "20.00",
                        "amount_max_usd": amount_max_usd,
                    },
                )
            )
        before_resource = _memory_snapshot()
        attempts, peak, duration = await self._execute_specs(specs)
        after_resource = _memory_snapshot()
        with connect(self.db_url, row_factory=psycopg.rows.dict_row) as conn:
            row = conn.execute(
                """
                select count(*) as active_count,
                       coalesce(sum(amount_max_usd), 0.00) as committed_max,
                       count(*) filter (where payment_method = 'zelle') as zelle_count,
                       count(*) filter (where payment_method = 'usdt_trc20') as usdt_count
                from ads
                where business_id = %s and status in ('active', 'in_order')
                """,
                (fixture["business_id"],),
            ).fetchone()
        winners = sum(attempt.status_code == 201 for attempt in attempts)
        committed = Decimal(str(row["committed_max"]))
        passed = (
            winners == 1
            and sum(
                attempt.status_code == 409
                and attempt.error_code == EXPECTED_AD_GUARD_CONFLICT
                for attempt in attempts
            )
            == 1
            and int(row["active_count"]) == 1
            and int(row["zelle_count"]) <= 1
            and int(row["usdt_count"]) <= 1
            and committed <= Decimal("100.00")
        )
        violations = []
        if int(row["zelle_count"]) > 1 or int(row["usdt_count"]) > 1:
            violations.append("duplicate_active_method")
        if committed > Decimal("100.00"):
            violations.append("advertised_capacity_exceeded")
        return self._scenario_record(
            name=f"concurrent_ad_publication_{label}",
            gate="PRODUCT_GATE",
            attempts=attempts,
            requested_concurrency=2,
            effective_concurrency=peak,
            expected_error_codes={EXPECTED_AD_GUARD_CONFLICT},
            duration_seconds=duration,
            passed=passed,
            status="PASS" if passed else "FAILED_PRODUCT_GATE",
            postgres_counts={
                "active_ads": int(row["active_count"]),
                "active_zelle": int(row["zelle_count"]),
                "active_usdt": int(row["usdt_count"]),
            },
            reservation_counts={},
            invariant_violations=violations,
            resource_usage=_resource_usage(
                before_resource,
                after_resource,
                duration_seconds=duration,
            ),
            details={"committed_max_usd": str(committed)},
        )

    def _attempts_since(
        self,
        start_index: int,
        *,
        name_fragment: str,
    ) -> list[AttemptResult]:
        return [
            AttemptResult(
                status_code=int(step["status_code"]),
                error_code=None,
                latency_ms=float(step["latency_ms"]),
            )
            for step in self._safe_steps[start_index:]
            if step["phase"] == "concurrency" and name_fragment in step["name"]
        ]

    async def _double_delivery_record(
        self,
        *,
        admin: dict[str, Any],
    ) -> dict[str, Any]:
        prepared = self._setup_reported_order(admin=admin, label="double_delivery")
        order_id = prepared["order"]["id"]
        self._request_data(
            "setup",
            "setup:confirm_payment:double_delivery",
            "POST",
            f"/api/v1/business/orders/{order_id}/confirm-payment",
            headers=self.headers(
                prepared["owner"],
                "47p1_double_delivery_confirm",
                content_type=True,
            ),
            json={"reason": "Pago recibido antes de entrega concurrente"},
        )
        self._request_data(
            "setup",
            "setup:receiver_details:double_delivery",
            "PUT",
            f"/api/v1/orders/{order_id}/receiver-details",
            headers=self.headers(
                prepared["remitter"],
                "47p1_double_delivery_receiver",
                content_type=True,
            ),
            json=RECEIVER_DETAILS,
        )
        shared_key = "47p1_double_delivery"
        specs = [
            RequestSpec(
                name="concurrency:business:double_delivery",
                method="POST",
                path=f"/api/v1/business/orders/{order_id}/mark-delivered",
                headers={
                    **self.headers(
                        prepared["owner"],
                        shared_key,
                        content_type=True,
                    ),
                    "X-Request-Id": (
                        f"req_{self.run_id}_double_delivery_{index}"
                    ),
                },
                json_payload={"reason": "Pago movil enviado en carrera local"},
            )
            for index in range(2)
        ]
        before_resource = _memory_snapshot()
        attempts, peak, duration = await self._execute_specs(specs)
        after_resource = _memory_snapshot()
        with connect(self.db_url, row_factory=psycopg.rows.dict_row) as conn:
            order_status = conn.execute(
                "select status from orders where id = %s",
                (order_id,),
            ).fetchone()["status"]
            delivered_events = conn.execute(
                """
                select count(*) as total
                from order_state_events
                where order_id = %s and event_type = 'order_delivered'
                """,
                (order_id,),
            ).fetchone()["total"]
            delivered_audits = conn.execute(
                """
                select count(*) as total
                from audit_logs
                where resource_id = %s and event_type = 'order_delivered'
                """,
                (order_id,),
            ).fetchone()["total"]
            delivered_jobs = conn.execute(
                """
                select count(*) as total
                from notification_jobs
                where order_id = %s
                  and notification_type = 'order_delivered_client'
                """,
                (order_id,),
            ).fetchone()["total"]
            reservation_status = conn.execute(
                """
                select status
                from business_capacity_reservations
                where order_id = %s
                """,
                (order_id,),
            ).fetchone()["status"]
            credit_consumptions = conn.execute(
                """
                select count(*) as total
                from credits_ledger
                where related_order_id = %s and type = 'consume'
                """,
                (order_id,),
            ).fetchone()["total"]
        passed = (
            any(attempt.status_code == 200 for attempt in attempts)
            and all(attempt.status_code in {200, 409} for attempt in attempts)
            and order_status == "delivered"
            and int(delivered_events) == 1
            and int(delivered_audits) == 1
            and int(delivered_jobs) == 1
            and reservation_status == "reserved"
            and int(credit_consumptions) == 1
        )
        return self._scenario_record(
            name="double_delivery",
            gate="PRODUCT_GATE",
            attempts=attempts,
            requested_concurrency=2,
            effective_concurrency=peak,
            expected_status_codes={409},
            duration_seconds=duration,
            passed=passed,
            status="PASS" if passed else "FAILED_PRODUCT_GATE",
            postgres_counts={
                "order_delivered_events": int(delivered_events),
                "order_delivered_audits": int(delivered_audits),
                "notification_jobs": int(delivered_jobs),
                "credit_consumptions": int(credit_consumptions),
            },
            reservation_counts={reservation_status: 1},
            invariant_violations=[] if passed else ["delivery_effect_duplicated"],
            resource_usage=_resource_usage(
                before_resource,
                after_resource,
                duration_seconds=duration,
            ),
            details={"final_status": order_status},
        )

    async def _double_transition_records(
        self,
        *,
        admin: dict[str, Any],
    ) -> list[dict[str, Any]]:
        before_db = self._global_db_snapshot()
        before_resource = _memory_snapshot()
        start_index = len(self._safe_steps)
        started_at = time.perf_counter()
        raw = await self._double_confirm_and_completion(admin)
        duration = time.perf_counter() - started_at
        after_resource = _memory_snapshot()
        after_db = self._global_db_snapshot()
        postgres_counts, reservation_counts = self._snapshot_delta(
            before_db,
            after_db,
        )
        resource_usage = _resource_usage(
            before_resource,
            after_resource,
            duration_seconds=duration,
        )
        confirm_attempts = self._attempts_since(
            start_index,
            name_fragment="confirm_payment",
        )
        completion_attempts = self._attempts_since(
            start_index,
            name_fragment="confirm_received",
        )
        confirm_passed = (
            any(attempt.status_code == 200 for attempt in confirm_attempts)
            and raw["payment_confirmed_events"] == 1
            and raw["credit_consume_rows"] == 1
        )
        completion_passed = (
            any(attempt.status_code == 200 for attempt in completion_attempts)
            and raw["completed_events"] == 1
            and raw["reservation_status"] == "consumed"
        )
        return [
            self._scenario_record(
                name="double_payment_confirmation",
                gate="PRODUCT_GATE",
                attempts=confirm_attempts,
                requested_concurrency=2,
                effective_concurrency=2,
                expected_status_codes={409},
                duration_seconds=duration,
                passed=confirm_passed,
                status="PASS" if confirm_passed else "FAILED_PRODUCT_GATE",
                postgres_counts=postgres_counts,
                reservation_counts=reservation_counts,
                invariant_violations=(
                    [] if confirm_passed else ["payment_confirmation_duplicated"]
                ),
                resource_usage=resource_usage,
                details={
                    "payment_confirmed_events": raw["payment_confirmed_events"],
                    "credit_consume_rows": raw["credit_consume_rows"],
                },
            ),
            self._scenario_record(
                name="double_completion",
                gate="PRODUCT_GATE",
                attempts=completion_attempts,
                requested_concurrency=2,
                effective_concurrency=2,
                expected_status_codes={409},
                duration_seconds=duration,
                passed=completion_passed,
                status="PASS" if completion_passed else "FAILED_PRODUCT_GATE",
                postgres_counts=postgres_counts,
                reservation_counts=reservation_counts,
                invariant_violations=(
                    [] if completion_passed else ["completion_effect_duplicated"]
                ),
                resource_usage=resource_usage,
                details={
                    "completed_events": raw["completed_events"],
                    "reservation_status": raw["reservation_status"],
                },
            ),
        ]

    async def _existing_race_record(
        self,
        *,
        name: str,
        runner: Callable[[], Awaitable[dict[str, Any]]],
        name_fragment: str,
    ) -> dict[str, Any]:
        before_db = self._global_db_snapshot()
        before_resource = _memory_snapshot()
        start_index = len(self._safe_steps)
        started_at = time.perf_counter()
        raw = await runner()
        duration = time.perf_counter() - started_at
        after_resource = _memory_snapshot()
        after_db = self._global_db_snapshot()
        postgres_counts, reservation_counts = self._snapshot_delta(
            before_db,
            after_db,
        )
        attempts = self._attempts_since(
            start_index,
            name_fragment=name_fragment,
        )
        passed = bool(raw["passed"])
        return self._scenario_record(
            name=name,
            gate="PRODUCT_GATE",
            attempts=attempts,
            requested_concurrency=2,
            effective_concurrency=2,
            expected_status_codes={409},
            duration_seconds=duration,
            passed=passed,
            status="PASS" if passed else "FAILED_PRODUCT_GATE",
            postgres_counts=postgres_counts,
            reservation_counts=reservation_counts,
            invariant_violations=[] if passed else [f"{name}_state_split"],
            resource_usage=_resource_usage(
                before_resource,
                after_resource,
                duration_seconds=duration,
            ),
            details={
                "winner_count": raw.get("winner_count"),
                "final_status": raw.get("db", {}).get("status"),
                "payment_reports": raw.get("db", {}).get("payment_reports"),
                "reservation_status": raw.get("db", {}).get("reservation_status"),
                "worker_status": raw.get("worker_status"),
            },
        )

    async def _chat_burst(
        self,
        *,
        admin: dict[str, Any],
    ) -> dict[str, Any]:
        chats: list[dict[str, Any]] = []
        for index in range(self.chat_orders):
            label = f"chat_burst_{index}"
            fixture = self._business_fixture(
                admin=admin,
                label=label,
                method_types=("zelle",),
                declared_capacity_usd=Decimal("50.00"),
                credits=2,
            )
            ad = self._create_ad(
                phase="setup",
                owner=fixture["owner"],
                payment_method_id=self._method_id(fixture, "zelle"),
                payment_method="zelle",
                label=label,
            )
            remitter = self._actor(
                offset=620_000 + index,
                label=f"{label}_client",
            )
            order = self._create_order(
                phase="setup",
                remitter=remitter,
                ad_id=ad["id"],
                label=label,
            )
            chats.append(
                {
                    "order": order,
                    "owner": fixture["owner"],
                    "remitter": remitter,
                    "token": f"47p1-{self.run_id}-chat-{index}",
                }
            )
        specs: list[RequestSpec] = []
        for chat_index, chat in enumerate(chats):
            for message_index in range(self.messages_per_order):
                actor = (
                    chat["remitter"] if message_index % 2 == 0 else chat["owner"]
                )
                specs.append(
                    RequestSpec(
                        name="concurrency:chat:burst",
                        method="POST",
                        path=f"/api/v1/orders/{chat['order']['id']}/messages",
                        headers=self.headers(
                            actor,
                            f"47p1_chat_{chat_index}_{message_index}",
                            content_type=True,
                        ),
                        json_payload={
                            "body": f"{chat['token']}-message-{message_index}",
                            "attachment_ids": [],
                        },
                        inspect_private_fields=True,
                    )
                )
        before_resource = _memory_snapshot()
        attempts, peak, duration = await self._execute_specs(specs)
        after_resource = _memory_snapshot()
        order_ids = [chat["order"]["id"] for chat in chats]
        with connect(self.db_url, row_factory=psycopg.rows.dict_row) as conn:
            rows = conn.execute(
                """
                select order_id::text, sender_user_id::text, body
                from messages
                where order_id = any(%s::uuid[])
                """,
                (order_ids,),
            ).fetchall()
        expected_by_order = {
            chat["order"]["id"]: {
                "token": chat["token"],
                "participants": {
                    chat["owner"]["user"]["id"],
                    chat["remitter"]["user"]["id"],
                },
            }
            for chat in chats
        }
        counts_by_order = Counter(row["order_id"] for row in rows)
        cross_order_messages = 0
        ownership_violations = 0
        for row in rows:
            expected = expected_by_order.get(row["order_id"])
            if expected is None or not row["body"].startswith(expected["token"]):
                cross_order_messages += 1
            if expected is None or row["sender_user_id"] not in expected["participants"]:
                ownership_violations += 1
        expected_total = self.chat_orders * self.messages_per_order
        complete_orders = sum(
            counts_by_order.get(chat["order"]["id"], 0) == self.messages_per_order
            for chat in chats
        )
        passed = (
            len(rows) == expected_total
            and complete_orders == self.chat_orders
            and cross_order_messages == 0
            and ownership_violations == 0
            and all(attempt.status_code == 201 for attempt in attempts)
            and not any(attempt.private_field_exposed for attempt in attempts)
        )
        violations = []
        if cross_order_messages:
            violations.append("chat_cross_order_message")
        if ownership_violations:
            violations.append("chat_sender_ownership")
        if any(attempt.private_field_exposed for attempt in attempts):
            violations.append("chat_private_field_exposure")
        return self._scenario_record(
            name="chat_burst",
            gate="PRODUCT_GATE",
            attempts=attempts,
            requested_concurrency=len(specs),
            effective_concurrency=peak,
            duration_seconds=duration,
            passed=passed,
            status="PASS" if passed else "FAILED_PRODUCT_GATE",
            postgres_counts={
                "messages": len(rows),
                "orders_with_expected_message_count": complete_orders,
            },
            reservation_counts={},
            invariant_violations=violations,
            resource_usage=_resource_usage(
                before_resource,
                after_resource,
                duration_seconds=duration,
            ),
            details={
                "orders": self.chat_orders,
                "messages_per_order": self.messages_per_order,
                "cross_order_messages": cross_order_messages,
                "ownership_violations": ownership_violations,
            },
        )

    def _sync_attempt(
        self,
        *,
        name: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> tuple[httpx.Response, AttemptResult]:
        started_at = time.perf_counter()
        response = self.client.request(method, path, **kwargs)
        latency_ms = (time.perf_counter() - started_at) * 1000
        self._record_response(
            phase="concurrency",
            name=name,
            method=method,
            path=path,
            response=response,
            started_at=started_at,
        )
        return response, AttemptResult(
            status_code=response.status_code,
            error_code=self._safe_error_code(response),
            latency_ms=round(latency_ms, 4),
        )

    def _receiver_details(self, *, admin: dict[str, Any]) -> dict[str, Any]:
        before_resource = _memory_snapshot()
        started_at = time.perf_counter()
        prepared = self._setup_reported_order(admin=admin, label="receiver_details")
        order_id = prepared["order"]["id"]
        attempts: list[AttemptResult] = []
        _, attempt = self._sync_attempt(
            name="concurrency:receiver:confirm_payment",
            method="POST",
            path=f"/api/v1/business/orders/{order_id}/confirm-payment",
            headers=self.headers(
                prepared["owner"],
                "47p1_receiver_confirm",
                content_type=True,
            ),
            json={"reason": "Pago recibido en prueba local"},
        )
        attempts.append(attempt)
        blocked, attempt = self._sync_attempt(
            name="concurrency:receiver:required",
            method="POST",
            path=f"/api/v1/business/orders/{order_id}/mark-delivered",
            headers=self.headers(
                prepared["owner"],
                "47p1_receiver_blocked_delivery",
                content_type=True,
            ),
            json={"reason": "Entrega local sin datos"},
        )
        attempts.append(attempt)
        invalid_payload = {**RECEIVER_DETAILS, "phone": "+14155552671"}
        invalid, attempt = self._sync_attempt(
            name="concurrency:receiver:runtime_invalid",
            method="PUT",
            path=f"/api/v1/orders/{order_id}/receiver-details",
            headers=self.headers(
                prepared["remitter"],
                "47p1_receiver_invalid",
                content_type=True,
            ),
            json=invalid_payload,
        )
        attempts.append(attempt)
        valid, attempt = self._sync_attempt(
            name="concurrency:receiver:local_valid",
            method="PUT",
            path=f"/api/v1/orders/{order_id}/receiver-details",
            headers=self.headers(
                prepared["remitter"],
                "47p1_receiver_valid",
                content_type=True,
            ),
            json=RECEIVER_DETAILS,
        )
        attempts.append(attempt)
        reveal, attempt = self._sync_attempt(
            name="concurrency:receiver:participant_reveal",
            method="GET",
            path=f"/api/v1/orders/{order_id}/receiver-details",
            headers=self.bearer(prepared["owner"], "47p1_receiver_reveal"),
        )
        attempts.append(attempt)
        postgres_rejected_invalid = False
        with connect(self.db_url) as conn:
            try:
                conn.execute(
                    """
                    update order_receiver_details
                    set phone = '+14155552671'
                    where order_id = %s
                    """,
                    (order_id,),
                )
                conn.commit()
            except psycopg.Error as exc:
                conn.rollback()
                postgres_rejected_invalid = exc.sqlstate == "23514"
        delivered, attempt = self._sync_attempt(
            name="concurrency:receiver:delivered",
            method="POST",
            path=f"/api/v1/business/orders/{order_id}/mark-delivered",
            headers=self.headers(
                prepared["owner"],
                "47p1_receiver_delivered",
                content_type=True,
            ),
            json={"reason": "Pago movil enviado en prueba local"},
        )
        attempts.append(attempt)
        with connect(self.db_url, row_factory=psycopg.rows.dict_row) as conn:
            receiver_count = conn.execute(
                "select count(*) as total from order_receiver_details where order_id = %s",
                (order_id,),
            ).fetchone()["total"]
            leaked_messages = conn.execute(
                """
                select count(*) as total
                from messages
                where order_id = %s and body like '%%0414%%'
                """,
                (order_id,),
            ).fetchone()["total"]
            events = conn.execute(
                """
                select event_type, count(*) as total
                from order_state_events
                where order_id = %s
                  and event_type in (
                      'payment_confirmed', 'order_delivered'
                  )
                group by event_type
                """,
                (order_id,),
            ).fetchall()
            audit_rows = conn.execute(
                """
                select event_type, count(*) as total
                from audit_logs
                where (
                    resource_type = 'order' and resource_id = %s
                ) or (
                    resource_type = 'order_receiver_details'
                    and resource_id in (
                        select id from order_receiver_details where order_id = %s
                    )
                )
                group by event_type
                """,
                (order_id, order_id),
            ).fetchall()
            jobs = conn.execute(
                "select count(*) as total from notification_jobs where order_id = %s",
                (order_id,),
            ).fetchone()["total"]
        event_counts = {row["event_type"]: int(row["total"]) for row in events}
        audit_counts = {
            row["event_type"]: int(row["total"]) for row in audit_rows
        }
        duration = time.perf_counter() - started_at
        after_resource = _memory_snapshot()
        blocked_code = self._safe_error_code(blocked)
        invalid_code = self._safe_error_code(invalid)
        passed = (
            attempts[0].status_code == 200
            and blocked.status_code == 409
            and blocked_code == "ORDER_RECEIVER_DETAILS_REQUIRED"
            and invalid.status_code == 400
            and invalid_code == "ORDER_RECEIVER_DETAILS_INVALID"
            and valid.status_code == 200
            and reveal.status_code == 200
            and reveal.headers.get("cache-control") == "private, no-store"
            and postgres_rejected_invalid
            and delivered.status_code == 200
            and int(receiver_count) == 1
            and int(leaked_messages) == 0
            and event_counts.get("order_delivered") == 1
            and audit_counts.get("order_receiver_details_shared") == 1
            and audit_counts.get("order_receiver_details_viewed") == 1
        )
        violations = []
        if not postgres_rejected_invalid:
            violations.append("postgres_receiver_constraint_missing")
        if int(leaked_messages):
            violations.append("receiver_details_written_to_chat")
        return self._scenario_record(
            name="receiver_details",
            gate="PRODUCT_GATE",
            attempts=attempts,
            requested_concurrency=1,
            effective_concurrency=1,
            expected_error_codes={
                "ORDER_RECEIVER_DETAILS_REQUIRED",
                "ORDER_RECEIVER_DETAILS_INVALID",
            },
            duration_seconds=duration,
            passed=passed,
            status="PASS" if passed else "FAILED_PRODUCT_GATE",
            postgres_counts={
                "receiver_details": int(receiver_count),
                "receiver_events": event_counts,
                "audit_logs": audit_counts,
                "notification_jobs": int(jobs),
                "chat_value_leaks": int(leaked_messages),
            },
            reservation_counts={},
            invariant_violations=violations,
            resource_usage=_resource_usage(
                before_resource,
                after_resource,
                duration_seconds=duration,
            ),
            details={
                "runtime_invalid_rejected": invalid_code
                == "ORDER_RECEIVER_DETAILS_INVALID",
                "postgres_invalid_rejected": postgres_rejected_invalid,
                "participant_reveal_private_no_store": reveal.headers.get(
                    "cache-control"
                )
                == "private, no-store",
            },
        )

    async def _run_async(self) -> list[dict[str, Any]]:
        admin = self._actor(
            offset=190_101,
            label="47p1_concurrency_admin",
            role="admin",
        )
        scenarios: list[dict[str, Any]] = []
        for level in self.levels:
            scenarios.append(
                await self._same_ad_contention(admin=admin, level=level)
            )
        scenarios.append(
            await self._two_order_race(
                admin=admin,
                label="active_order_limit",
                active_order_limit=1,
                declared_capacity_usd=Decimal("100.00"),
                expected_winners=1,
            )
        )
        scenarios.append(
            await self._two_order_race(
                admin=admin,
                label="shared_capacity_orders",
                active_order_limit=2,
                declared_capacity_usd=Decimal("100.00"),
                expected_winners=2,
            )
        )
        for label, methods, maximum in (
            ("duplicate_zelle", ("zelle", "zelle"), "40.00"),
            ("duplicate_usdt", ("usdt_trc20", "usdt_trc20"), "40.00"),
            ("shared_capacity", ("zelle", "usdt_trc20"), "60.00"),
        ):
            scenarios.append(
                await self._ad_publication_case(
                    admin=admin,
                    label=label,
                    methods=methods,
                    amount_max_usd=maximum,
                )
            )
        scenarios.append(await self._double_delivery_record(admin=admin))
        scenarios.extend(await self._double_transition_records(admin=admin))
        scenarios.append(
            await self._existing_race_record(
                name="payment_vs_cancel",
                runner=lambda: self._payment_cancel_race(admin),
                name_fragment="payment_vs_cancel",
            )
        )
        scenarios.append(
            await self._existing_race_record(
                name="payment_vs_expiration",
                runner=lambda: self._payment_expiration_race(admin),
                name_fragment="payment_vs_expiration",
            )
        )
        scenarios.append(await self._chat_burst(admin=admin))
        scenarios.append(self._receiver_details(admin=admin))
        return scenarios

    async def _run_smoke_async(self) -> list[dict[str, Any]]:
        admin = self._actor(
            offset=190_102,
            label="47p1_smoke_admin",
            role="admin",
        )
        return [
            await self._same_ad_contention(admin=admin, level=level)
            for level in sorted(PRODUCT_GATE_LEVELS)
        ]

    def _build_payload(
        self,
        *,
        mode: str,
        scenarios: list[dict[str, Any]],
        duration: float,
        overall_before: dict[str, Any],
        overall_after: dict[str, Any],
    ) -> dict[str, Any]:
        scenario_by_name = {scenario["scenario"]: scenario for scenario in scenarios}
        violations: list[str] = []
        for level in PRODUCT_GATE_LEVELS:
            scenario = scenario_by_name.get(f"same_ad_contention_c{level}")
            if scenario is None:
                violations.append(f"missing_product_gate_c{level}")
            elif not scenario["passed"]:
                violations.append(f"failed_product_gate_c{level}")
        for scenario in scenarios:
            if scenario["invariant_violations"]:
                violations.extend(
                    f"{scenario['scenario']}:{item}"
                    for item in scenario["invariant_violations"]
                )
            if scenario["gate"] == "PRODUCT_GATE" and not scenario["passed"]:
                marker = f"failed:{scenario['scenario']}"
                if marker not in violations:
                    violations.append(marker)
        payload = {
            "slice": "47P1",
            "phase": "local_load_concurrency_integrity",
            "mode": mode,
            "run_id": self.run_id,
            "environment": {
                "app_env": "local",
                "database": "local_postgresql_disposable",
                "redis": "local_redis",
                "external_providers": False,
            },
            "levels": self.levels,
            "scenarios": scenarios,
            "summary": {
                "product_gates_required": sorted(PRODUCT_GATE_LEVELS),
                "product_gates_passed": all(
                    scenario_by_name.get(f"same_ad_contention_c{level}", {}).get(
                        "passed",
                        False,
                    )
                    for level in PRODUCT_GATE_LEVELS
                ),
                "scenario_count": len(scenarios),
                "passed_count": sum(scenario["passed"] for scenario in scenarios),
                "local_resource_limited_count": sum(
                    scenario["status"] == "LOCAL_RESOURCE_LIMIT"
                    for scenario in scenarios
                ),
                "invariant_violations": violations,
                "duration_seconds": round(duration, 4),
                "resource_usage": _resource_usage(
                    overall_before,
                    overall_after,
                    duration_seconds=duration,
                ),
            },
            "query_families_for_47p3": [
                "order_create_ad_lock_and_capacity_reservation",
                "active_order_limit_under_business_lock",
                "chat_message_insert_and_latest_window",
                "receiver_details_order_lock",
            ],
            "cost": "local_machine_only",
            "exit_code": 1 if violations else 0,
        }
        assert_safe_report(payload)
        return payload

    def _run(self, *, mode: str, runner: Callable[[], Awaitable[list[dict[str, Any]]]]) -> dict[str, Any]:
        overall_before = _memory_snapshot()
        started_at = time.perf_counter()
        scenarios = asyncio.run(runner())
        duration = time.perf_counter() - started_at
        overall_after = _memory_snapshot()
        return self._build_payload(
            mode=mode,
            scenarios=scenarios,
            duration=duration,
            overall_before=overall_before,
            overall_after=overall_after,
        )

    def run_47p1(self) -> dict[str, Any]:
        return self._run(mode="full", runner=self._run_async)

    def run_smoke(self) -> dict[str, Any]:
        return self._run(
            mode="smoke_product_gates",
            runner=self._run_smoke_async,
        )


def write_evidence(
    payload: dict[str, Any],
    *,
    output_path: Path,
    ndjson_path: Path,
) -> None:
    assert_safe_report(payload)
    write_json(output_path, payload)
    write_ndjson(ndjson_path, payload["scenarios"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="run only the real c50/c100 local product gates",
    )
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--levels", type=_parse_levels, default=_parse_levels("50,100,250"))
    parser.add_argument("--chat-orders", type=int, default=10)
    parser.add_argument("--messages-per-order", type=int, default=5)
    parser.add_argument("--run-id", default=f"47p1_{int(time.time())}")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_DIR / "concurrency_47p1.json"),
    )
    parser.add_argument("--ndjson-output", default=None)
    args = parser.parse_args()
    if not 2 <= args.chat_orders <= 25:
        raise SystemExit("--chat-orders must be between 2 and 25")
    if not 1 <= args.messages_per_order <= 20:
        raise SystemExit("--messages-per-order must be between 1 and 20")
    levels = sorted(PRODUCT_GATE_LEVELS) if args.smoke else args.levels
    harness = P2PConcurrency47P1(
        env_file=Path(args.env_file),
        run_id=args.run_id,
        levels=levels,
        chat_orders=args.chat_orders,
        messages_per_order=args.messages_per_order,
    )
    payload = harness.run_smoke() if args.smoke else harness.run_47p1()
    output_path = Path(args.output)
    ndjson_path = (
        Path(args.ndjson_output)
        if args.ndjson_output
        else output_path.with_suffix(".ndjson")
    )
    write_evidence(
        payload,
        output_path=output_path,
        ndjson_path=ndjson_path,
    )
    print(
        json.dumps(
            {
                "slice": payload["slice"],
                "run_id": payload["run_id"],
                "exit_code": payload["exit_code"],
                "product_gates_passed": payload["summary"][
                    "product_gates_passed"
                ],
                "invariant_violation_count": len(
                    payload["summary"]["invariant_violations"]
                ),
                "output": str(output_path),
                "ndjson_output": str(ndjson_path),
            },
            indent=2,
        )
    )
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
