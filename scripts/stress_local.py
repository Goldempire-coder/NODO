from __future__ import annotations

import argparse
import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg

from local_hardening_common import DEFAULT_ENV_FILE, add_api_path, write_json
from local_smoke import LocalSmoke

add_api_path()
from app.shared.db.connection import connect  # noqa: E402

PROFILE_TARGETS = {
    "initial": {"businesses": 2, "orders": 2, "marketplace_searches": 4, "stripe_events": 2, "manual_reviews": 1},
    "10": {"businesses": 20, "orders": 200, "marketplace_searches": 200, "stripe_events": 50, "manual_reviews": 20},
    "25": {"businesses": 50, "orders": 500, "marketplace_searches": 500, "stripe_events": 125, "manual_reviews": 50},
    "50": {"businesses": 100, "orders": 1000, "marketplace_searches": 1000, "stripe_events": 250, "manual_reviews": 100},
    "100": {"businesses": 200, "orders": 2000, "marketplace_searches": 2000, "stripe_events": 500, "manual_reviews": 200},
}


class StressTimeoutError(RuntimeError):
    pass


def estimate_required_credits(amount_max_usd: Decimal) -> int:
    if amount_max_usd <= Decimal("100"):
        return 1
    if amount_max_usd <= Decimal("500"):
        return 2
    if amount_max_usd <= Decimal("2000"):
        return 3
    raise ValueError(f"stress amount exceeds MVP ad max: {amount_max_usd}")


class LocalStress(LocalSmoke):
    def __init__(
        self,
        *,
        env_file: Path,
        run_id: str,
        profile: str,
        cap_businesses: int | None,
        cap_orders: int | None,
        workflow_mode: str = "after_orders",
        max_duration_seconds: int | None = None,
        checkpoint_output: Path | None = None,
    ) -> None:
        super().__init__(env_file=env_file, run_id=run_id)
        target = PROFILE_TARGETS[profile].copy()
        if cap_businesses is not None:
            target["businesses"] = min(target["businesses"], cap_businesses)
        if cap_orders is not None:
            target["orders"] = min(target["orders"], cap_orders)
        target["marketplace_searches"] = min(target["marketplace_searches"], max(target["orders"], 1))
        target["stripe_events"] = min(target["stripe_events"], max(target["businesses"], 1))
        target["manual_reviews"] = min(target["manual_reviews"], max(target["businesses"], 1))
        self.target = target
        self.profile = profile
        self.workflow_mode = workflow_mode
        self.max_duration_seconds = max_duration_seconds
        self.checkpoint_output = checkpoint_output
        self.progress: dict[str, Any] = {
            "businesses": 0,
            "ads": 0,
            "orders": 0,
            "workflow_orders": 0,
            "marketplace_searches": 0,
            "phase": "initialized",
        }
        self.synthetic_violations: dict[str, int] = {
            "idempotency_duplicates": 0,
            "idempotency_replay_conflicts": 0,
            "double_credit_consumption": 0,
            "double_credit_accreditation": 0,
            "negative_balances": 0,
            "invalid_transitions": 0,
            "redis_failures": 0,
            "db_errors": 0,
            "timeouts": 0,
            "deadlocks": 0,
            "job_lock_failures": 0,
        }

    def elapsed_seconds(self) -> float:
        return time.perf_counter() - self.started_at

    def enforce_runtime(self, phase: str) -> None:
        if self.max_duration_seconds is None:
            return
        if self.elapsed_seconds() <= self.max_duration_seconds:
            return
        self.progress["phase"] = phase
        self.write_checkpoint(status="timeout")
        raise StressTimeoutError(f"stress exceeded {self.max_duration_seconds}s during {phase}")

    def checkpoint_payload(self, *, status: str) -> dict[str, Any]:
        return {
            "slice": "slice_11_hardening_deploy",
            "phase": "local_stress_checkpoint",
            "status": status,
            "profile": self.profile,
            "workflow_mode": self.workflow_mode,
            "target": self.target,
            "progress": self.progress,
            "elapsed_seconds": round(self.elapsed_seconds(), 3),
            "metrics": self.metrics.summary(started_at=self.started_at),
            "invariant_violations": self.synthetic_violations,
            "steps_recorded": len(self.steps),
        }

    def profiled_steps(self) -> list[dict[str, Any]]:
        return [
            {
                "name": step["name"],
                "method": step["method"],
                "path": step["path"],
                "route_group": step.get("route_group"),
                "status_code": step["status_code"],
                "latency_ms": step.get("latency_ms"),
                "profile": step["profile"],
            }
            for step in self.steps
            if "profile" in step
        ]

    def write_checkpoint(self, *, status: str = "running") -> None:
        if not self.checkpoint_output:
            return
        write_json(self.checkpoint_output, self.checkpoint_payload(status=status))

    def set_business_limit(self, business_id: str, limit: int) -> None:
        with connect(self.db_url) as conn:
            conn.execute(
                "update businesses set active_order_limit = %s, max_order_amount_usd = 100000, updated_at = now() where id = %s",
                (limit, business_id),
            )
            conn.commit()

    def wallet_invariant_scan(self) -> None:
        with connect(self.db_url, row_factory=psycopg.rows.dict_row) as conn:
            negative = conn.execute(
                "select count(*) as count from credit_wallets where available_credits < 0 or blocked_credits < 0 or consumed_credits < 0"
            ).fetchone()["count"]
            duplicate_consumes = conn.execute(
                "select count(*) as count from (select related_order_id from credits_ledger where type = 'consume' and related_order_id is not null group by related_order_id having count(*) > 1) x"
            ).fetchone()["count"]
            duplicate_purchases = conn.execute(
                "select count(*) as count from (select related_credit_purchase_id from credits_ledger where type = 'purchase' and related_credit_purchase_id is not null group by related_credit_purchase_id having count(*) > 1) x"
            ).fetchone()["count"]
        self.synthetic_violations["negative_balances"] = int(negative)
        self.synthetic_violations["double_credit_consumption"] = int(duplicate_consumes)
        self.synthetic_violations["double_credit_accreditation"] = int(duplicate_purchases)

    def complete_workflow_order(self, *, index: int, order: dict, owner: dict, remitter: dict) -> None:
        evidence = self.request(
            f"stress:evidence:{index}",
            "POST",
            f"/api/v1/orders/{order['id']}/payment-evidence",
            headers=self.headers(remitter, f"stress_evidence_{index}"),
            data={"file_type": "payment_evidence"},
            files={"file": ("proof.png", b"stress-proof", "image/png")},
        )
        self.request(
            f"stress:report:{index}",
            "POST",
            f"/api/v1/orders/{order['id']}/payment-report",
            headers=self.headers(remitter, f"stress_report_{index}", content_type=True),
            json={
                "payment_type": "zelle",
                "payment_reference": f"STRESS-{index:06d}",
                "payment_sender_name": "Stress Remitter",
                "payment_sender_account_masked": "***1234",
                "payment_amount": order.get("amount_usd", "50.00"),
                "proof_file_id": evidence["file"]["id"],
                "pending_payment_report_id": evidence["pending_payment_report_id"],
            },
        )
        self.request(
            f"stress:confirm:{index}",
            "POST",
            f"/api/v1/business/orders/{order['id']}/confirm-payment",
            headers=self.headers(owner, f"stress_confirm_{index}", content_type=True),
            json={"reason": "Stress local payment received"},
        )
        self.request(
            f"stress:deliver:{index}",
            "POST",
            f"/api/v1/business/orders/{order['id']}/mark-delivered",
            headers=self.headers(owner, f"stress_deliver_{index}", content_type=True),
            json={"reason": "Stress local delivered"},
        )

    def run_stress(self) -> dict:
        admin = self.login(self.synthetic_telegram_id(210), "stress_admin")
        self.set_role(admin["user"]["id"], "admin")
        remitter_count = min(max(2, self.target["orders"] // 20), 100)
        remitters = [
            self.login(self.synthetic_telegram_id(10_000 + index), f"stress_remitter_{index}")
            for index in range(remitter_count)
        ]
        businesses: list[dict] = []
        ads: list[dict] = []
        orders: list[dict] = []
        workflow_orders: list[dict] = []
        workflow_limit = min(self.target["orders"], self.target["businesses"])
        credits_by_business_index = [0 for _ in range(self.target["businesses"])]
        for order_index in range(self.target["orders"]):
            business_index = order_index % max(self.target["businesses"], 1)
            slot = order_index // max(self.target["businesses"], 1)
            amount_max = Decimal(100 + slot * 100)
            credits_by_business_index[business_index] += estimate_required_credits(amount_max)

        for index in range(self.target["businesses"]):
            self.enforce_runtime("seed_businesses")
            owner = self.login(self.synthetic_telegram_id(230 + index), f"stress_owner_{index}")
            business, payment_method_id = self.create_approved_business(owner, admin)
            self.set_business_limit(business["id"], self.target["orders"])
            credits_for_business = max(credits_by_business_index[index] + 2, 2)
            self.request(
                f"stress:credits:adjust:{index}",
                "POST",
                "/api/v1/admin/credits/adjust",
                headers=self.headers(admin, f"stress_credit_{index}", content_type=True),
                json={"business_id": business["id"], "amount": credits_for_business, "direction": "add", "reason": "local_stress_seed"},
            )
            businesses.append({"owner": owner, "business": business, "payment_method_id": payment_method_id})
            self.progress["businesses"] = len(businesses)
            self.progress["phase"] = "seed_businesses"
            self.write_checkpoint()

        for index in range(self.target["orders"]):
            self.enforce_runtime("create_ads")
            item = businesses[index % len(businesses)]
            slot = index // max(len(businesses), 1)
            amount_min = 20 + slot * 100
            amount_max = 100 + slot * 100
            order_amount = amount_min + 30
            ad = self.request(
                f"stress:ads:create:{index}",
                "POST",
                "/api/v1/business/ads",
                headers=self.headers(item["owner"], f"stress_ad_{index}", content_type=True),
                json={
                    "payment_method_id": item["payment_method_id"],
                    "payment_method": "zelle",
                    "delivery_method": "pago_movil_ve",
                    "rate_bs_per_usd": "39.5000",
                    "amount_min_usd": f"{amount_min}.00",
                    "amount_max_usd": f"{amount_max}.00",
                },
            )["ad"]
            ad["stress_amount_usd"] = f"{order_amount}.00"
            ads.append(ad)
            self.progress["ads"] = len(ads)
            self.progress["phase"] = "create_ads"
            if len(ads) % 5 == 0 or len(ads) == self.target["orders"]:
                self.write_checkpoint()

        for index in range(self.target["marketplace_searches"]):
            self.enforce_runtime("marketplace_searches")
            remitter = remitters[index % len(remitters)]
            self.request(
                f"stress:ads:search:{index}",
                "GET",
                "/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&delivery_method=pago_movil_ve&limit=20",
                headers=self.bearer(remitter, f"stress_search_{index}"),
            )
            self.progress["marketplace_searches"] = index + 1
            self.progress["phase"] = "marketplace_searches"
            if (index + 1) % 10 == 0 or index + 1 == self.target["marketplace_searches"]:
                self.write_checkpoint()

        for index in range(self.target["orders"]):
            self.enforce_runtime("create_orders")
            ad = ads[index % len(ads)]
            remitter = remitters[index % len(remitters)]
            order = self.request(
                f"stress:orders:create:{index}",
                "POST",
                "/api/v1/orders",
                headers=self.headers(remitter, f"stress_order_{index}", content_type=True),
                json={
                    "ad_id": ad["id"],
                    "amount_usd": ad["stress_amount_usd"],
                    "receiver_data": {"bank": "Banco Local", "phone": "+584121234567", "document": f"V{index:08d}", "holder": "Stress Receiver"},
                },
            )["order"]
            replay = self.client.post(
                "/api/v1/orders",
                headers=self.headers(remitter, f"stress_order_{index}", content_type=True),
                json={
                    "ad_id": ad["id"],
                    "amount_usd": "50.00",
                    "receiver_data": {"bank": "Banco Local", "phone": "+584121234567", "document": f"V{index:08d}", "holder": "Stress Receiver"},
                },
            )
            if replay.status_code not in {200, 201}:
                time.sleep(0.1)
                replay = self.client.post(
                    "/api/v1/orders",
                    headers=self.headers(remitter, f"stress_order_{index}", content_type=True),
                    json={
                        "ad_id": ad["id"],
                        "amount_usd": ad["stress_amount_usd"],
                        "receiver_data": {"bank": "Banco Local", "phone": "+584121234567", "document": f"V{index:08d}", "holder": "Stress Receiver"},
                    },
                )
                if replay.status_code not in {200, 201}:
                    self.synthetic_violations["idempotency_replay_conflicts"] += 1
            if replay.status_code in {200, 201} and replay.json()["data"]["order"]["id"] != order["id"]:
                self.synthetic_violations["idempotency_duplicates"] += 1
            order["_stress_remitter_index"] = index % len(remitters)
            orders.append(order)
            self.progress["orders"] = len(orders)
            self.progress["phase"] = "create_orders"
            if self.workflow_mode == "interleaved" and len(workflow_orders) < workflow_limit:
                business_index = index % len(businesses)
                self.enforce_runtime("complete_workflow_interleaved")
                self.complete_workflow_order(
                    index=len(workflow_orders),
                    order=order,
                    owner=businesses[business_index]["owner"],
                    remitter=remitters[order["_stress_remitter_index"]],
                )
                workflow_orders.append(order)
                self.progress["workflow_orders"] = len(workflow_orders)
            if len(orders) % 5 == 0 or len(orders) == self.target["orders"]:
                self.write_checkpoint()

        if self.workflow_mode == "after_orders":
            workflow_orders = orders[:workflow_limit]
            for index, order in enumerate(workflow_orders):
                self.enforce_runtime("complete_workflow_after_orders")
                business_index = index % len(businesses)
                self.complete_workflow_order(
                    index=index,
                    order=order,
                    owner=businesses[business_index]["owner"],
                    remitter=remitters[order["_stress_remitter_index"]],
                )
                self.progress["workflow_orders"] = index + 1
                self.progress["phase"] = "complete_workflow_after_orders"
                self.write_checkpoint()

        self.enforce_runtime("jobs_dry_run")
        self.progress["phase"] = "jobs_dry_run"
        self.write_checkpoint()
        self.request(
            "stress:jobs:dry_run",
            "POST",
            "/api/v1/admin/jobs/expire-and-escalate-orders/dry-run?batch_size=500",
            headers=self.headers(admin, "stress_job_dry_run"),
        )
        self.enforce_runtime("wallet_invariant_scan")
        self.progress["phase"] = "wallet_invariant_scan"
        self.wallet_invariant_scan()
        summary = self.metrics.summary(started_at=self.started_at)
        exit_code = 1 if any(self.synthetic_violations.values()) else 0
        return {
            "slice": "slice_11_hardening_deploy",
            "phase": "local_stress",
            "profile": self.profile,
            "workflow_mode": self.workflow_mode,
            "target": self.target,
            "actual": {"businesses": len(businesses), "remitters": len(remitters), "ads": len(ads), "orders": len(orders), "workflow_orders": len(workflow_orders)},
            "metrics": summary,
            "invariant_violations": self.synthetic_violations,
            "steps_recorded": len(self.steps),
            "profiled_steps": self.profiled_steps(),
            "exit_code": exit_code,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--profile", choices=sorted(PROFILE_TARGETS), default="initial")
    parser.add_argument("--cap-businesses", type=int, default=None)
    parser.add_argument("--cap-orders", type=int, default=None)
    parser.add_argument("--workflow-mode", choices=["after_orders", "interleaved"], default="after_orders")
    parser.add_argument("--max-duration-seconds", type=int, default=None)
    parser.add_argument("--checkpoint-output", default=None)
    parser.add_argument("--run-id", default=f"stress{int(time.time())}")
    parser.add_argument("--output", default="evidence/slice_runs/slice_11_local_stress.json")
    args = parser.parse_args()
    runner = LocalStress(
        env_file=Path(args.env_file),
        run_id=args.run_id,
        profile=args.profile,
        cap_businesses=args.cap_businesses,
        cap_orders=args.cap_orders,
        workflow_mode=args.workflow_mode,
        max_duration_seconds=args.max_duration_seconds,
        checkpoint_output=Path(args.checkpoint_output) if args.checkpoint_output else None,
    )
    try:
        payload = runner.run_stress()
    except StressTimeoutError as exc:
        payload = runner.checkpoint_payload(status="timeout")
        payload["error"] = str(exc)
        payload["exit_code"] = 2
    except Exception as exc:
        payload = runner.checkpoint_payload(status="failed")
        payload["error"] = str(exc)
        payload["error_type"] = type(exc).__name__
        payload["exit_code"] = 1
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, default=str))
    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
