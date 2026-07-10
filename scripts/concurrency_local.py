from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

import httpx
import psycopg

from local_hardening_common import DEFAULT_ENV_FILE, MetricsRecorder, add_api_path, write_json
from local_smoke import LocalSmoke

add_api_path()
from app.shared.db.connection import connect  # noqa: E402


class LocalConcurrency:
    def __init__(
        self,
        *,
        env_file: Path,
        run_id: str,
        searches: int,
        duplicate_requests: int,
        same_ad_requests: int,
        unique_orders: int,
    ) -> None:
        self.smoke = LocalSmoke(env_file=env_file, run_id=run_id)
        self.run_id = run_id
        self.searches = searches
        self.duplicate_requests = duplicate_requests
        self.same_ad_requests = same_ad_requests
        self.unique_orders = unique_orders
        self.metrics = MetricsRecorder()
        self.started_at = time.perf_counter()
        self.violations: dict[str, int] = {
            "duplicate_order_rows": 0,
            "duplicate_order_response_mismatch": 0,
            "duplicate_order_errors": 0,
            "same_ad_multiple_orders": 0,
            "same_ad_success_count_invalid": 0,
            "same_ad_db_rows_invalid": 0,
            "unique_order_errors": 0,
            "search_errors": 0,
            "negative_balances": 0,
            "db_errors": 0,
        }

    def _prepare(self) -> dict[str, Any]:
        max_ads_for_single_business = 20
        required_ads = self.unique_orders + 2
        if required_ads > max_ads_for_single_business:
            raise ValueError(
                "unique_orders is too high for one MVP business range set: "
                f"requires {required_ads} ads, maximum is {max_ads_for_single_business}. "
                "Use --unique-orders 18 or less, or extend this harness to seed multiple businesses."
            )
        admin = self.smoke.login(self.smoke.synthetic_telegram_id(310000), "concurrency_admin")
        self.smoke.set_role(admin["user"]["id"], "admin")
        owner = self.smoke.login(self.smoke.synthetic_telegram_id(320000), "concurrency_owner")
        remitter = self.smoke.login(self.smoke.synthetic_telegram_id(330000), "concurrency_remitter")
        race_remitters = [
            self.smoke.login(self.smoke.synthetic_telegram_id(340000 + index), f"concurrency_race_remitter_{index}")
            for index in range(self.same_ad_requests)
        ]
        business, payment_method_id = self.smoke.create_approved_business(owner, admin)
        with connect(self.smoke.db_url) as conn:
            conn.execute(
                "update businesses set active_order_limit = %s, max_order_amount_usd = 100000, updated_at = now() where id = %s",
                (self.unique_orders + self.duplicate_requests + self.same_ad_requests + 5, business["id"]),
            )
            conn.commit()
        self.smoke.request(
            "concurrency:credits:adjust",
            "POST",
            "/api/v1/admin/credits/adjust",
            headers=self.smoke.headers(admin, "concurrency_credit_adjust", content_type=True),
            json={
                "business_id": business["id"],
                "amount": (self.unique_orders + self.duplicate_requests + self.same_ad_requests + 5) * 4,
                "direction": "add",
                "reason": "local_concurrency_seed",
            },
        )
        ads = [
            self.smoke.request(
                f"concurrency:ads:create:{index}",
                "POST",
                "/api/v1/business/ads",
                headers=self.smoke.headers(owner, f"concurrency_ad_{index}", content_type=True),
                json={
                    "payment_method_id": payment_method_id,
                    "payment_method": "zelle",
                    "delivery_method": "pago_movil_ve",
                    "rate_bs_per_usd": "39.5000",
                    "amount_min_usd": f"{20 + (index * 100)}.00",
                    "amount_max_usd": f"{100 + (index * 100)}.00",
                },
            )["ad"]
            for index in range(self.unique_orders + 2)
        ]
        return {
            "admin": admin,
            "owner": owner,
            "remitter": remitter,
            "race_remitters": race_remitters,
            "business": business,
            "ads": ads,
        }

    async def _request(self, client: httpx.AsyncClient, name: str, method: str, url: str, **kwargs: Any) -> httpx.Response:
        started = time.perf_counter()
        response = await client.request(method, url, **kwargs)
        self.metrics.record(name, response.status_code, started)
        return response

    async def _run_async(self, prepared: dict[str, Any]) -> dict[str, Any]:
        transport = httpx.ASGITransport(app=self.smoke.client.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            search_responses = await asyncio.gather(
                *[
                    self._request(
                        client,
                        "concurrent:ads:search",
                        "GET",
                        "/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&delivery_method=pago_movil_ve&limit=20",
                        headers=self.smoke.bearer(prepared["remitter"], f"concurrency_search_{index}"),
                    )
                    for index in range(self.searches)
                ]
            )
            self.violations["search_errors"] = sum(1 for response in search_responses if response.status_code >= 400)

            duplicate_ad = prepared["ads"][0]
            duplicate_payload = {
                "ad_id": duplicate_ad["id"],
                "amount_usd": "50.00",
                "receiver_data": {"bank": "Banco Local", "phone": "+584121234567", "document": "V99990000", "holder": "Concurrent Receiver"},
            }
            duplicate_key = f"{self.run_id}_duplicate_order_key"
            duplicate_responses = await asyncio.gather(
                *[
                    self._request(
                        client,
                        "concurrent:orders:duplicate_key",
                        "POST",
                        "/api/v1/orders",
                        headers={
                            **self.smoke.headers(prepared["remitter"], duplicate_key, content_type=True),
                            "X-Request-Id": f"req_{self.run_id}_duplicate_{index}",
                        },
                        json=duplicate_payload,
                    )
                    for index in range(self.duplicate_requests)
                ]
            )
            successful_duplicate_ids = []
            for response in duplicate_responses:
                if response.status_code >= 400:
                    self.violations["duplicate_order_errors"] += 1
                    continue
                successful_duplicate_ids.append(response.json()["data"]["order"]["id"])
            if len(set(successful_duplicate_ids)) > 1:
                self.violations["duplicate_order_response_mismatch"] += 1

            race_ad = prepared["ads"][1]
            same_ad_responses = await asyncio.gather(
                *[
                    self._request(
                        client,
                        "concurrent:orders:same_ad_different_keys",
                        "POST",
                        "/api/v1/orders",
                        headers=self.smoke.headers(race_remitter, f"concurrency_same_ad_{index}", content_type=True),
                        json={
                            "ad_id": race_ad["id"],
                            "amount_usd": "150.00",
                            "receiver_data": {
                                "bank": "Banco Local",
                                "phone": "+584121234567",
                                "document": f"V7777{index:04d}",
                                "holder": f"Concurrent Same Ad Receiver {index}",
                            },
                        },
                    )
                    for index, race_remitter in enumerate(prepared["race_remitters"])
                ]
            )
            same_ad_successful_ids = [
                response.json()["data"]["order"]["id"] for response in same_ad_responses if response.status_code < 400
            ]
            if len(set(same_ad_successful_ids)) > 1:
                self.violations["same_ad_multiple_orders"] += 1
            if len(same_ad_successful_ids) != 1:
                self.violations["same_ad_success_count_invalid"] += 1

            unique_responses = await asyncio.gather(
                *[
                    self._request(
                        client,
                        "concurrent:orders:create_unique",
                        "POST",
                        "/api/v1/orders",
                        headers=self.smoke.headers(prepared["remitter"], f"concurrency_unique_order_{index}", content_type=True),
                        json={
                            "ad_id": prepared["ads"][index + 2]["id"],
                            "amount_usd": f"{50 + ((index + 2) * 100)}.00",
                            "receiver_data": {
                                "bank": "Banco Local",
                                "phone": "+584121234567",
                                "document": f"V{index:08d}",
                                "holder": "Concurrent Unique Receiver",
                            },
                        },
                    )
                    for index in range(self.unique_orders)
                ]
            )
            self.violations["unique_order_errors"] = sum(1 for response in unique_responses if response.status_code >= 400)

        with connect(self.smoke.db_url, row_factory=psycopg.rows.dict_row) as conn:
            duplicate_rows = conn.execute(
                "select count(*) as count from orders where remitter_user_id = %s and idempotency_key = %s",
                (prepared["remitter"]["user"]["id"], duplicate_key),
            ).fetchone()["count"]
            same_ad_rows = conn.execute(
                "select count(*) as count from orders where ad_id = %s",
                (prepared["ads"][1]["id"],),
            ).fetchone()["count"]
            negative_balances = conn.execute(
                "select count(*) as count from credit_wallets where available_credits < 0 or blocked_credits < 0 or consumed_credits < 0"
            ).fetchone()["count"]
        self.violations["duplicate_order_rows"] = max(0, int(duplicate_rows) - 1)
        self.violations["same_ad_db_rows_invalid"] = 0 if int(same_ad_rows) == 1 else 1
        self.violations["negative_balances"] = int(negative_balances)

        return {
            "duplicate_successful_ids": successful_duplicate_ids,
            "duplicate_status_codes": [response.status_code for response in duplicate_responses],
            "same_ad_successful_ids": same_ad_successful_ids,
            "same_ad_status_codes": [response.status_code for response in same_ad_responses],
            "unique_status_codes": [response.status_code for response in unique_responses],
            "search_status_codes": [response.status_code for response in search_responses],
        }

    def run(self) -> dict[str, Any]:
        prepared = self._prepare()
        details = asyncio.run(self._run_async(prepared))
        summary = self.metrics.summary(started_at=self.started_at)
        exit_code = 1 if any(self.violations.values()) else 0
        return {
            "slice": "slice_11_hardening_deploy",
            "phase": "local_concurrency",
            "run_id": self.run_id,
            "targets": {
                "searches": self.searches,
                "duplicate_requests_same_idempotency_key": self.duplicate_requests,
                "same_ad_requests_different_idempotency_keys": self.same_ad_requests,
                "unique_order_creations": self.unique_orders,
            },
            "metrics": summary,
            "invariant_violations": self.violations,
            "details": details,
            "exit_code": exit_code,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--searches", type=int, default=25)
    parser.add_argument("--duplicate-requests", type=int, default=8)
    parser.add_argument("--same-ad-requests", type=int, default=8)
    parser.add_argument("--unique-orders", type=int, default=8)
    parser.add_argument("--run-id", default=f"concurrency{int(time.time())}")
    parser.add_argument("--output", default="evidence/slice_runs/slice_11_local_concurrency.json")
    args = parser.parse_args()
    payload = LocalConcurrency(
        env_file=Path(args.env_file),
        run_id=args.run_id,
        searches=args.searches,
        duplicate_requests=args.duplicate_requests,
        same_ad_requests=args.same_ad_requests,
        unique_orders=args.unique_orders,
    ).run()
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, default=str))
    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
