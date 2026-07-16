from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import hmac
import json
import math
import re
import time
import uuid
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import psycopg

from local_hardening_common import DEFAULT_ENV_FILE, MetricsRecorder, add_api_path, write_json
from local_smoke import LocalSmoke
from staging_guardrails import guardrail_payload, require_staging_guardrails

add_api_path()
from app.modules.ads.rules import calculate_required_credits  # noqa: E402
from app.shared.db.connection import connect  # noqa: E402


REQUEST_ERROR_SAMPLE_LIMIT = 100
SENSITIVE_MESSAGE_PATTERNS = (
    "authorization",
    "cookie",
    "access_token",
    "refresh_token",
    "telegram initdata",
    "bot_token",
    "business_intake_bot_token",
    "database_url",
    "redis_url",
    "supabase_service_role_key",
    "jwt_secret",
    "private_key",
    "seed phrase",
    "mnemonic",
    "storage_path",
    "account_value",
    "signed_url",
)


def _base64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _json_dumps(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def create_access_token_at(
    *,
    user_id: str,
    role: str,
    status: str,
    secret: str,
    ttl_seconds: int,
    issued_at: int,
) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "role": role,
        "status": status,
        "iat": issued_at,
        "exp": issued_at + ttl_seconds,
        "jti": str(uuid.uuid4()),
    }
    signing_input = f"{_base64url_encode(_json_dumps(header))}.{_base64url_encode(_json_dumps(payload))}"
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_base64url_encode(signature)}"


def parse_process_time_ms(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value.strip())
    except ValueError:
        return None
    if parsed < 0:
        return None
    return round(parsed, 4)


def parse_server_timing(value: str | None) -> dict[str, float]:
    if not value:
        return {}
    parsed: dict[str, float] = {}
    for item in value.split(","):
        parts = [part.strip() for part in item.split(";") if part.strip()]
        if not parts:
            continue
        metric_name = parts[0]
        duration: float | None = None
        for part in parts[1:]:
            if part.startswith("dur="):
                duration = parse_process_time_ms(part.removeprefix("dur="))
        if duration is not None and metric_name:
            parsed[metric_name] = duration
    return parsed


def classify_request_error(exc: httpx.RequestError) -> str:
    if isinstance(exc, httpx.ConnectTimeout):
        return "CONNECT_TIMEOUT"
    if isinstance(exc, httpx.ConnectError):
        return "CONNECT_ERROR"
    if isinstance(exc, httpx.ReadTimeout):
        return "READ_TIMEOUT"
    if isinstance(exc, httpx.WriteTimeout):
        return "WRITE_TIMEOUT"
    if isinstance(exc, httpx.PoolTimeout):
        return "POOL_TIMEOUT"
    if isinstance(exc, httpx.RemoteProtocolError):
        return "REMOTE_DISCONNECT_OR_PROTOCOL_ERROR"
    if isinstance(exc, httpx.ProtocolError):
        return "PROTOCOL_ERROR"
    return "UNKNOWN_CLIENT_ERROR"


def redact_exception_message(message: str, *, max_length: int = 240) -> str:
    redacted = message.replace("\r", " ").replace("\n", " ")
    redacted = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer <redacted>", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"(https?://[^\s?]+)\?[^\s]+", r"\1?<redacted_query>", redacted, flags=re.IGNORECASE)
    for marker in SENSITIVE_MESSAGE_PATTERNS:
        redacted = re.sub(
            rf"({re.escape(marker)})\s*[:=]\s*[^,\s;]+",
            r"\1=<redacted>",
            redacted,
            flags=re.IGNORECASE,
        )
    if len(redacted) > max_length:
        redacted = f"{redacted[:max_length]}..."
    return redacted


class RealCapacityHarness:
    """Scenario-focused capacity harness.

    This intentionally avoids the legacy business self-onboarding path. It creates a
    prepared internal fixture dataset, then stresses marketplace and order behavior
    separately so order capacity is not hidden behind slow document/admin setup.
    """

    def __init__(
        self,
        *,
        env_file: Path,
        run_id: str,
        businesses: int,
        ads_per_business: int,
        remitters: int,
        marketplace_reads: int,
        order_creates: int,
        same_ad_race_requests: int,
        payment_confirms: int,
        marketplace_concurrency: int | None = None,
        remote_base_url: str | None = None,
        fixture_mode: str | None = None,
        profile_marketplace: bool = False,
        profile_detail_limit: int = 50,
        auth_mode: str = "fresh-claims",
        max_connections: int | None = None,
        fixture_setup_mode: str = "api_ads",
    ) -> None:
        if ads_per_business > 18:
            raise ValueError("ads_per_business must be <= 18 to keep MVP amount ranges valid and non-overlapping")
        if businesses < 1:
            raise ValueError("businesses must be >= 1")
        if math.ceil(max(payment_confirms, 0) / businesses) > 18:
            raise ValueError("payment_confirms per business must be <= 18 to keep MVP amount ranges valid and non-overlapping")
        self.run_id = run_id
        self.business_count = businesses
        self.ads_per_business = ads_per_business
        self.remitter_count = remitters
        self.marketplace_reads = marketplace_reads
        self.order_creates = order_creates
        self.same_ad_race_requests = same_ad_race_requests
        self.payment_confirms = payment_confirms
        self.marketplace_concurrency = marketplace_concurrency or marketplace_reads
        self.remote_base_url = remote_base_url.rstrip("/") if remote_base_url else None
        self.fixture_mode = self._resolve_fixture_mode(fixture_mode)
        self.fixture_setup_mode = self._resolve_fixture_setup_mode(fixture_setup_mode)
        self.guardrails = (
            require_staging_guardrails(
                env_file=env_file,
                run_id=run_id,
                api_base_url=self.remote_base_url,
            )
            if self.remote_base_url
            else None
        )
        self.smoke = LocalSmoke(env_file=env_file, run_id=run_id)
        self.profile_marketplace = profile_marketplace
        self.profile_detail_limit = max(0, profile_detail_limit)
        self.auth_mode = self._resolve_auth_mode(auth_mode)
        self.max_connections = self._resolve_max_connections(max_connections)
        self._direct_ads_created = 0
        self._marketplace_cache_invalidated = False
        self.metrics = MetricsRecorder()
        self.started_at = time.perf_counter()
        self.load_started_at: float | None = None
        self.phase_timings: dict[str, float] = {}
        self.profiled_steps: list[dict[str, Any]] = []
        self.latency_samples: list[dict[str, Any]] = []
        self.request_error_samples: list[dict[str, Any]] = []
        self._request_error_classifications: Counter[str] = Counter()
        self._request_error_endpoints: Counter[str] = Counter()
        self._request_error_groups: Counter[str] = Counter()
        self._backend_process_times: list[float] = []
        self._external_minus_backend: list[float] = []
        self._response_sizes: list[float] = []
        self._server_timing_values: dict[str, list[float]] = defaultdict(list)
        self._profile_stage_values: dict[str, list[float]] = defaultdict(list)
        self._profile_cache_hits: Counter[str] = Counter()
        self._profile_auth_modes: Counter[str] = Counter()
        self._profile_totals: list[float] = []
        self.violations: dict[str, int] = {
            "marketplace_read_errors": 0,
            "order_create_errors": 0,
            "same_ad_success_count_invalid": 0,
            "same_ad_unexpected_status": 0,
            "same_ad_db_rows_invalid": 0,
            "duplicate_idempotency_response_mismatch": 0,
            "duplicate_idempotency_db_rows_invalid": 0,
            "fixture_insufficient_reserved_ads": 0,
            "payment_report_setup_errors": 0,
            "confirm_distinct_errors": 0,
            "confirm_distinct_state_invalid": 0,
            "confirm_same_order_success_count_invalid": 0,
            "confirm_same_order_double_consume": 0,
            "negative_balances": 0,
            "double_credit_consumption": 0,
            "db_errors": 0,
        }

    def _resolve_fixture_mode(self, fixture_mode: str | None) -> str:
        allowed = {"local_asgi", "db_seed_api_remote", "api_remote_only"}
        if fixture_mode is not None and fixture_mode not in allowed:
            raise ValueError(f"fixture_mode must be one of {sorted(allowed)}")
        if self.remote_base_url:
            if fixture_mode is None:
                raise ValueError("--remote-base-url requires explicit --fixture-mode")
            if fixture_mode == "api_remote_only":
                raise ValueError("api_remote_only is blocked: this harness still requires direct DB seed and SQL invariants")
            if fixture_mode != "db_seed_api_remote":
                raise ValueError("remote_base_url only supports fixture_mode=db_seed_api_remote until api_remote_only is implemented")
            return fixture_mode
        if fixture_mode in {None, "local_asgi"}:
            return "local_asgi"
        raise ValueError("fixture_mode with no remote_base_url must be local_asgi")

    @staticmethod
    def _resolve_auth_mode(auth_mode: str) -> str:
        allowed = {"fresh-claims", "fallback-db"}
        if auth_mode not in allowed:
            raise ValueError(f"auth_mode must be one of {sorted(allowed)}")
        return auth_mode

    @staticmethod
    def _resolve_max_connections(max_connections: int | None) -> int | None:
        if max_connections is None:
            return None
        if max_connections < 1:
            raise ValueError("max_connections must be >= 1")
        if max_connections > 1000:
            raise ValueError("max_connections must be <= 1000")
        return max_connections

    @staticmethod
    def _resolve_fixture_setup_mode(fixture_setup_mode: str) -> str:
        allowed = {"api_ads", "db_direct_ads"}
        if fixture_setup_mode not in allowed:
            raise ValueError(f"fixture_setup_mode must be one of {sorted(allowed)}")
        return fixture_setup_mode

    def _client_context(self, *, concurrency: int | None = None) -> httpx.AsyncClient:
        if self.remote_base_url:
            max_connections = self.max_connections or max(20, concurrency or self.marketplace_concurrency)
            return httpx.AsyncClient(
                base_url=self.remote_base_url,
                timeout=30.0,
                limits=httpx.Limits(max_connections=max_connections, max_keepalive_connections=max_connections),
            )
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.smoke.client.app),
            base_url="http://testserver",
        )

    def _fixture_business(self, *, owner: dict[str, Any], admin: dict[str, Any], index: int) -> dict[str, str]:
        self.smoke.set_role(owner["user"]["id"], "business_owner")
        with connect(self.smoke.db_url, row_factory=psycopg.rows.dict_row) as conn:
            owner_row = conn.execute("select telegram_id from users where id = %s", (owner["user"]["id"],)).fetchone()
            if owner_row is None or owner_row["telegram_id"] is None:
                raise RuntimeError("capacity fixture owner does not have telegram_id")
            business = conn.execute(
                """
                insert into businesses (
                    owner_user_id, business_name, rif, address, phone, country,
                    verification_status, trust_level, risk_level,
                    max_order_amount_usd, daily_limit_usd, active_order_limit,
                    approved_at, created_at, updated_at
                )
                values (
                    %s, %s, %s, %s, %s, 'VE',
                    'approved', 'basic', 'normal',
                    100000, 100000, %s,
                    now(), now(), now()
                )
                returning id
                """,
                (
                    owner["user"]["id"],
                    f"Capacity {self.run_id} business {index}",
                    f"J-{index:08d}-9",
                    "Av Capacity 1",
                    "+584121234567",
                    max(self.order_creates + self.same_ad_race_requests + 5, 10),
                ),
            ).fetchone()
            payment_method = conn.execute(
                """
                insert into business_payment_methods (
                    business_id, method_type, network, account_value, account_masked,
                    holder_name, verified_status, active, created_at, updated_at
                )
                values (%s, 'zelle', null, %s, %s, 'Capacity Owner', 'approved', true, now(), now())
                returning id
                """,
                (
                    business["id"],
                    f"capacity_{self.run_id}_{index}@example.local",
                    f"***{index:04d}",
                ),
            ).fetchone()
            usdt_payment_method = conn.execute(
                """
                insert into business_payment_methods (
                    business_id, method_type, network, account_value, account_masked,
                    holder_name, verified_status, active, created_at, updated_at
                )
                values (%s, 'usdt_trc20', 'trc20', %s, %s, 'Capacity Owner', 'approved', true, now(), now())
                returning id
                """,
                (
                    business["id"],
                    f"capacity_{self.run_id}_{index}_trc20_wallet",
                    f"***TRC{index:04d}",
                ),
            ).fetchone()
            conn.execute(
                """
                insert into business_access_links (
                    business_id, user_id, telegram_id_snapshot, role_in_business, status,
                    linked_by_admin_id, linked_at, reason, created_at, updated_at
                )
                values (%s, %s, %s, 'owner', 'active', %s, now(), 'capacity_fixture', now(), now())
                """,
                (business["id"], owner["user"]["id"], owner_row["telegram_id"], admin["user"]["id"]),
            )
            required_credits = 10000
            conn.execute(
                """
                insert into credit_wallets (
                    business_id, available_credits, blocked_credits, consumed_credits,
                    lifetime_adjusted_credits, created_at, updated_at
                )
                values (%s, %s, 0, 0, %s, now(), now())
                on conflict (business_id) do update
                set available_credits = excluded.available_credits,
                    lifetime_adjusted_credits = excluded.lifetime_adjusted_credits,
                    updated_at = now()
                """,
                (business["id"], required_credits, required_credits),
            )
            conn.commit()
        return {
            "business_id": str(business["id"]),
            "payment_method_id": str(payment_method["id"]),
            "usdt_payment_method_id": str(usdt_payment_method["id"]),
        }

    def _create_ad_fixture(
        self,
        *,
        owner: dict[str, Any],
        fixture: dict[str, Any],
        payment_method_id: str,
        payment_method: str,
        business_index: int,
        ad_index: int,
        amount_min: int,
        amount_max: int,
        request_label: str,
    ) -> dict[str, Any]:
        if self.fixture_setup_mode == "db_direct_ads":
            return self._create_ad_fixture_direct_db(
                owner=owner,
                fixture=fixture,
                payment_method_id=payment_method_id,
                payment_method=payment_method,
                business_index=business_index,
                ad_index=ad_index,
                amount_min=amount_min,
                amount_max=amount_max,
            )
        return self._create_ad_fixture_via_api(
            owner=owner,
            payment_method_id=payment_method_id,
            payment_method=payment_method,
            business_index=business_index,
            ad_index=ad_index,
            amount_min=amount_min,
            amount_max=amount_max,
            request_label=request_label,
        )

    def _create_ad_fixture_via_api(
        self,
        *,
        owner: dict[str, Any],
        payment_method_id: str,
        payment_method: str,
        business_index: int,
        ad_index: int,
        amount_min: int,
        amount_max: int,
        request_label: str,
    ) -> dict[str, Any]:
        return self.smoke.request(
            request_label,
            "POST",
            "/api/v1/business/ads",
            headers=self.smoke.headers(owner, f"capacity_ad_{business_index}_{ad_index}", content_type=True),
            json={
                "payment_method_id": payment_method_id,
                "payment_method": payment_method,
                "delivery_method": "pago_movil_ve",
                "rate_bs_per_usd": "39.5000",
                "amount_min_usd": f"{amount_min}.00",
                "amount_max_usd": f"{amount_max}.00",
            },
        )["ad"]

    def _create_ad_fixture_direct_db(
        self,
        *,
        owner: dict[str, Any],
        fixture: dict[str, Any],
        payment_method_id: str,
        payment_method: str,
        business_index: int,
        ad_index: int,
        amount_min: int,
        amount_max: int,
    ) -> dict[str, Any]:
        amount_min_usd = Decimal(f"{amount_min}.00")
        amount_max_usd = Decimal(f"{amount_max}.00")
        required_credits = calculate_required_credits(amount_max_usd)
        business_id = fixture["business_id"]
        with connect(self.smoke.db_url, row_factory=psycopg.rows.dict_row) as conn:
            wallet = conn.execute(
                "select * from credit_wallets where business_id = %s for update",
                (business_id,),
            ).fetchone()
            if wallet is None or wallet["available_credits"] < required_credits:
                conn.rollback()
                raise RuntimeError("capacity direct ad fixture has insufficient credits")
            ad = conn.execute(
                """
                insert into ads (
                    business_id, payment_method_id, payment_method, delivery_method,
                    rate_bs_per_usd, amount_min_usd, amount_max_usd, required_credits,
                    status, activated_at, expires_at, last_rate_updated_at, created_at, updated_at
                )
                values (%s, %s, %s, 'pago_movil_ve', 39.5000, %s, %s, %s,
                    'active', now(), now() + interval '7 days', now(), now(), now())
                returning *
                """,
                (business_id, payment_method_id, payment_method, amount_min_usd, amount_max_usd, required_credits),
            ).fetchone()
            available_after = wallet["available_credits"] - required_credits
            blocked_after = wallet["blocked_credits"] + required_credits
            conn.execute(
                """
                update credit_wallets
                set available_credits = %s, blocked_credits = %s, updated_at = now()
                where business_id = %s
                """,
                (available_after, blocked_after, business_id),
            )
            ledger = conn.execute(
                """
                insert into credits_ledger (
                    business_id, type, amount, available_before, available_after,
                    blocked_before, blocked_after, consumed_before, consumed_after,
                    related_ad_id, reason, source, reference_type, reference_id, created_by, created_at
                )
                values (%s, 'hold', %s, %s, %s, %s, %s, %s, %s, %s,
                    'ad_publish_credit_hold', 'ads', 'ad', %s, %s, now())
                returning id
                """,
                (
                    business_id,
                    required_credits,
                    wallet["available_credits"],
                    available_after,
                    wallet["blocked_credits"],
                    blocked_after,
                    wallet["consumed_credits"],
                    wallet["consumed_credits"],
                    ad["id"],
                    ad["id"],
                    owner["user"]["id"],
                ),
            ).fetchone()
            ad = conn.execute(
                "update ads set credit_hold_ledger_id = %s, updated_at = now() where id = %s returning *",
                (ledger["id"], ad["id"]),
            ).fetchone()
            conn.commit()
        self._direct_ads_created += 1
        self.smoke.steps.append(
            {
                "name": "fixture:ad_direct_db",
                "business_index": business_index,
                "ad_index": ad_index,
                "payment_method": payment_method,
                "required_credits": required_credits,
                "status_code": 200,
            }
        )
        return {
            "id": str(ad["id"]),
            "business_id": str(ad["business_id"]),
            "payment_method_id": str(ad["payment_method_id"]),
            "payment_method": ad["payment_method"],
            "delivery_method": ad["delivery_method"],
            "rate_bs_per_usd": str(ad["rate_bs_per_usd"]),
            "amount_min_usd": str(ad["amount_min_usd"]),
            "amount_max_usd": str(ad["amount_max_usd"]),
            "required_credits": int(ad["required_credits"]),
            "status": ad["status"],
        }

    def _invalidate_marketplace_cache_after_direct_ads(self) -> None:
        if self._direct_ads_created <= 0:
            return
        cache = getattr(self.smoke.client.app.state, "marketplace_cache", None)
        if cache is None or not hasattr(cache, "clear_prefix"):
            self.smoke.steps.append(
                {
                    "name": "fixture:marketplace_cache_invalidate_skipped",
                    "direct_ads_created": self._direct_ads_created,
                    "status_code": 200,
                }
            )
            return
        cache.clear_prefix("")
        self._marketplace_cache_invalidated = True
        self.smoke.steps.append(
            {
                "name": "fixture:marketplace_cache_invalidate",
                "direct_ads_created": self._direct_ads_created,
                "status_code": 200,
            }
        )

    def prepare_dataset(self) -> dict[str, Any]:
        admin = self.smoke.fixture_login(self.smoke.synthetic_telegram_id(510000), "capacity_admin", role="admin")
        owners = [
            self.smoke.fixture_login(
                self.smoke.synthetic_telegram_id(520000 + index),
                f"capacity_owner_{index}",
                role="business_owner",
            )
            for index in range(self.business_count)
        ]
        remitters = [
            self.smoke.fixture_login(self.smoke.synthetic_telegram_id(530000 + index), f"capacity_remitter_{index}")
            for index in range(max(self.remitter_count, self.same_ad_race_requests, 1))
        ]
        businesses: list[dict[str, Any]] = []
        ads: list[dict[str, Any]] = []
        payment_ads: list[dict[str, Any]] = []
        for business_index, owner in enumerate(owners):
            fixture = self._fixture_business(owner=owner, admin=admin, index=business_index)
            business_ads = []
            for ad_index in range(self.ads_per_business):
                slot = ad_index
                amount_min = 20 + slot * 100
                amount_max = 100 + slot * 100
                ad = self._create_ad_fixture(
                    owner=owner,
                    fixture=fixture,
                    payment_method_id=fixture["payment_method_id"],
                    payment_method="zelle",
                    business_index=business_index,
                    ad_index=ad_index,
                    amount_min=amount_min,
                    amount_max=amount_max,
                    request_label=f"capacity:ads:create:{business_index}:{ad_index}",
                )
                ad["capacity_amount_usd"] = f"{amount_min + 30}.00"
                ads.append(ad)
                business_ads.append(ad)
            businesses.append({"owner": owner, **fixture, "ads": business_ads, "payment_ads": []})
        payment_ads_needed = self.payment_confirms + (1 if self.payment_confirms else 0)
        per_business_payment_slot: dict[int, int] = {}
        for payment_index in range(payment_ads_needed):
            business_index = payment_index % len(businesses)
            business = businesses[business_index]
            owner = business["owner"]
            slot = per_business_payment_slot.get(business_index, 0)
            per_business_payment_slot[business_index] = slot + 1
            amount_min = 20 + slot * 100
            amount_max = 100 + slot * 100
            ad = self._create_ad_fixture(
                owner=owner,
                fixture=business,
                payment_method_id=business["usdt_payment_method_id"],
                payment_method="usdt_trc20",
                business_index=business_index,
                ad_index=slot,
                amount_min=amount_min,
                amount_max=amount_max,
                request_label=f"capacity:payment_ads:create:{business_index}:{slot}",
            )
            ad["capacity_amount_usd"] = f"{amount_min + 30}.00"
            ad["capacity_business_index"] = business_index
            payment_ads.append(ad)
            business["payment_ads"].append(ad)
        self._invalidate_marketplace_cache_after_direct_ads()
        return {"admin": admin, "businesses": businesses, "ads": ads, "payment_ads": payment_ads, "remitters": remitters}

    def _ensure_request_observability_headers(self, *, name: str, method: str, path: str, kwargs: dict[str, Any]) -> dict[str, str]:
        headers = dict(kwargs.get("headers") or {})
        slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower() or "request"
        headers.setdefault("X-Request-Id", f"req_{self.run_id}_{slug}_{uuid.uuid4().hex[:8]}")
        headers.setdefault("X-Correlation-Id", f"corr_{self.run_id}")
        headers.setdefault("X-NODO-Operation-Id", f"op_{self.run_id}_{slug}")
        headers.setdefault("X-NODO-Surface", self._surface_for_request(name=name, method=method, path=path))
        kwargs["headers"] = headers
        return headers

    @staticmethod
    def _surface_for_request(*, name: str, method: str, path: str) -> str:
        if path.startswith("/api/v1/admin"):
            return "admin_web"
        if path.startswith("/api/v1/business") or name.startswith("capacity:business_orders"):
            return "business_mini_app"
        return "client_mini_app"

    async def _request(self, client: httpx.AsyncClient, name: str, method: str, url: str, **kwargs: Any) -> httpx.Response:
        started = time.perf_counter()
        normalized_method = method.upper()
        path = url.split("?", 1)[0]
        route_group = f"{normalized_method} {path}"
        request_headers = self._ensure_request_observability_headers(name=name, method=normalized_method, path=path, kwargs=kwargs)
        try:
            response = await client.request(method, url, **kwargs)
        except httpx.RequestError as exc:
            latency_ms = self.metrics.record(name, 599, started, route_group=route_group)
            self._record_latency_sample(
                name=name,
                method=normalized_method,
                path=path,
                status_code=599,
                external_duration_ms=latency_ms,
                response=None,
                request_headers=request_headers,
            )
            self._record_request_error(
                name=name,
                method=normalized_method,
                path=path,
                status_code=599,
                external_duration_ms=latency_ms,
                exc=exc,
                request_headers=request_headers,
            )
            request = httpx.Request(normalized_method, str(client.base_url).rstrip("/") + url)
            return httpx.Response(
                599,
                json={"error": {"code": type(exc).__name__, "message": "remote_request_failed"}},
                request=request,
            )
        latency_ms = self.metrics.record(name, response.status_code, started, route_group=route_group)
        self._record_latency_sample(
            name=name,
            method=normalized_method,
            path=path,
            status_code=response.status_code,
            external_duration_ms=latency_ms,
            response=response,
            request_headers=request_headers,
        )
        try:
            body = response.json()
        except ValueError:
            body = {}
        data = body.get("data") if isinstance(body, dict) else None
        if isinstance(data, dict) and "_profile" in data:
            self._record_profile(name=name, method=normalized_method, path=path, status_code=response.status_code, profile=data["_profile"])
        return response

    def _record_request_error(
        self,
        *,
        name: str,
        method: str,
        path: str,
        status_code: int,
        external_duration_ms: float,
        exc: httpx.RequestError,
        request_headers: dict[str, str],
    ) -> None:
        classification = classify_request_error(exc)
        endpoint = f"{method} {path}"
        self._request_error_classifications[classification] += 1
        self._request_error_endpoints[endpoint] += 1
        self._request_error_groups[name] += 1
        if len(self.request_error_samples) >= REQUEST_ERROR_SAMPLE_LIMIT:
            return
        self.request_error_samples.append(
            {
                "method": method,
                "endpoint": path,
                "group": name,
                "request_id": request_headers.get("X-Request-Id"),
                "correlation_id": request_headers.get("X-Correlation-Id"),
                "operation_id": request_headers.get("X-NODO-Operation-Id"),
                "surface": request_headers.get("X-NODO-Surface"),
                "status": status_code,
                "exception_class": type(exc).__name__,
                "exception_message_redacted": redact_exception_message(str(exc)),
                "elapsed_ms": round(external_duration_ms, 4),
                "response_started": False,
                "classification": classification,
            }
        )

    def _record_latency_sample(
        self,
        *,
        name: str,
        method: str,
        path: str,
        status_code: int,
        external_duration_ms: float,
        response: httpx.Response | None,
        request_headers: dict[str, str] | None = None,
    ) -> None:
        process_time_ms = parse_process_time_ms(response.headers.get("X-NODO-Process-Time-Ms")) if response is not None else None
        server_timing = parse_server_timing(response.headers.get("Server-Timing")) if response is not None else {}
        backend_time_ms = process_time_ms
        if backend_time_ms is None and "app" in server_timing:
            backend_time_ms = server_timing["app"]
        if backend_time_ms is not None:
            self._backend_process_times.append(backend_time_ms)
            self._external_minus_backend.append(round(max(0.0, external_duration_ms - backend_time_ms), 4))
        for metric_name, duration in server_timing.items():
            self._server_timing_values[metric_name].append(duration)
        response_size = float(len(response.content)) if response is not None else 0.0
        self._response_sizes.append(response_size)
        if len(self.latency_samples) < self.profile_detail_limit:
            headers = response.headers if response is not None else {}
            request_headers = request_headers or {}
            self.latency_samples.append(
                {
                    "name": name,
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "external_duration_ms": round(external_duration_ms, 4),
                    "backend_process_ms": backend_time_ms,
                    "external_minus_backend_ms": (
                        round(max(0.0, external_duration_ms - backend_time_ms), 4) if backend_time_ms is not None else None
                    ),
                    "server_timing": server_timing,
                    "request_id": headers.get("X-Request-Id") or request_headers.get("X-Request-Id"),
                    "correlation_id": headers.get("X-Correlation-Id") or request_headers.get("X-Correlation-Id"),
                    "operation_id": headers.get("X-NODO-Operation-Id") or request_headers.get("X-NODO-Operation-Id"),
                    "response_size_bytes": int(response_size),
                }
            )

    def _record_profile(self, *, name: str, method: str, path: str, status_code: int, profile: dict[str, Any]) -> None:
        total_ms = profile.get("total_ms")
        if isinstance(total_ms, (int, float)):
            self._profile_totals.append(float(total_ms))
        dependency = profile.get("dependency")
        if isinstance(dependency, dict):
            auth = dependency.get("auth")
            if isinstance(auth, dict):
                mode = auth.get("mode")
                if isinstance(mode, str):
                    self._profile_auth_modes[mode] += 1
                for stage in auth.get("stages", []):
                    self._record_profile_stage(stage)
        for stage in profile.get("stages", []):
            self._record_profile_stage(stage)
        if len(self.profiled_steps) < self.profile_detail_limit:
            self.profiled_steps.append(
                {
                    "name": name,
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "profile": profile,
                }
            )

    def _record_profile_stage(self, stage: Any) -> None:
        if not isinstance(stage, dict):
            return
        name = stage.get("stage")
        elapsed = stage.get("elapsed_ms")
        if isinstance(name, str) and isinstance(elapsed, (int, float)):
            self._profile_stage_values[name].append(float(elapsed))
        metadata = stage.get("metadata")
        if name == "cache:hit" and isinstance(metadata, dict):
            hit_type = metadata.get("hit_type")
            if isinstance(hit_type, str):
                self._profile_cache_hits[hit_type] += 1

    @staticmethod
    def _percentiles(values: list[float]) -> dict[str, float | int]:
        if not values:
            return {"count": 0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}
        ordered = sorted(values)

        def pct(percent: float) -> float:
            index = min(len(ordered) - 1, max(0, math.ceil((percent / 100.0) * len(ordered)) - 1))
            return round(ordered[index], 4)

        return {"count": len(values), "p50_ms": pct(50), "p95_ms": pct(95), "p99_ms": pct(99)}

    def profile_summary(self) -> dict[str, Any]:
        stages = {stage: self._percentiles(values) for stage, values in sorted(self._profile_stage_values.items())}
        return {
            "enabled": self.profile_marketplace,
            "captured_profiles": len(self._profile_totals),
            "raw_profile_limit": self.profile_detail_limit,
            "route_total": self._percentiles(self._profile_totals),
            "stages": stages,
            "cache_hit_counts": dict(self._profile_cache_hits),
            "auth_mode_counts": dict(self._profile_auth_modes),
            "db_acquire_p95_ms": stages.get("db:acquire", {}).get("p95_ms", 0.0),
            "db_query_p95_ms": stages.get("db:query:list_marketplace_ads_with_businesses", {}).get("p95_ms", 0.0),
            "route_total_p95_ms": self._percentiles(self._profile_totals)["p95_ms"],
        }

    def latency_isolation_summary(self) -> dict[str, Any]:
        metrics_summary = self.metrics.summary(started_at=self.load_started_at or self.started_at)
        return {
            "enabled": True,
            "sample_limit": self.profile_detail_limit,
            "external": {
                "all_requests": {
                    "p50_ms": metrics_summary["p50_ms"],
                    "p95_ms": metrics_summary["p95_ms"],
                    "p99_ms": metrics_summary["p99_ms"],
                    "count": metrics_summary["total_requests"],
                },
                "route_groups": metrics_summary["route_groups"],
            },
            "backend_process": self._percentiles(self._backend_process_times),
            "external_minus_backend": self._percentiles(self._external_minus_backend),
            "server_timing": {
                metric: self._percentiles(values) for metric, values in sorted(self._server_timing_values.items())
            },
            "response_size_bytes": self._percentiles(self._response_sizes),
            "profile": self.profile_summary(),
        }

    def request_error_summary(self) -> dict[str, Any]:
        return {
            "total": sum(self._request_error_classifications.values()),
            "sample_limit": REQUEST_ERROR_SAMPLE_LIMIT,
            "by_classification": dict(self._request_error_classifications),
            "by_endpoint": dict(self._request_error_endpoints),
            "by_group": dict(self._request_error_groups),
        }

    async def run_marketplace_reads(self, prepared: dict[str, Any]) -> dict[str, Any]:
        remitters = self._fresh_fixture_logins(prepared["remitters"])
        remitters = [self._marketplace_auth_login(login) for login in remitters]
        prepared["remitters"] = remitters
        client_context = self._client_context(concurrency=max(100, self.marketplace_concurrency))
        semaphore = asyncio.Semaphore(max(1, self.marketplace_concurrency))

        async def search(index: int) -> httpx.Response:
            async with semaphore:
                headers = self.smoke.bearer(remitters[index % len(remitters)], f"capacity_search_{index}")
                if self.profile_marketplace:
                    headers["X-NODO-Profile"] = "1"
                return await self._request(
                    client,
                    "capacity:marketplace:read",
                    "GET",
                    f"/api/v1/ads/search?amount_usd={50 + ((index % self.ads_per_business) * 100)}.00&payment_method=zelle&delivery_method=pago_movil_ve&limit=20",
                    headers=headers,
                )

        async with client_context as client:
            responses = await asyncio.gather(*[search(index) for index in range(self.marketplace_reads)])
        self.violations["marketplace_read_errors"] = sum(1 for response in responses if response.status_code >= 400)
        return {"status_codes": [response.status_code for response in responses]}

    def _marketplace_auth_login(self, login: dict[str, Any]) -> dict[str, Any]:
        if self.auth_mode == "fresh-claims":
            return login
        user = login.get("user")
        if not isinstance(user, dict):
            raise RuntimeError("fallback-db auth mode requires user payload in fixture login")
        settings = self.smoke.client.app.state.settings
        if not settings.jwt_secret:
            raise RuntimeError("fallback-db auth mode requires JWT_SECRET")
        claim_ttl = int(getattr(settings, "marketplace_read_auth_claim_ttl_seconds", 0) or 0)
        access_ttl = max(int(getattr(settings, "access_token_ttl_seconds", 0) or 0), claim_ttl + 600, 900)
        issued_at = int(time.time()) - max(claim_ttl + 60, 120)
        stale_login = dict(login)
        stale_login["access_token"] = create_access_token_at(
            user_id=str(user["id"]),
            role=str(user["role"]),
            status=str(user["status"]),
            secret=settings.jwt_secret,
            ttl_seconds=access_ttl,
            issued_at=issued_at,
        )
        stale_login["expires_in"] = access_ttl
        stale_login["_issued_monotonic"] = time.perf_counter()
        stale_login["_capacity_auth_mode"] = "fallback-db"
        return stale_login

    def _fresh_fixture_logins(self, logins: list[dict[str, Any]]) -> list[dict[str, Any]]:
        refreshed: list[dict[str, Any]] = []
        for index, login in enumerate(logins):
            telegram_id = login.get("_fixture_telegram_id")
            username = login.get("_fixture_username")
            role = login.get("_fixture_role", "remitter")
            if isinstance(telegram_id, int) and isinstance(username, str):
                refreshed.append(self.smoke.fixture_login(telegram_id, f"{username}_fresh_{index}", role=str(role)))
            else:
                refreshed.append(login)
        return refreshed

    def _order_flow_ads(self, prepared: dict[str, Any]) -> list[dict[str, Any]]:
        # Keep two untouched ads reserved for the race/idempotency scenarios.
        return prepared["ads"][: max(0, len(prepared["ads"]) - 2)]

    async def run_order_creates(self, prepared: dict[str, Any]) -> dict[str, Any]:
        available_ads = self._order_flow_ads(prepared)
        ads = available_ads[: self.order_creates]
        if len(ads) < self.order_creates:
            self.violations["fixture_insufficient_reserved_ads"] += 1
        remitters = prepared["remitters"]
        async with self._client_context(concurrency=max(1, len(ads))) as client:
            responses = await asyncio.gather(
                *[
                    self._request(
                        client,
                        "capacity:orders:create_distinct",
                        "POST",
                        "/api/v1/orders",
                        headers=self.smoke.headers(remitters[index % len(remitters)], f"capacity_order_{index}", content_type=True),
                        json={
                            "ad_id": ad["id"],
                            "amount_usd": ad["capacity_amount_usd"],
                            "receiver_data": {
                                "bank": "Banco Local",
                                "phone": "+584121234567",
                                "document": f"V{index:08d}",
                                "holder": f"Capacity Receiver {index}",
                            },
                        },
                    )
                    for index, ad in enumerate(ads)
                ]
            )
        self.violations["order_create_errors"] = sum(1 for response in responses if response.status_code >= 400)
        return {
            "status_codes": [response.status_code for response in responses],
            "attempted": len(ads),
            "requested": self.order_creates,
            "reserved_for_race": 2,
        }

    async def run_same_ad_race(self, prepared: dict[str, Any]) -> dict[str, Any]:
        if len(prepared["ads"]) < 2:
            self.violations["fixture_insufficient_reserved_ads"] += 1
            return {"status_codes": [], "successful_ids": []}
        race_ad = prepared["ads"][-2]
        remitters = prepared["remitters"]
        async with self._client_context(concurrency=max(1, self.same_ad_race_requests)) as client:
            responses = await asyncio.gather(
                *[
                    self._request(
                        client,
                        "capacity:orders:same_ad_race",
                        "POST",
                        "/api/v1/orders",
                        headers=self.smoke.headers(remitters[index % len(remitters)], f"capacity_same_ad_{index}", content_type=True),
                        json={
                            "ad_id": race_ad["id"],
                            "amount_usd": race_ad["capacity_amount_usd"],
                            "receiver_data": {
                                "bank": "Banco Local",
                                "phone": "+584121234567",
                                "document": f"R{index:08d}",
                                "holder": f"Race Receiver {index}",
                            },
                        },
                    )
                    for index in range(self.same_ad_race_requests)
                ]
            )
        successful_ids = [
            response.json()["data"]["order"]["id"]
            for response in responses
            if response.status_code < 400
        ]
        if len(successful_ids) != 1:
            self.violations["same_ad_success_count_invalid"] += 1
        unexpected_statuses = [
            response.status_code
            for response in responses
            if response.status_code not in {201, 409}
        ]
        if unexpected_statuses:
            self.violations["same_ad_unexpected_status"] += len(unexpected_statuses)
        with connect(self.smoke.db_url, row_factory=psycopg.rows.dict_row) as conn:
            rows = conn.execute("select count(*) as count from orders where ad_id = %s", (race_ad["id"],)).fetchone()["count"]
        if int(rows) != 1:
            self.violations["same_ad_db_rows_invalid"] += 1
        return {"status_codes": [response.status_code for response in responses], "successful_ids": successful_ids, "unexpected_statuses": unexpected_statuses, "db_rows": int(rows)}

    async def run_duplicate_idempotency_race(self, prepared: dict[str, Any]) -> dict[str, Any]:
        if len(prepared["ads"]) < 2:
            self.violations["fixture_insufficient_reserved_ads"] += 1
            return {"status_codes": [], "successful_ids": []}
        duplicate_ad = prepared["ads"][-1]
        remitter = prepared["remitters"][0]
        duplicate_key = f"{self.run_id}_capacity_duplicate_order_key"
        stored_idempotency_key = f"{self.run_id}_{duplicate_key}"
        duplicate_requests = max(2, min(self.same_ad_race_requests, 25))
        async with self._client_context(concurrency=duplicate_requests) as client:
            responses = await asyncio.gather(
                *[
                    self._request(
                        client,
                        "capacity:orders:duplicate_idempotency",
                        "POST",
                        "/api/v1/orders",
                        headers={
                            **self.smoke.headers(remitter, duplicate_key, content_type=True),
                            "X-Request-Id": f"req_{self.run_id}_capacity_duplicate_{index}",
                        },
                        json={
                            "ad_id": duplicate_ad["id"],
                            "amount_usd": duplicate_ad["capacity_amount_usd"],
                            "receiver_data": {
                                "bank": "Banco Local",
                                "phone": "+584121234567",
                                "document": "D99990000",
                                "holder": "Duplicate Capacity Receiver",
                            },
                        },
                    )
                    for index in range(duplicate_requests)
                ]
            )
        successful_ids = [
            response.json()["data"]["order"]["id"]
            for response in responses
            if response.status_code < 400
        ]
        if len(set(successful_ids)) > 1:
            self.violations["duplicate_idempotency_response_mismatch"] += 1
        with connect(self.smoke.db_url, row_factory=psycopg.rows.dict_row) as conn:
            rows = conn.execute(
                "select count(*) as count from orders where remitter_user_id = %s and idempotency_key = %s",
                (remitter["user"]["id"], stored_idempotency_key),
            ).fetchone()["count"]
        if int(rows) != 1:
            self.violations["duplicate_idempotency_db_rows_invalid"] += 1
        return {"status_codes": [response.status_code for response in responses], "successful_ids": successful_ids, "db_rows": int(rows)}

    def _prepare_payment_reported_orders(self, prepared: dict[str, Any]) -> list[dict[str, Any]]:
        orders: list[dict[str, Any]] = []
        remitters = prepared["remitters"]
        payment_ads = prepared.get("payment_ads", [])
        for index, ad in enumerate(payment_ads[: self.payment_confirms + 1]):
            remitter = remitters[index % len(remitters)]
            order = self.smoke.request(
                f"capacity:payment_orders:create:{index}",
                "POST",
                "/api/v1/orders",
                headers=self.smoke.headers(remitter, f"capacity_payment_order_{index}", content_type=True),
                json={
                    "ad_id": ad["id"],
                    "amount_usd": ad["capacity_amount_usd"],
                    "receiver_data": {
                        "bank": "Banco Local",
                        "phone": "+584121234567",
                        "document": f"P{index:08d}",
                        "holder": f"Payment Receiver {index}",
                    },
                },
            )["order"]
            report = self.smoke.request(
                f"capacity:payment_report:usdt:{index}",
                "POST",
                f"/api/v1/orders/{order['id']}/payment-report",
                headers=self.smoke.headers(remitter, f"capacity_payment_report_{index}", content_type=True),
                json={
                    "payment_type": "usdt_trc20",
                    "tx_hash": f"0x{self.run_id.replace('-', '')[:16]}{index:08d}abcdef",
                    "network": "TRC20",
                    "payment_amount": ad["capacity_amount_usd"],
                },
            )
            if report.get("order", {}).get("status") != "payment_reported":
                self.violations["payment_report_setup_errors"] += 1
            business = prepared["businesses"][ad["capacity_business_index"]]
            orders.append({"order": report["order"], "ad": ad, "owner": business["owner"], "remitter": remitter})
        if len(orders) < self.payment_confirms + (1 if self.payment_confirms else 0):
            self.violations["payment_report_setup_errors"] += 1
        return orders

    async def run_confirm_distinct(self, prepared: dict[str, Any]) -> dict[str, Any]:
        if self.payment_confirms <= 0:
            return {"status_codes": [], "attempted": 0}
        reported_orders = self._prepare_payment_reported_orders(prepared)
        distinct = reported_orders[: self.payment_confirms]
        async with self._client_context(concurrency=max(1, len(distinct))) as client:
            responses = await asyncio.gather(
                *[
                    self._request(
                        client,
                        "capacity:business_orders:confirm_distinct",
                        "POST",
                        f"/api/v1/business/orders/{item['order']['id']}/confirm-payment",
                        headers=self.smoke.headers(item["owner"], f"capacity_confirm_distinct_{index}", content_type=True),
                        json={"reason": "Capacity confirm distinct"},
                    )
                    for index, item in enumerate(distinct)
                ]
            )
        self.violations["confirm_distinct_errors"] = sum(1 for response in responses if response.status_code >= 400)
        order_ids = [item["order"]["id"] for item in distinct]
        with connect(self.smoke.db_url, row_factory=psycopg.rows.dict_row) as conn:
            rows = conn.execute(
                """
                select
                    count(*) filter (where o.status = 'payment_confirmed') as confirmed_orders,
                    count(distinct o.id) as total_orders,
                    count(*) filter (where a.status = 'archived') as archived_ads,
                    (
                        select count(*)
                        from credits_ledger cl
                        where cl.type = 'consume' and cl.related_order_id = any(%s)
                    ) as consume_rows
                from orders o
                join ads a on a.id = o.ad_id
                where o.id = any(%s)
                """,
                (order_ids, order_ids),
            ).fetchone()
        expected = len(distinct)
        if any(int(rows[key]) != expected for key in ("confirmed_orders", "total_orders", "archived_ads", "consume_rows")):
            self.violations["confirm_distinct_state_invalid"] += 1
        same_order_result = await self.run_confirm_same_order_race(reported_orders[-1]) if len(reported_orders) > self.payment_confirms else {"status_codes": [], "successful_ids": [], "consume_rows": 0}
        return {
            "status_codes": [response.status_code for response in responses],
            "attempted": len(distinct),
            "db_state": {key: int(rows[key]) for key in ("confirmed_orders", "total_orders", "archived_ads", "consume_rows")},
            "same_order_race": same_order_result,
        }

    async def run_confirm_same_order_race(self, item: dict[str, Any]) -> dict[str, Any]:
        requests = max(2, min(self.same_ad_race_requests, 25))
        async with self._client_context(concurrency=requests) as client:
            responses = await asyncio.gather(
                *[
                    self._request(
                        client,
                        "capacity:business_orders:confirm_same_order_race",
                        "POST",
                        f"/api/v1/business/orders/{item['order']['id']}/confirm-payment",
                        headers=self.smoke.headers(item["owner"], f"capacity_confirm_same_order_{index}", content_type=True),
                        json={"reason": "Capacity same order race"},
                    )
                    for index in range(requests)
                ]
            )
        successful_ids = [
            response.json()["data"]["order"]["id"]
            for response in responses
            if response.status_code < 400
        ]
        if len(successful_ids) != 1:
            self.violations["confirm_same_order_success_count_invalid"] += 1
        with connect(self.smoke.db_url, row_factory=psycopg.rows.dict_row) as conn:
            row = conn.execute(
                """
                select
                    (select count(*) from credits_ledger where type = 'consume' and related_order_id = %s) as consume_rows,
                    (select status from orders where id = %s) as order_status,
                    (select status from ads where id = %s) as ad_status
                """,
                (item["order"]["id"], item["order"]["id"], item["ad"]["id"]),
            ).fetchone()
        if int(row["consume_rows"]) != 1:
            self.violations["confirm_same_order_double_consume"] += 1
        return {
            "status_codes": [response.status_code for response in responses],
            "successful_ids": successful_ids,
            "consume_rows": int(row["consume_rows"]),
            "order_status": row["order_status"],
            "ad_status": row["ad_status"],
        }

    def scan_invariants(self) -> dict[str, int]:
        with connect(self.smoke.db_url, row_factory=psycopg.rows.dict_row) as conn:
            negative_balances = conn.execute(
                "select count(*) as count from credit_wallets where available_credits < 0 or blocked_credits < 0 or consumed_credits < 0"
            ).fetchone()["count"]
            duplicate_consumes = conn.execute(
                """
                select count(*) as count
                from (
                    select related_order_id
                    from credits_ledger
                    where type = 'consume' and related_order_id is not null
                    group by related_order_id
                    having count(*) > 1
                ) x
                """
            ).fetchone()["count"]
        self.violations["negative_balances"] = int(negative_balances)
        self.violations["double_credit_consumption"] = int(duplicate_consumes)
        return {"negative_balances": int(negative_balances), "double_credit_consumption": int(duplicate_consumes)}

    def run(self, scenario: str) -> dict[str, Any]:
        setup_started = time.perf_counter()
        prepared = self.prepare_dataset()
        self.phase_timings["setup_seconds"] = round(time.perf_counter() - setup_started, 4)
        self.load_started_at = time.perf_counter()
        details: dict[str, Any] = {}
        if scenario in {"all", "marketplace-reads"}:
            details["marketplace_reads"] = asyncio.run(self.run_marketplace_reads(prepared))
        if scenario in {"all", "order-flow"}:
            details["order_flow"] = asyncio.run(self.run_order_creates(prepared))
        if scenario in {"all", "order-race"}:
            details["same_ad_race"] = asyncio.run(self.run_same_ad_race(prepared))
            details["duplicate_idempotency_race"] = asyncio.run(self.run_duplicate_idempotency_race(prepared))
        if scenario in {"all", "payment-confirm"}:
            details["payment_confirm"] = asyncio.run(self.run_confirm_distinct(prepared))
        self.phase_timings["measured_load_seconds"] = round(time.perf_counter() - self.load_started_at, 4)
        invariants_started = time.perf_counter()
        details["invariants"] = self.scan_invariants()
        self.phase_timings["invariants_seconds"] = round(time.perf_counter() - invariants_started, 4)
        self.phase_timings["total_seconds"] = round(time.perf_counter() - self.started_at, 4)
        summary = self.metrics.summary(started_at=self.load_started_at)
        exit_code = 1 if any(self.violations.values()) else 0
        return {
            "slice": "real_services_capacity_hardening",
            "phase": "scenario_capacity",
            "run_id": self.run_id,
            "scenario": scenario,
            "fixture_mode": self.fixture_mode,
            "fixture_setup_mode": self.fixture_setup_mode,
            "auth_mode": self.auth_mode,
            "fixture_mode_detail": {
                "local_asgi": {
                    "seed": "local_asgi_internal_fixture_dataset",
                    "measured_requests": "local_asgi",
                    "invariants": "direct_db_sql",
                },
                "db_seed_api_remote": {
                    "seed": "hybrid_direct_db_seed_plus_configurable_ad_setup",
                    "measured_requests": "remote_api",
                    "invariants": "direct_db_sql",
                    "api_remote_only": False,
                    "setup_note": {
                        "api_ads": "Users/businesses/access/wallet fixtures use direct DB helpers, but ad and payment-order setup still exercises app APIs before measured load.",
                        "db_direct_ads": "Users/businesses/access/wallet/ad fixtures use direct DB helpers with marketplace shared-cache invalidation; payment-order setup still exercises app APIs before measured load.",
                    }[self.fixture_setup_mode],
                },
            }[self.fixture_mode],
            "fixture_setup": {
                "ad_setup": self.fixture_setup_mode,
                "direct_ads_created": self._direct_ads_created,
                "marketplace_cache_invalidated": self._marketplace_cache_invalidated,
                "payment_order_setup": "api",
            },
            "client": {
                "max_connections": self.max_connections,
                "max_connections_effective": self.max_connections or "max(20, scenario_concurrency)",
                "timeout_seconds": 30.0 if self.remote_base_url else None,
            },
            "phase_timings": self.phase_timings,
            "staging_guardrails": guardrail_payload(self.guardrails) if self.guardrails else None,
            "request_target": self.remote_base_url or "local_asgi_testclient",
            "cleanup": {
                "required": bool(self.remote_base_url),
                "run_id": self.run_id,
                "recommended_command": (
                    f"python scripts\\staging_cleanup_synthetic_run.py --env-file <staging-env> --run-id {self.run_id} --output evidence\\slice_runs\\cleanup_{self.run_id}.json"
                    if self.remote_base_url
                    else None
                ),
            },
            "targets": {
                "businesses": self.business_count,
                "ads_per_business": self.ads_per_business,
                "remitters": self.remitter_count,
                "marketplace_reads": self.marketplace_reads,
                "marketplace_concurrency": self.marketplace_concurrency,
                "order_creates": self.order_creates,
                "same_ad_race_requests": self.same_ad_race_requests,
                "payment_confirms": self.payment_confirms,
            },
            "prepared": {
                "businesses": len(prepared["businesses"]),
                "ads": len(prepared["ads"]),
                "payment_ads": len(prepared.get("payment_ads", [])),
                "remitters": len(prepared["remitters"]),
            },
            "metrics": summary,
            "latency_isolation": self.latency_isolation_summary(),
            "latency_samples": self.latency_samples,
            "request_error_samples": self.request_error_samples,
            "request_error_summary": self.request_error_summary(),
            "profiled_steps": self.profiled_steps,
            "profile_summary": self.profile_summary(),
            "invariant_violations": self.violations,
            "details": details,
            "exit_code": exit_code,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--scenario", choices=["all", "marketplace-reads", "order-flow", "order-race", "payment-confirm"], default="all")
    parser.add_argument("--businesses", type=int, default=2)
    parser.add_argument("--ads-per-business", type=int, default=4)
    parser.add_argument("--remitters", type=int, default=8)
    parser.add_argument("--marketplace-reads", type=int, default=20)
    parser.add_argument("--marketplace-concurrency", type=int, default=None)
    parser.add_argument("--order-creates", type=int, default=4)
    parser.add_argument("--same-ad-race-requests", type=int, default=6)
    parser.add_argument("--payment-confirms", type=int, default=0)
    parser.add_argument("--run-id", default=f"capacity{int(time.time())}")
    parser.add_argument("--output", default="evidence/slice_runs/real_services_capacity_harness.json")
    parser.add_argument("--remote-base-url", default=None)
    parser.add_argument("--fixture-mode", choices=["local_asgi", "db_seed_api_remote", "api_remote_only"], default=None)
    parser.add_argument("--profile-marketplace", action="store_true")
    parser.add_argument("--auth-mode", choices=["fresh-claims", "fallback-db"], default="fresh-claims")
    parser.add_argument("--max-connections", type=int, default=None)
    parser.add_argument("--fixture-setup-mode", choices=["api_ads", "db_direct_ads"], default="api_ads")
    args = parser.parse_args()
    payload = RealCapacityHarness(
        env_file=Path(args.env_file),
        run_id=args.run_id,
        businesses=args.businesses,
        ads_per_business=args.ads_per_business,
        remitters=args.remitters,
        marketplace_reads=args.marketplace_reads,
        order_creates=args.order_creates,
        same_ad_race_requests=args.same_ad_race_requests,
        payment_confirms=args.payment_confirms,
        marketplace_concurrency=args.marketplace_concurrency,
        remote_base_url=args.remote_base_url,
        fixture_mode=args.fixture_mode,
        profile_marketplace=args.profile_marketplace,
        auth_mode=args.auth_mode,
        max_connections=args.max_connections,
        fixture_setup_mode=args.fixture_setup_mode,
    ).run(args.scenario)
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, default=str))
    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
