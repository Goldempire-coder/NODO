from __future__ import annotations

import argparse
import json
import time
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from cleanup_synthetic_run import collect_counts, populate_cleanup_tables, validate_run_id
from local_hardening_common import DEFAULT_ENV_FILE, add_api_path, configure_env, write_json
from staging_guardrails import guardrail_payload, require_staging_guardrails

add_api_path()
from app.modules.ads.rules import calculate_required_credits  # noqa: E402
from app.shared.cache import CacheUnavailableError, RedisTTLCache  # noqa: E402
from app.shared.db.connection import connect  # noqa: E402


MARKETPLACE_CACHE_NAMESPACE = "marketplace:ads"
TARGET_RATE_BS_PER_USD = Decimal("39.5000")


def expected_counts(businesses: int, ads_per_business: int) -> dict[str, int]:
    if businesses < 1:
        raise ValueError("businesses must be >= 1")
    if ads_per_business < 1:
        raise ValueError("ads_per_business must be >= 1")
    if ads_per_business > 18:
        raise ValueError("ads_per_business must be <= 18")
    ads = businesses * ads_per_business
    return {
        "admin_users": 1,
        "owner_users": businesses,
        "users": businesses + 1,
        "businesses": businesses,
        "business_access_links": businesses,
        "business_payment_methods": businesses,
        "credit_wallets": businesses,
        "ads": ads,
        "credits_ledger": ads,
    }


def synthetic_telegram_id(run_id: str, offset: int) -> int:
    digest = uuid.uuid5(uuid.NAMESPACE_URL, run_id).int
    return 7_800_000_000 + (digest % 1_000_000) * 10_000 + offset


def ad_amount_range(ad_index: int) -> tuple[Decimal, Decimal]:
    amount_min = Decimal(20 + ad_index * 100)
    amount_max = min(amount_min + Decimal(80), Decimal(2000))
    return amount_min.quantize(Decimal("0.01")), amount_max.quantize(Decimal("0.01"))


def _json_safe_counts(counts: dict[str, Any]) -> dict[str, int]:
    return {key: int(value) for key, value in counts.items()}


def _sample_ids(ids: list[str], limit: int = 3) -> list[str]:
    return ids[:limit]


def fixture_validation_failures(validation: dict[str, int], expected: dict[str, int]) -> list[str]:
    failures: list[str] = []
    if validation["approved_businesses"] != expected["businesses"]:
        failures.append("approved_business_count_mismatch")
    if validation["marketplace_visible_ads"] != expected["ads"]:
        failures.append("marketplace_visible_ad_count_mismatch")
    if validation["invalid_ads"] != 0:
        failures.append("invalid_ads_present")
    if validation["active_access_links"] != expected["business_access_links"]:
        failures.append("active_access_link_count_mismatch")
    if validation["valid_wallets"] != expected["credit_wallets"]:
        failures.append("credit_wallet_count_mismatch")
    return failures


def output_contains_sensitive_marker(payload: dict[str, Any]) -> list[str]:
    markers = (
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

    def values_only(value: Any) -> Any:
        if isinstance(value, dict):
            return [values_only(item) for item in value.values()]
        if isinstance(value, list):
            return [values_only(item) for item in value]
        return value

    serialized = json.dumps(values_only(payload), ensure_ascii=False)
    return [marker for marker in markers if marker.lower() in serialized.lower()]


def _insert_rows(cursor: psycopg.Cursor[Any], sql: str, rows: list[tuple[Any, ...]]) -> None:
    if rows:
        cursor.executemany(sql, rows)


def seed_fixture(conn: psycopg.Connection[Any], *, run_id: str, businesses: int, ads_per_business: int) -> dict[str, Any]:
    validate_run_id(run_id)
    counts = expected_counts(businesses, ads_per_business)
    now_expr = "now()"
    admin_id = uuid.uuid4()
    owner_ids = [uuid.uuid4() for _ in range(businesses)]
    business_ids = [uuid.uuid4() for _ in range(businesses)]
    payment_method_ids = [uuid.uuid4() for _ in range(businesses)]
    wallet_ids = [uuid.uuid4() for _ in range(businesses)]
    access_link_ids = [uuid.uuid4() for _ in range(businesses)]
    ad_ids: list[uuid.UUID] = []
    ledger_ids: list[uuid.UUID] = []

    user_rows: list[tuple[Any, ...]] = [
        (
            admin_id,
            synthetic_telegram_id(run_id, 9000),
            f"{run_id}_fixture_admin",
            f"{run_id}_fixture_admin",
            "admin",
            "active",
        )
    ]
    for index, owner_id in enumerate(owner_ids):
        user_rows.append(
            (
                owner_id,
                synthetic_telegram_id(run_id, index),
                f"{run_id}_owner_{index:04d}",
                f"{run_id}_owner_{index:04d}",
                "business_owner",
                "active",
            )
        )

    business_rows = [
        (
            business_ids[index],
            owner_ids[index],
            f"Delivery {run_id} business {index:04d}",
            f"J-{index:08d}-9",
            f"+58412{index:07d}"[-12:],
        )
        for index in range(businesses)
    ]
    payment_rows = [
        (
            payment_method_ids[index],
            business_ids[index],
            f"delivery_fixture_{run_id}_{index:04d}@example.local",
            f"***{index:04d}",
        )
        for index in range(businesses)
    ]
    access_rows = [
        (
            access_link_ids[index],
            business_ids[index],
            owner_ids[index],
            synthetic_telegram_id(run_id, index),
            admin_id,
        )
        for index in range(businesses)
    ]

    wallet_rows: list[tuple[Any, ...]] = []
    ad_rows: list[tuple[Any, ...]] = []
    ledger_rows: list[tuple[Any, ...]] = []
    ad_ledger_rows: list[tuple[Any, ...]] = []
    for business_index in range(businesses):
        available = 10_000
        blocked = 0
        total_required = 0
        for ad_index in range(ads_per_business):
            ad_id = uuid.uuid4()
            ledger_id = uuid.uuid4()
            amount_min, amount_max = ad_amount_range(ad_index)
            required = calculate_required_credits(amount_max)
            available_after = available - required
            blocked_after = blocked + required
            ad_ids.append(ad_id)
            ledger_ids.append(ledger_id)
            ad_rows.append(
                (
                    ad_id,
                    business_ids[business_index],
                    payment_method_ids[business_index],
                    amount_min,
                    amount_max,
                    required,
                )
            )
            ledger_rows.append(
                (
                    ledger_id,
                    business_ids[business_index],
                    required,
                    available,
                    available_after,
                    blocked,
                    blocked_after,
                    ad_id,
                    owner_ids[business_index],
                )
            )
            ad_ledger_rows.append((ledger_id, ad_id))
            available = available_after
            blocked = blocked_after
            total_required += required
        wallet_rows.append(
            (
                wallet_ids[business_index],
                business_ids[business_index],
                10_000 - total_required,
                total_required,
                10_000,
            )
        )

    with conn.cursor() as cursor:
        _insert_rows(
            cursor,
            f"""
            insert into users (id, telegram_id, username, first_name, role, status, created_at, updated_at)
            values (%s, %s, %s, %s, %s, %s, {now_expr}, {now_expr})
            """,
            user_rows,
        )
        _insert_rows(
            cursor,
            f"""
            insert into businesses (
                id, owner_user_id, business_name, rif, address, phone, country,
                verification_status, trust_level, risk_level,
                max_order_amount_usd, daily_limit_usd, active_order_limit,
                approved_at, created_at, updated_at
            )
            values (%s, %s, %s, %s, 'Av Delivery Fixture 1', %s, 'VE',
                'approved', 'basic', 'normal', 100000, 100000, 100000, {now_expr}, {now_expr}, {now_expr})
            """,
            business_rows,
        )
        _insert_rows(
            cursor,
            f"""
            insert into business_payment_methods (
                id, business_id, method_type, network, account_value, account_masked,
                holder_name, verified_status, active, created_at, updated_at
            )
            values (%s, %s, 'zelle', null, %s, %s, 'Delivery Fixture Owner', 'approved', true, {now_expr}, {now_expr})
            """,
            payment_rows,
        )
        _insert_rows(
            cursor,
            f"""
            insert into business_access_links (
                id, business_id, user_id, telegram_id_snapshot, role_in_business, status,
                linked_by_admin_id, linked_at, reason, created_at, updated_at
            )
            values (%s, %s, %s, %s, 'owner', 'active', %s, {now_expr}, 'delivery_fixture', {now_expr}, {now_expr})
            """,
            access_rows,
        )
        _insert_rows(
            cursor,
            f"""
            insert into credit_wallets (
                id, business_id, available_credits, blocked_credits, consumed_credits,
                lifetime_adjusted_credits, created_at, updated_at
            )
            values (%s, %s, %s, %s, 0, %s, {now_expr}, {now_expr})
            """,
            wallet_rows,
        )
        _insert_rows(
            cursor,
            f"""
            insert into ads (
                id, business_id, payment_method_id, payment_method, delivery_method,
                rate_bs_per_usd, amount_min_usd, amount_max_usd, required_credits,
                status, activated_at, expires_at, last_rate_updated_at, created_at, updated_at
            )
            values (%s, %s, %s, 'zelle', 'pago_movil_ve', {TARGET_RATE_BS_PER_USD}, %s, %s, %s,
                'active', {now_expr}, {now_expr} + interval '7 days', {now_expr}, {now_expr}, {now_expr})
            """,
            ad_rows,
        )
        _insert_rows(
            cursor,
            f"""
            insert into credits_ledger (
                id, business_id, type, amount, available_before, available_after,
                blocked_before, blocked_after, consumed_before, consumed_after,
                related_ad_id, reason, source, reference_type, reference_id, created_by, created_at
            )
            values (%s, %s, 'hold', %s, %s, %s, %s, %s, 0, 0, %s,
                'ad_publish_credit_hold', 'ads', 'ad', %s, %s, {now_expr})
            """,
            [(ledger_id, business_id, amount, available_before, available_after, blocked_before, blocked_after, ad_id, ad_id, created_by) for ledger_id, business_id, amount, available_before, available_after, blocked_before, blocked_after, ad_id, created_by in ledger_rows],
        )
        _insert_rows(
            cursor,
            f"update ads set credit_hold_ledger_id = %s, updated_at = {now_expr} where id = %s",
            ad_ledger_rows,
        )

    return {
        "inserted_counts": counts,
        "sample_ids": {
            "businesses": _sample_ids([str(item) for item in business_ids]),
            "ads": _sample_ids([str(item) for item in ad_ids]),
        },
    }


def validate_fixture(conn: psycopg.Connection[Any], *, run_id: str, businesses: int, ads_per_business: int) -> dict[str, Any]:
    expected = expected_counts(businesses, ads_per_business)
    like = f"%{run_id}%"
    row = conn.execute(
        """
        select
            (select count(*) from users where username ilike %s or first_name ilike %s) as users,
            (select count(*) from businesses where business_name ilike %s and verification_status = 'approved') as approved_businesses,
            (
                select count(*)
                from ads a
                join businesses b on b.id = a.business_id
                join business_payment_methods pm on pm.id = a.payment_method_id
                where b.business_name ilike %s
                  and b.verification_status = 'approved'
                  and a.status = 'active'
                  and a.expires_at > now()
                  and a.payment_method = 'zelle'
                  and a.delivery_method = 'pago_movil_ve'
                  and pm.active = true
                  and pm.verified_status = 'approved'
            ) as marketplace_visible_ads,
            (
                select count(*)
                from ads a
                join businesses b on b.id = a.business_id
                where b.business_name ilike %s
                  and (a.status <> 'active' or a.expires_at <= now() or a.credit_hold_ledger_id is null)
            ) as invalid_ads,
            (
                select count(*)
                from business_access_links l
                join businesses b on b.id = l.business_id
                where b.business_name ilike %s and l.status = 'active' and l.role_in_business = 'owner'
            ) as active_access_links,
            (
                select count(*)
                from credit_wallets w
                join businesses b on b.id = w.business_id
                where b.business_name ilike %s and w.available_credits >= 0 and w.blocked_credits >= 0
            ) as valid_wallets
        """,
        (like, like, like, like, like, like, like),
    ).fetchone()
    validation = {
        "users_found": int(row["users"]),
        "approved_businesses": int(row["approved_businesses"]),
        "marketplace_visible_ads": int(row["marketplace_visible_ads"]),
        "invalid_ads": int(row["invalid_ads"]),
        "active_access_links": int(row["active_access_links"]),
        "valid_wallets": int(row["valid_wallets"]),
        "expected": expected,
    }
    failures = fixture_validation_failures(validation, expected)
    validation["failures"] = failures
    validation["ok"] = not failures
    return validation


def cleanup_discoverability(conn: psycopg.Connection[Any], *, run_id: str) -> dict[str, int]:
    populate_cleanup_tables(conn, run_id)
    return _json_safe_counts(collect_counts(conn, run_id=run_id))


def bump_marketplace_cache_version(redis_url: str | None) -> dict[str, Any]:
    if not redis_url:
        return {"attempted": False, "status": "skipped_no_redis_url"}
    try:
        cache = RedisTTLCache(redis_url)
        cache.incr(f"{MARKETPLACE_CACHE_NAMESPACE}:version")
    except CacheUnavailableError as exc:
        return {"attempted": True, "status": "failed", "error_code": str(exc)}
    return {"attempted": True, "status": "version_bumped", "namespace": MARKETPLACE_CACHE_NAMESPACE}


def build_payload(
    *,
    env_file: Path,
    run_id: str,
    businesses: int,
    ads_per_business: int,
    apply: bool,
    confirm_staging: bool,
) -> dict[str, Any]:
    validate_run_id(run_id)
    started = time.perf_counter()
    guardrails = require_staging_guardrails(env_file=env_file, mutating=apply, confirm_staging=confirm_staging, run_id=run_id)
    env = configure_env(env_file)
    plan = expected_counts(businesses, ads_per_business)
    payload: dict[str, Any] = {
        "slice": "slice_33A3_fast_fixture_setup_for_delivery_tests",
        "phase": "prepare_marketplace_delivery_fixtures",
        "mode": "apply" if apply else "dry_run",
        "run_id": run_id,
        "businesses_requested": businesses,
        "ads_per_business": ads_per_business,
        "ads_requested": businesses * ads_per_business,
        "planned_counts": plan,
        "inserted_counts": {},
        "validation": {},
        "cleanup_discoverability": {},
        "cache_invalidation": {},
        "sample_ids": {},
        "cleanup_run_id": run_id,
        "guardrails": guardrail_payload(guardrails),
        "failures": [],
        "exit_code": 0,
    }
    if not apply:
        payload["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
        return payload

    try:
        with connect(env["DATABASE_URL"], row_factory=dict_row) as conn:
            seeded = seed_fixture(conn, run_id=run_id, businesses=businesses, ads_per_business=ads_per_business)
            payload["inserted_counts"] = seeded["inserted_counts"]
            payload["sample_ids"] = seeded["sample_ids"]
            payload["validation"] = validate_fixture(conn, run_id=run_id, businesses=businesses, ads_per_business=ads_per_business)
            if payload["validation"].get("failures"):
                payload["failures"].extend(payload["validation"]["failures"])
                conn.rollback()
            else:
                conn.commit()
        if not payload["failures"]:
            with connect(env["DATABASE_URL"]) as conn:
                payload["cleanup_discoverability"] = cleanup_discoverability(conn, run_id=run_id)
                conn.rollback()
    except Exception as exc:
        payload["failures"].append(f"{type(exc).__name__}:{str(exc)[:240]}")
    if not payload["failures"]:
        payload["cache_invalidation"] = bump_marketplace_cache_version(env.get("REDIS_URL"))
    payload["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
    payload["exit_code"] = 1 if payload["failures"] else 0
    markers = output_contains_sensitive_marker(payload)
    payload["sensitive_marker_scan"] = {"status": "failed" if markers else "passed", "markers": markers}
    if markers:
        payload["exit_code"] = 1
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--businesses", type=int, required=True)
    parser.add_argument("--ads-per-business", type=int, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-staging", action="store_true")
    args = parser.parse_args()
    payload = build_payload(
        env_file=Path(args.env_file),
        run_id=args.run_id,
        businesses=args.businesses,
        ads_per_business=args.ads_per_business,
        apply=bool(args.apply),
        confirm_staging=bool(args.confirm_staging),
    )
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, default=str))
    return int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
