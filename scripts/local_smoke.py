from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
import time
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from local_hardening_common import DEFAULT_ENV_FILE, MetricsRecorder, add_api_path, configure_env, write_json

add_api_path()
from app.shared.db.connection import connect  # noqa: E402
from app.auth.jwt import create_access_token, create_refresh_token, hash_refresh_token  # noqa: E402
from app.modules.users.auth_helpers import hash_ip  # noqa: E402
from app.modules.users.models import utc_now  # noqa: E402
from app.modules.users.presenters import public_user_payload  # noqa: E402


def signed_init_data(telegram_id: int, username: str, bot_token: str) -> str:
    payload = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": telegram_id, "username": username, "first_name": username}, separators=(",", ":"), sort_keys=True),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


class LocalSmoke:
    def __init__(self, *, env_file: Path, run_id: str) -> None:
        self.env = configure_env(env_file)
        from app.main import create_app

        self.client = TestClient(create_app())
        self.run_id = run_id
        self.metrics = MetricsRecorder()
        self.started_at = time.perf_counter()
        self.steps: list[dict] = []
        self.db_url = self.env["DATABASE_URL"]
        self.bot_token = self.env["BOT_TOKEN"]
        self.sequence = 0
        self.access_token_refresh_margin_seconds = 120

    def metric_route_group(self, method: str, path: str) -> str:
        route = path.split("?", 1)[0]
        route = re.sub(
            r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?=/|$)",
            "/{id}",
            route,
        )
        return f"{method.upper()} {route}"

    def unique_key(self, label: str) -> str:
        self.sequence += 1
        return f"{label}_{self.sequence}"

    def synthetic_telegram_id(self, offset: int) -> int:
        run_hash = int(hashlib.sha256(self.run_id.encode("utf-8")).hexdigest()[:12], 16)
        return 7_000_000_000 + (run_hash % 1_000_000) * 1_000 + offset

    def request(self, name: str, method: str, path: str, **kwargs) -> dict:
        started = time.perf_counter()
        response = self.client.request(method, path, **kwargs)
        latency_ms = self.metrics.record(name, response.status_code, started, route_group=self.metric_route_group(method, path))
        step = {
            "name": name,
            "method": method,
            "path": path,
            "status_code": response.status_code,
            "latency_ms": round(latency_ms, 4),
            "route_group": self.metric_route_group(method, path),
        }
        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text[:500]}
        data = body.get("data") if isinstance(body, dict) else None
        if isinstance(data, dict) and "_profile" in data:
            step["profile"] = data.pop("_profile")
        step["body_keys"] = sorted(body.keys()) if isinstance(body, dict) else []
        self.steps.append(step)
        if response.status_code >= 400:
            raise RuntimeError(f"{name} failed: {response.status_code} {response.text}")
        return data

    def stamp_login(self, login: dict) -> dict:
        login["_issued_monotonic"] = time.perf_counter()
        return login

    def ensure_fresh_login(self, login: dict, key: str) -> None:
        expires_in = int(login.get("expires_in") or 0)
        issued_at = float(login.get("_issued_monotonic") or 0)
        refresh_token = login.get("refresh_token")
        if not expires_in or not issued_at or not refresh_token:
            return
        refresh_margin = min(self.access_token_refresh_margin_seconds, max(1, expires_in // 4))
        if time.perf_counter() - issued_at < expires_in - refresh_margin:
            return
        existing_user = login.get("user")
        refreshed = self.request(
            f"auth:refresh:{key}",
            "POST",
            "/api/v1/auth/refresh",
            headers={"X-Request-Id": f"req_{self.run_id}_{key}_refresh"},
            json={"refresh_token": refresh_token},
        )
        login.update(refreshed)
        if existing_user and "user" not in login:
            login["user"] = existing_user
        self.stamp_login(login)

    def headers(self, login: dict, key: str, *, content_type: bool = False) -> dict[str, str]:
        self.ensure_fresh_login(login, key)
        headers = {
            "Authorization": f"Bearer {login['access_token']}",
            "X-Request-Id": f"req_{self.run_id}_{key}",
            "Idempotency-Key": f"{self.run_id}_{key}",
        }
        if content_type:
            headers["Content-Type"] = "application/json"
        return headers

    def bearer(self, login: dict, key: str) -> dict[str, str]:
        self.ensure_fresh_login(login, key)
        return {"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": f"req_{self.run_id}_{key}"}

    def login(self, telegram_id: int, username: str) -> dict:
        return self.stamp_login(self.request(
            f"auth:{username}",
            "POST",
            "/api/v1/auth/telegram",
            headers={"X-Request-Id": f"req_{self.run_id}_login_{telegram_id}"},
            json={"init_data": signed_init_data(telegram_id, f"{self.run_id}_{username}", self.bot_token)},
        ))

    def fixture_login(self, telegram_id: int, username: str, *, role: str = "remitter") -> dict:
        """Create a synthetic session without exercising the public auth rate limit."""
        settings = self.client.app.state.settings
        if not settings.jwt_secret or not settings.jwt_refresh_secret:
            raise RuntimeError("fixture_login requires JWT secrets")
        user, _created = self.client.app.state.user_repository.upsert_telegram_user(
            telegram_id=telegram_id,
            username=f"{self.run_id}_{username}",
            first_name=username,
            last_name=None,
        )
        if role != user.role:
            self.client.app.state.user_repository.set_user_role(user.id, role)
            user = self.client.app.state.user_repository.get_user_by_id(user.id)
            if user is None:
                raise RuntimeError("fixture_login failed to reload user")
        access_token, access_token_jti, _ = create_access_token(
            user_id=user.id,
            role=user.role,
            status=user.status,
            secret=settings.jwt_secret,
            ttl_seconds=settings.access_token_ttl_seconds,
        )
        refresh_token = create_refresh_token()
        self.client.app.state.user_repository.create_session(
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(refresh_token, settings.jwt_refresh_secret),
            access_token_jti=access_token_jti,
            expires_at=utc_now() + timedelta(seconds=settings.refresh_token_ttl_seconds),
            ip_hash=hash_ip("127.0.0.1"),
            user_agent="capacity-fixture",
        )
        login = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": settings.access_token_ttl_seconds,
            "user": public_user_payload(user),
            "_fixture_telegram_id": telegram_id,
            "_fixture_username": username,
            "_fixture_role": user.role,
        }
        self.steps.append({
            "name": f"fixture_login:{username}",
            "telegram_id": telegram_id,
            "role": user.role,
            "status_code": 200,
        })
        return self.stamp_login(login)

    def set_role(self, user_id: str, role: str) -> None:
        self.client.app.state.user_repository.set_user_role(user_id, role)
        self.steps.append({"name": "fixture:set_role", "user_id": user_id, "role": role, "status_code": 200})

    def activate_payment_method(self, payment_method_id: str, business_id: str) -> None:
        with connect(self.db_url) as conn:
            conn.execute(
                "update business_payment_methods set verified_status = 'approved', active = true, updated_at = now() where id = %s and business_id = %s",
                (payment_method_id, business_id),
            )
            conn.commit()
        self.steps.append({"name": "fixture:activate_payment_method", "payment_method_id": payment_method_id, "status_code": 200})

    def create_approved_business(self, owner: dict, admin: dict) -> tuple[dict, str]:
        suffix = self.unique_key("business")
        self.set_role(owner["user"]["id"], "business_owner")
        business = self.client.app.state.business_repository.create_business(
            owner_user_id=owner["user"]["id"],
            business_name=f"Casa Local {self.run_id} {suffix}",
            rif="J-12345678-9",
            address="Av Local 1",
            phone="+584121234567",
            country="VE",
        )
        with connect(self.db_url) as conn:
            conn.execute(
                """
                update businesses
                set verification_status = 'approved',
                    approved_at = now(),
                    max_order_amount_usd = 100000,
                    active_order_limit = 100000,
                    updated_at = now()
                where id = %s
                returning *
                """,
                (business.id,),
            )
            conn.commit()
        approved_id = business.id
        approved = self.client.app.state.business_repository.get_business(approved_id)
        owner_record = self.client.app.state.user_repository.get_user_by_id(owner["user"]["id"])
        self.client.app.state.business_repository.create_access_link(
            business_id=approved_id,
            user_id=owner["user"]["id"],
            telegram_id_snapshot=owner_record.telegram_id,
            role_in_business="owner",
            linked_by_admin_id=admin["user"]["id"],
            reason="Synthetic local hardening access link",
        )
        payment = self.client.app.state.business_repository.add_payment_method(
            business_id=approved_id,
            method_type="zelle",
            network=None,
            account_value=f"{self.run_id}@example.local",
            account_masked="***.local",
            holder_name="Owner Local",
        )
        self.activate_payment_method(payment.id, approved_id)
        self.steps.append({"name": "fixture:create_approved_business", "business_id": approved_id, "status_code": 200})
        return {"id": approved.id, "business_name": approved.business_name, "verification_status": approved.verification_status}, payment.id

    def run(self) -> dict:
        health = self.request("health", "GET", "/health", headers={"X-Request-Id": f"req_{self.run_id}_health"})
        ready = self.request("ready", "GET", "/ready", headers={"X-Request-Id": f"req_{self.run_id}_ready"})
        version = self.request("version", "GET", "/version", headers={"X-Request-Id": f"req_{self.run_id}_version"})

        owner = self.login(self.synthetic_telegram_id(110), "owner")
        remitter = self.login(self.synthetic_telegram_id(120), "remitter")
        admin = self.login(self.synthetic_telegram_id(130), "admin")
        self.set_role(admin["user"]["id"], "admin")

        business, payment_method_id = self.create_approved_business(owner, admin)
        adjustment = self.request(
            "admin:credits:adjust",
            "POST",
            "/api/v1/admin/credits/adjust",
            headers=self.headers(admin, "admin_credit_adjust", content_type=True),
            json={"business_id": business["id"], "amount": 5, "direction": "add", "reason": "local_hardening_seed"},
        )
        ad = self.request(
            "ads:create",
            "POST",
            "/api/v1/business/ads",
            headers=self.headers(owner, "create_ad", content_type=True),
            json={
                "payment_method_id": payment_method_id,
                "payment_method": "zelle",
                "delivery_method": "pago_movil_ve",
                "rate_bs_per_usd": "39.5000",
                "amount_min_usd": "20.00",
                "amount_max_usd": "100.00",
            },
        )["ad"]
        search = self.request(
            "ads:search",
            "GET",
            "/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&delivery_method=pago_movil_ve&limit=10",
            headers=self.bearer(remitter, "search_ads"),
        )
        order = self.request(
            "orders:create",
            "POST",
            "/api/v1/orders",
            headers=self.headers(remitter, "create_order", content_type=True),
            json={
                "ad_id": ad["id"],
                "amount_usd": "50.00",
                "receiver_data": {"bank": "Banco Local", "phone": "+584121234567", "document": "V12345678", "holder": "Receiver Local"},
            },
        )["order"]
        instructions = self.request(
            "orders:payment_instructions",
            "GET",
            f"/api/v1/orders/{order['id']}/payment-instructions",
            headers=self.bearer(remitter, "payment_instructions"),
        )
        evidence = self.request(
            "orders:payment_evidence",
            "POST",
            f"/api/v1/orders/{order['id']}/payment-evidence",
            headers=self.headers(remitter, "payment_evidence"),
            data={"file_type": "payment_evidence"},
            files={"file": ("proof.png", b"synthetic-proof", "image/png")},
        )
        report = self.request(
            "orders:payment_report",
            "POST",
            f"/api/v1/orders/{order['id']}/payment-report",
            headers=self.headers(remitter, "payment_report", content_type=True),
            json={
                "payment_type": "zelle",
                "payment_reference": "LOCAL-REF-123456",
                "payment_sender_name": "Remitter Local",
                "payment_sender_account_masked": "***1234",
                "payment_amount": "50.00",
                "proof_file_id": evidence["file"]["id"],
                "pending_payment_report_id": evidence["pending_payment_report_id"],
            },
        )
        confirmed = self.request(
            "business_orders:confirm_payment",
            "POST",
            f"/api/v1/business/orders/{order['id']}/confirm-payment",
            headers=self.headers(owner, "confirm_payment", content_type=True),
            json={"reason": "Pago recibido en smoke local"},
        )
        delivered = self.request(
            "business_orders:mark_delivered",
            "POST",
            f"/api/v1/business/orders/{order['id']}/mark-delivered",
            headers=self.headers(owner, "mark_delivered", content_type=True),
            json={"reason": "Pago movil enviado en smoke local"},
        )
        message = self.request(
            "chat:message",
            "POST",
            f"/api/v1/orders/{order['id']}/messages",
            headers=self.headers(remitter, "chat_message", content_type=True),
            json={"body": "Mensaje sintetico local", "attachment_ids": []},
        )
        dispute = self.request(
            "disputes:open",
            "POST",
            f"/api/v1/orders/{order['id']}/disputes",
            headers=self.headers(remitter, "open_dispute", content_type=True),
            json={"reason": "payment_mobile_not_received", "description": "Disputa sintetica local", "evidence_file_ids": []},
        )["dispute"]
        resolved = self.request(
            "admin:dispute:resolve",
            "POST",
            f"/api/v1/admin/disputes/{dispute['id']}/resolve",
            headers=self.headers(admin, "resolve_dispute", content_type=True),
            json={"resolution_type": "keep_under_review", "reason": "Smoke local mantiene revision"},
        )
        job_dry_run = self.request(
            "admin:jobs:dry_run",
            "POST",
            "/api/v1/admin/jobs/expire-and-escalate-orders/dry-run?batch_size=50",
            headers=self.headers(admin, "job_dry_run"),
        )
        dashboard = self.request("admin:dashboard", "GET", "/api/v1/admin/dashboard", headers=self.bearer(admin, "dashboard"))
        metrics = self.request("admin:metrics", "GET", "/api/v1/admin/metrics", headers=self.bearer(admin, "metrics"))

        combined_payload = json.dumps(
            [health, ready, version, search, order, instructions, evidence, report, confirmed, delivered, message, resolved, adjustment, job_dry_run, dashboard, metrics],
            default=str,
        )
        forbidden_hits = [
            term
            for term in ["storage_path", "JWT_SECRET", "JWT_REFRESH_SECRET", "BOT_TOKEN", "STRIPE_SECRET", "payment_instructions_snapshot"]
            if term in combined_payload
        ]
        summary = self.metrics.summary(started_at=self.started_at)
        return {
            "slice": "slice_11_hardening_deploy",
            "phase": "local_smoke",
            "run_id": self.run_id,
            "dataset": {"businesses": 1, "remitters": 1, "admins": 1, "orders": 1, "disputes": 1},
            "ids": {"business_id": business["id"], "ad_id": ad["id"], "order_id": order["id"], "dispute_id": dispute["id"]},
            "metrics": summary,
            "forbidden_response_hits": forbidden_hits,
            "steps": self.steps,
            "exit_code": 1 if forbidden_hits else 0,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--run-id", default=f"local{int(time.time())}")
    parser.add_argument("--output", default="evidence/slice_runs/slice_11_local_smoke.json")
    args = parser.parse_args()
    payload = LocalSmoke(env_file=Path(args.env_file), run_id=args.run_id).run()
    write_json(Path(args.output), payload)
    print(payload)
    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
