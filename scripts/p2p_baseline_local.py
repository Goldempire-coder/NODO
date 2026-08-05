from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import time
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import psycopg

from local_hardening_common import (
    DEFAULT_ENV_FILE,
    MetricsRecorder,
    assert_local_database_url,
    write_json,
)
from local_smoke import LocalSmoke

from app.modules.businesses.pin_security import hash_pin
from app.modules.users.models import utc_now
from app.modules.users.presenters import public_user_payload
from app.modules.users.terms import CURRENT_TERMS_VERSION
from app.shared.db.connection import connect


PRIVATE_NO_STORE = "private, no-store"
RECEIVER_DETAILS = {
    "bank": "0102",
    "phone": "0414 1234567",
    "document": "V12345678",
    "holder": "Receptor Local",
}


class P2PBaselineLocal(LocalSmoke):
    """Canonical local-only P2P baseline for the current chat-first contract."""

    def __init__(
        self,
        *,
        env_file: Path,
        run_id: str,
        same_ad_requests: int = 50,
    ) -> None:
        super().__init__(env_file=env_file, run_id=run_id)
        assert_local_database_url(self.db_url)
        self.same_ad_requests = same_ad_requests
        self._phase_metrics = {
            "setup": MetricsRecorder(),
            "functional": MetricsRecorder(),
            "concurrency": MetricsRecorder(),
        }
        self._phase_started = {
            phase: time.perf_counter() for phase in self._phase_metrics
        }
        self._safe_steps: list[dict[str, Any]] = []
        self._header_checks: list[dict[str, Any]] = []
        self._violations: list[str] = []
        self._fixture_sequence = 0

    def _record_response(
        self,
        *,
        phase: str,
        name: str,
        method: str,
        path: str,
        response: httpx.Response,
        started_at: float,
    ) -> None:
        route_group = self.metric_route_group(method, path)
        latency_ms = self._phase_metrics[phase].record(
            name,
            response.status_code,
            started_at,
            route_group=route_group,
        )
        self._safe_steps.append(
            {
                "phase": phase,
                "name": name,
                "route": route_group,
                "status_code": response.status_code,
                "latency_ms": round(latency_ms, 4),
            }
        )

    def _request_response(
        self,
        phase: str,
        name: str,
        method: str,
        path: str,
        *,
        expected: set[int] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        started_at = time.perf_counter()
        response = self.client.request(method, path, **kwargs)
        self._record_response(
            phase=phase,
            name=name,
            method=method,
            path=path,
            response=response,
            started_at=started_at,
        )
        allowed = expected or {200, 201}
        if response.status_code not in allowed:
            error_code = "UNKNOWN_ERROR"
            try:
                error_code = response.json().get("error", {}).get("code", error_code)
            except ValueError:
                pass
            raise RuntimeError(
                f"{name} failed with status={response.status_code} code={error_code}"
            )
        return response

    def _request_data(
        self,
        phase: str,
        name: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self._request_response(
            phase,
            name,
            method,
            path,
            **kwargs,
        ).json()["data"]

    def _require_no_store(self, response: httpx.Response, *, label: str) -> None:
        actual = response.headers.get("cache-control")
        passed = actual == PRIVATE_NO_STORE
        self._header_checks.append(
            {"label": label, "status_code": response.status_code, "passed": passed}
        )
        if not passed:
            self._violations.append(f"private_cache_header:{label}")

    def _actor(self, *, offset: int, label: str, role: str = "remitter") -> dict:
        login = self.fixture_login(
            self.synthetic_telegram_id(offset),
            label,
            role=role,
        )
        updated = self.client.app.state.user_repository.accept_terms(
            login["user"]["id"],
            CURRENT_TERMS_VERSION,
        )
        login["user"] = public_user_payload(updated)
        return login

    def _synthetic_rif(self, label: str) -> str:
        digest = int(hashlib.sha256(label.encode("utf-8")).hexdigest()[:10], 16)
        return f"J-{10_000_000 + (digest % 89_999_999):08d}-9"

    def _synthetic_wallet(self, label: str) -> str:
        alphabet = (
            "123456789"
            + "ABCDEFGHJKLMNPQRSTUVWXYZ"
            + "abcdefghijkmnopqrstuvwxyz"
        )
        digest = hashlib.sha256(label.encode("utf-8")).digest()
        suffix = "".join(alphabet[value % len(alphabet)] for value in digest)
        return "T" + (suffix * 2)[:33]

    def _business_fixture(
        self,
        *,
        admin: dict,
        label: str,
        method_types: tuple[str, ...],
        declared_capacity_usd: Decimal,
        credits: int = 8,
        active_order_limit: int = 1,
    ) -> dict[str, Any]:
        self._fixture_sequence += 1
        owner = self._actor(
            offset=100_000 + self._fixture_sequence,
            label=f"{label}_owner",
            role="business_owner",
        )
        business = self.client.app.state.business_repository.create_business(
            owner_user_id=owner["user"]["id"],
            business_name=f"Casa Local {self.run_id} {label}",
            rif=self._synthetic_rif(f"{self.run_id}:{label}"),
            address="Av Local 1",
            phone="0414 1234567",
            country="VE",
        )
        with connect(self.db_url) as conn:
            conn.execute(
                """
                update businesses
                set verification_status = 'approved',
                    approved_at = now(),
                    min_order_amount_usd = 20.00,
                    max_order_amount_usd = 1000.00,
                    daily_limit_usd = 1000.00,
                    active_order_limit = %s,
                    is_accepting_orders = true,
                    updated_at = now()
                where id = %s
                """,
                (active_order_limit, business.id),
            )
            conn.commit()
        owner_record = self.client.app.state.user_repository.get_user_by_id(
            owner["user"]["id"]
        )
        link = self.client.app.state.business_repository.create_access_link(
            business_id=business.id,
            user_id=owner["user"]["id"],
            telegram_id_snapshot=owner_record.telegram_id,
            role_in_business="owner",
            linked_by_admin_id=admin["user"]["id"],
            reason="47P0 synthetic local owner link",
        )
        self.client.app.state.business_repository.set_access_link_pin_hash(
            link_id=link.id,
            pin_hash=hash_pin("1234"),
        )
        self.client.app.state.business_repository.mark_access_link_pin_verified(
            link_id=link.id,
            unlocked_until=utc_now() + timedelta(minutes=30),
        )
        methods: list[dict[str, str]] = []
        for index, method_type in enumerate(method_types):
            if method_type == "zelle":
                account_value = f"{label}-{index}@example.local"
                account_masked = "***@example.local"
                network = None
            elif method_type == "usdt_trc20":
                account_value = self._synthetic_wallet(
                    f"{self.run_id}:{label}:{index}"
                )
                account_masked = f"{account_value[:5]}...{account_value[-4:]}"
                network = "TRC20"
            else:
                raise ValueError(f"unsupported local method fixture: {method_type}")
            payment = self.client.app.state.business_repository.add_payment_method(
                business_id=business.id,
                method_type=method_type,
                network=network,
                account_value=account_value,
                account_masked=account_masked,
                holder_name="Owner Local",
            )
            self.activate_payment_method(payment.id, business.id)
            methods.append({"id": payment.id, "type": method_type})
        self.client.app.state.capacity_repository.set_declared_capacity(
            business_id=business.id,
            amount_usd=declared_capacity_usd,
            actor_user_id=owner["user"]["id"],
        )
        self._request_data(
            "setup",
            f"setup:credits:{label}",
            "POST",
            "/api/v1/admin/credits/adjust",
            headers=self.headers(
                admin,
                f"47p0_credit_{label}",
                content_type=True,
            ),
            json={
                "business_id": business.id,
                "amount": credits,
                "direction": "add",
                "reason": "47p0_local_baseline_seed",
            },
        )
        return {
            "owner": owner,
            "business_id": business.id,
            "methods": methods,
        }

    def _method_id(self, fixture: dict[str, Any], method_type: str, index: int = 0) -> str:
        matching = [item["id"] for item in fixture["methods"] if item["type"] == method_type]
        return matching[index]

    def _create_ad(
        self,
        *,
        phase: str,
        owner: dict,
        payment_method_id: str,
        payment_method: str,
        label: str,
        amount_max_usd: str = "50.00",
    ) -> dict[str, Any]:
        return self._request_data(
            phase,
            f"ads:create:{label}",
            "POST",
            "/api/v1/business/ads",
            headers=self.headers(owner, f"47p0_ad_{label}", content_type=True),
            json={
                "payment_method_id": payment_method_id,
                "payment_method": payment_method,
                "delivery_method": "pago_movil_ve",
                "rate_bs_per_usd": "39.5000",
                "amount_min_usd": "20.00",
                "amount_max_usd": amount_max_usd,
            },
        )["ad"]

    def _create_order(
        self,
        *,
        phase: str,
        remitter: dict,
        ad_id: str,
        label: str,
    ) -> dict[str, Any]:
        return self._request_data(
            phase,
            f"orders:create:{label}",
            "POST",
            "/api/v1/orders",
            headers=self.headers(
                remitter,
                f"47p0_order_{label}",
                content_type=True,
            ),
            json={"ad_id": ad_id, "amount_usd": "50.00"},
        )["order"]

    def _run_functional_flow(
        self,
        *,
        method_type: str,
        owner: dict,
        remitter: dict,
        ad: dict[str, Any],
        rating_stars: int,
        include_evidence: bool,
    ) -> dict[str, Any]:
        label = method_type.replace("_trc20", "")
        order = self._create_order(
            phase="functional",
            remitter=remitter,
            ad_id=ad["id"],
            label=label,
        )
        self._request_data(
            "functional",
            f"chat:client_message:{label}",
            "POST",
            f"/api/v1/orders/{order['id']}/messages",
            headers=self.headers(
                remitter,
                f"47p0_client_message_{label}",
                content_type=True,
            ),
            json={"body": "Mensaje sintetico local del cliente", "attachment_ids": []},
        )
        self._request_data(
            "functional",
            f"chat:business_message:{label}",
            "POST",
            f"/api/v1/orders/{order['id']}/messages",
            headers=self.headers(
                owner,
                f"47p0_business_message_{label}",
                content_type=True,
            ),
            json={"body": "Mensaje sintetico local del negocio", "attachment_ids": []},
        )
        self._request_data(
            "functional",
            f"chat:share_payment_details:{label}",
            "POST",
            f"/api/v1/orders/{order['id']}/share-payment-details",
            headers=self.headers(owner, f"47p0_share_{label}"),
        )
        client_thread = self._request_response(
            "functional",
            f"chat:list_client:{label}",
            "GET",
            f"/api/v1/orders/{order['id']}/messages?limit=50",
            headers=self.bearer(remitter, f"47p0_chat_client_{label}"),
        )
        self._require_no_store(client_thread, label=f"chat_client_{label}")
        instructions = self._request_response(
            "functional",
            f"orders:payment_instructions:{label}",
            "GET",
            f"/api/v1/orders/{order['id']}/payment-instructions",
            headers=self.bearer(remitter, f"47p0_instructions_{label}"),
        )
        self._require_no_store(instructions, label=f"payment_instructions_{label}")

        evidence: dict[str, Any] | None = None
        if include_evidence:
            evidence_response = self._request_response(
                "functional",
                f"orders:payment_evidence:{label}",
                "POST",
                f"/api/v1/orders/{order['id']}/payment-evidence",
                headers=self.headers(remitter, f"47p0_evidence_{label}"),
                data={"file_type": "payment_evidence"},
                files={
                    "file": (
                        "proof.png",
                        f"47p0-proof-{self.run_id}-{label}".encode("utf-8"),
                        "image/png",
                    )
                },
            )
            self._require_no_store(evidence_response, label=f"payment_evidence_{label}")
            evidence = evidence_response.json()["data"]

        payment_payload: dict[str, Any] = {
            "payment_type": method_type,
            "payment_amount": "50.00",
        }
        if method_type == "usdt_trc20":
            payment_payload.update(
                {
                    "tx_hash": hashlib.sha256(
                        f"{self.run_id}:{order['id']}".encode("utf-8")
                    ).hexdigest(),
                    "network": "TRC20",
                }
            )
        elif evidence is not None:
            payment_payload.update(
                {
                    "proof_file_id": evidence["file"]["id"],
                    "pending_payment_report_id": evidence[
                        "pending_payment_report_id"
                    ],
                }
            )
        report = self._request_data(
            "functional",
            f"orders:payment_report:{label}",
            "POST",
            f"/api/v1/orders/{order['id']}/payment-report",
            headers=self.headers(
                remitter,
                f"47p0_report_{label}",
                content_type=True,
            ),
            json=payment_payload,
        )
        business_thread = self._request_response(
            "functional",
            f"chat:list_business:{label}",
            "GET",
            f"/api/v1/orders/{order['id']}/messages?limit=50",
            headers=self.bearer(owner, f"47p0_chat_business_{label}"),
        )
        self._require_no_store(business_thread, label=f"chat_business_{label}")
        if evidence is not None:
            view = self._request_response(
                "functional",
                f"orders:payment_evidence_view:{label}",
                "POST",
                f"/api/v1/orders/{order['id']}/message-attachments/"
                f"{evidence['file']['id']}/view-url",
                headers=self.headers(owner, f"47p0_view_evidence_{label}"),
            )
            self._require_no_store(view, label=f"payment_evidence_view_{label}")

        confirmed = self._request_data(
            "functional",
            f"business:confirm_payment:{label}",
            "POST",
            f"/api/v1/business/orders/{order['id']}/confirm-payment",
            headers=self.headers(
                owner,
                f"47p0_confirm_{label}",
                content_type=True,
            ),
            json={"reason": "Pago recibido en baseline local"},
        )
        self._request_data(
            "functional",
            f"orders:receiver_details_share:{label}",
            "PUT",
            f"/api/v1/orders/{order['id']}/receiver-details",
            headers=self.headers(
                remitter,
                f"47p0_receiver_{label}",
                content_type=True,
            ),
            json=RECEIVER_DETAILS,
        )
        receiver_reveal = self._request_response(
            "functional",
            f"business:receiver_details_reveal:{label}",
            "GET",
            f"/api/v1/orders/{order['id']}/receiver-details",
            headers=self.bearer(owner, f"47p0_reveal_receiver_{label}"),
        )
        self._require_no_store(receiver_reveal, label=f"receiver_details_{label}")
        delivered = self._request_data(
            "functional",
            f"business:mark_delivered:{label}",
            "POST",
            f"/api/v1/business/orders/{order['id']}/mark-delivered",
            headers=self.headers(
                owner,
                f"47p0_delivered_{label}",
                content_type=True,
            ),
            json={"reason": "Pago movil enviado en baseline local"},
        )
        completed = self._request_data(
            "functional",
            f"orders:confirm_received:{label}",
            "POST",
            f"/api/v1/orders/{order['id']}/confirm-received",
            headers=self.headers(remitter, f"47p0_received_{label}"),
        )
        rating = self._request_data(
            "functional",
            f"orders:rating:{label}",
            "POST",
            f"/api/v1/orders/{order['id']}/rating",
            headers=self.headers(
                remitter,
                f"47p0_rating_{label}",
                content_type=True,
            ),
            json={"stars": rating_stars},
        )
        final_thread = self._request_response(
            "functional",
            f"chat:list_completed:{label}",
            "GET",
            f"/api/v1/orders/{order['id']}/messages?limit=50",
            headers=self.bearer(remitter, f"47p0_chat_completed_{label}"),
        )
        self._require_no_store(final_thread, label=f"chat_completed_{label}")

        if report["order"]["status"] != "payment_reported":
            self._violations.append(f"functional:{label}:payment_reported")
        if confirmed["order"]["status"] != "payment_confirmed":
            self._violations.append(f"functional:{label}:payment_confirmed")
        if delivered["order"]["status"] != "delivered":
            self._violations.append(f"functional:{label}:delivered")
        if completed["order"]["status"] != "completed":
            self._violations.append(f"functional:{label}:completed")
        rating_record = rating.get("rating", {})
        rated = rating_record.get("stars") == rating_stars
        if not rated:
            self._violations.append(f"functional:{label}:rating")
        return {
            "method": method_type,
            "completed": completed["order"]["status"] == "completed",
            "rated": rated,
            "proof_exercised": include_evidence,
        }

    def run_functional(self) -> dict[str, Any]:
        admin = self._actor(offset=90_001, label="47p0_admin", role="admin")
        business = self._business_fixture(
            admin=admin,
            label="functional",
            method_types=("zelle", "usdt_trc20"),
            declared_capacity_usd=Decimal("100.00"),
            credits=6,
        )
        owner = business["owner"]
        zelle_ad = self._create_ad(
            phase="functional",
            owner=owner,
            payment_method_id=self._method_id(business, "zelle"),
            payment_method="zelle",
            label="functional_zelle",
        )
        usdt_ad = self._create_ad(
            phase="functional",
            owner=owner,
            payment_method_id=self._method_id(business, "usdt_trc20"),
            payment_method="usdt_trc20",
            label="functional_usdt",
        )
        self._request_data(
            "functional",
            "business:profile",
            "GET",
            "/api/v1/businesses/me",
            headers=self.bearer(owner, "47p0_business_profile"),
        )
        self._request_data(
            "functional",
            "business:capacity",
            "GET",
            "/api/v1/business/capacity",
            headers=self.bearer(owner, "47p0_business_capacity"),
        )
        zelle_remitter = self._actor(offset=90_010, label="47p0_zelle_client")
        usdt_remitter = self._actor(offset=90_011, label="47p0_usdt_client")
        flows = [
            self._run_functional_flow(
                method_type="zelle",
                owner=owner,
                remitter=zelle_remitter,
                ad=zelle_ad,
                rating_stars=5,
                include_evidence=True,
            ),
            self._run_functional_flow(
                method_type="usdt_trc20",
                owner=owner,
                remitter=usdt_remitter,
                ad=usdt_ad,
                rating_stars=4,
                include_evidence=False,
            ),
        ]
        business_orders = self._request_data(
            "functional",
            "business:orders",
            "GET",
            "/api/v1/business/orders?limit=20",
            headers=self.bearer(owner, "47p0_business_orders"),
        )
        ticket = self._request_data(
            "functional",
            "support:create_ticket",
            "POST",
            "/api/v1/support/tickets",
            headers={
                **self.headers(
                    zelle_remitter,
                    "47p0_support_ticket",
                    content_type=True,
                ),
                "X-NODO-Surface": "client_mini_app",
            },
            json={
                "scope": "client_general",
                "category": "technical_issue",
                "subject": "Baseline local",
                "message": "Ticket sintetico para validar headers privados.",
            },
        )
        support_list = self._request_response(
            "functional",
            "support:list",
            "GET",
            "/api/v1/support/tickets?limit=20",
            headers=self.bearer(zelle_remitter, "47p0_support_list"),
        )
        self._require_no_store(support_list, label="support_list")
        support_detail = self._request_response(
            "functional",
            "support:detail",
            "GET",
            f"/api/v1/support/tickets/{ticket['id']}",
            headers=self.bearer(zelle_remitter, "47p0_support_detail"),
        )
        self._require_no_store(support_detail, label="support_detail")
        return {
            "flows": flows,
            "business_order_count": len(business_orders["items"]),
            "support_header_checks": 2,
        }

    async def _async_request(
        self,
        client: httpx.AsyncClient,
        *,
        name: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        started_at = time.perf_counter()
        response = await client.request(method, path, **kwargs)
        self._record_response(
            phase="concurrency",
            name=name,
            method=method,
            path=path,
            response=response,
            started_at=started_at,
        )
        return response

    @staticmethod
    def _safe_error_code(response: httpx.Response) -> str | None:
        if response.status_code < 400:
            return None
        try:
            return response.json().get("error", {}).get("code", "UNKNOWN_ERROR")
        except ValueError:
            return "NON_JSON_ERROR"

    def _db_counts(self, order_id: str) -> dict[str, Any]:
        with connect(self.db_url, row_factory=psycopg.rows.dict_row) as conn:
            order = conn.execute(
                "select status from orders where id = %s",
                (order_id,),
            ).fetchone()
            report_count = conn.execute(
                "select count(*) as count from payment_reports where order_id = %s",
                (order_id,),
            ).fetchone()["count"]
            reservation = conn.execute(
                "select status from business_capacity_reservations where order_id = %s",
                (order_id,),
            ).fetchone()
        return {
            "status": order["status"],
            "payment_reports": int(report_count),
            "reservation_status": reservation["status"] if reservation else None,
        }

    def _setup_reported_order(
        self,
        *,
        admin: dict,
        label: str,
    ) -> dict[str, Any]:
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
        remitter = self._actor(
            offset=200_000 + self._fixture_sequence,
            label=f"{label}_client",
        )
        order = self._create_order(
            phase="setup",
            remitter=remitter,
            ad_id=ad["id"],
            label=label,
        )
        self._request_data(
            "setup",
            f"setup:share:{label}",
            "POST",
            f"/api/v1/orders/{order['id']}/share-payment-details",
            headers=self.headers(fixture["owner"], f"47p0_setup_share_{label}"),
        )
        report = self._request_data(
            "setup",
            f"setup:report:{label}",
            "POST",
            f"/api/v1/orders/{order['id']}/payment-report",
            headers=self.headers(
                remitter,
                f"47p0_setup_report_{label}",
                content_type=True,
            ),
            json={"payment_type": "zelle", "payment_amount": "50.00"},
        )
        if report["order"]["status"] != "payment_reported":
            raise RuntimeError(f"{label} did not reach payment_reported")
        return {
            "owner": fixture["owner"],
            "business_id": fixture["business_id"],
            "remitter": remitter,
            "order": order,
        }

    async def _same_ad_race(self, admin: dict) -> dict[str, Any]:
        fixture = self._business_fixture(
            admin=admin,
            label="same_ad_race",
            method_types=("zelle",),
            declared_capacity_usd=Decimal("50.00"),
            credits=3,
        )
        ad = self._create_ad(
            phase="setup",
            owner=fixture["owner"],
            payment_method_id=self._method_id(fixture, "zelle"),
            payment_method="zelle",
            label="same_ad_race",
        )
        remitters = [
            self._actor(offset=300_000 + index, label=f"same_ad_client_{index}")
            for index in range(self.same_ad_requests)
        ]
        transport = httpx.ASGITransport(app=self.client.app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            responses = await asyncio.gather(
                *[
                    self._async_request(
                        client,
                        name="concurrency:orders:same_ad",
                        method="POST",
                        path="/api/v1/orders",
                        headers=self.headers(
                            remitter,
                            f"47p0_same_ad_{index}",
                            content_type=True,
                        ),
                        json={"ad_id": ad["id"], "amount_usd": "50.00"},
                    )
                    for index, remitter in enumerate(remitters)
                ]
            )
        successful = [response for response in responses if response.status_code == 201]
        with connect(self.db_url, row_factory=psycopg.rows.dict_row) as conn:
            order_count = conn.execute(
                "select count(*) as count from orders where ad_id = %s",
                (ad["id"],),
            ).fetchone()["count"]
            reservation_count = conn.execute(
                """
                select count(*) as count
                from business_capacity_reservations reservation
                join orders on orders.id = reservation.order_id
                where orders.ad_id = %s
                """,
                (ad["id"],),
            ).fetchone()["count"]
        passed = len(successful) == 1 and int(order_count) == 1 and int(reservation_count) == 1
        if not passed:
            self._violations.append("concurrency:same_ad")
        return {
            "requested": self.same_ad_requests,
            "successful": len(successful),
            "expected_conflicts": sum(response.status_code == 409 for response in responses),
            "unexpected_statuses": sorted(
                response.status_code
                for response in responses
                if response.status_code not in {201, 409}
            ),
            "safe_error_codes": sorted(
                {
                    code
                    for response in responses
                    if (code := self._safe_error_code(response)) is not None
                }
            ),
            "db_order_count": int(order_count),
            "db_reservation_count": int(reservation_count),
            "passed": passed,
        }

    async def _ad_publish_race(
        self,
        *,
        admin: dict,
        label: str,
        method_types: tuple[str, str],
        amount_max_usd: str,
    ) -> dict[str, Any]:
        fixture = self._business_fixture(
            admin=admin,
            label=label,
            method_types=method_types,
            declared_capacity_usd=Decimal("100.00"),
            credits=4,
        )
        payloads = []
        method_offsets: dict[str, int] = {}
        for method_type in method_types:
            index = method_offsets.get(method_type, 0)
            method_offsets[method_type] = index + 1
            payloads.append(
                {
                    "payment_method_id": self._method_id(
                        fixture,
                        method_type,
                        index=index,
                    ),
                    "payment_method": method_type,
                    "delivery_method": "pago_movil_ve",
                    "rate_bs_per_usd": "39.5000",
                    "amount_min_usd": "20.00",
                    "amount_max_usd": amount_max_usd,
                }
            )
        transport = httpx.ASGITransport(app=self.client.app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            responses = await asyncio.gather(
                *[
                    self._async_request(
                        client,
                        name=f"concurrency:ads:{label}",
                        method="POST",
                        path="/api/v1/business/ads",
                        headers=self.headers(
                            fixture["owner"],
                            f"47p0_{label}_{index}",
                            content_type=True,
                        ),
                        json=payload,
                    )
                    for index, payload in enumerate(payloads)
                ]
            )
        with connect(self.db_url, row_factory=psycopg.rows.dict_row) as conn:
            row = conn.execute(
                """
                select count(*) as active_count,
                       coalesce(sum(amount_max_usd), 0.00) as committed_max
                from ads
                where business_id = %s and status in ('active', 'in_order')
                """,
                (fixture["business_id"],),
            ).fetchone()
        successful = sum(response.status_code == 201 for response in responses)
        committed_max = Decimal(str(row["committed_max"]))
        passed = successful == 1 and int(row["active_count"]) == 1 and committed_max <= Decimal("100.00")
        if not passed:
            self._violations.append(f"concurrency:{label}")
        return {
            "successful": successful,
            "expected_conflicts": sum(response.status_code == 409 for response in responses),
            "safe_error_codes": sorted(
                {
                    code
                    for response in responses
                    if (code := self._safe_error_code(response)) is not None
                }
            ),
            "db_active_count": int(row["active_count"]),
            "db_committed_max_usd": str(committed_max),
            "passed": passed,
        }

    async def _double_confirm_and_completion(self, admin: dict) -> dict[str, Any]:
        prepared = self._setup_reported_order(admin=admin, label="double_transition")
        order_id = prepared["order"]["id"]
        transport = httpx.ASGITransport(app=self.client.app)
        shared_key = "47p0_double_confirm"
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            confirm_responses = await asyncio.gather(
                *[
                    self._async_request(
                        client,
                        name="concurrency:business:confirm_payment",
                        method="POST",
                        path=f"/api/v1/business/orders/{order_id}/confirm-payment",
                        headers={
                            **self.headers(
                                prepared["owner"],
                                shared_key,
                                content_type=True,
                            ),
                            "X-Request-Id": f"req_{self.run_id}_double_confirm_{index}",
                        },
                        json={"reason": "Pago recibido en carrera local"},
                    )
                    for index in range(2)
                ]
            )
        self._request_data(
            "setup",
            "setup:receiver_details:double_transition",
            "PUT",
            f"/api/v1/orders/{order_id}/receiver-details",
            headers=self.headers(
                prepared["remitter"],
                "47p0_double_receiver",
                content_type=True,
            ),
            json=RECEIVER_DETAILS,
        )
        self._request_data(
            "setup",
            "setup:delivered:double_transition",
            "POST",
            f"/api/v1/business/orders/{order_id}/mark-delivered",
            headers=self.headers(
                prepared["owner"],
                "47p0_double_delivered",
                content_type=True,
            ),
            json={"reason": "Pago movil enviado en carrera local"},
        )
        completion_key = "47p0_double_completion"
        transport = httpx.ASGITransport(app=self.client.app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            completion_responses = await asyncio.gather(
                *[
                    self._async_request(
                        client,
                        name="concurrency:orders:confirm_received",
                        method="POST",
                        path=f"/api/v1/orders/{order_id}/confirm-received",
                        headers={
                            **self.headers(prepared["remitter"], completion_key),
                            "X-Request-Id": f"req_{self.run_id}_double_completion_{index}",
                        },
                    )
                    for index in range(2)
                ]
            )
        with connect(self.db_url, row_factory=psycopg.rows.dict_row) as conn:
            confirmed_events = conn.execute(
                "select count(*) as count from order_state_events where order_id = %s and event_type = 'payment_confirmed'",
                (order_id,),
            ).fetchone()["count"]
            consumed_ledgers = conn.execute(
                "select count(*) as count from credits_ledger where related_order_id = %s and type = 'consume'",
                (order_id,),
            ).fetchone()["count"]
            completed_events = conn.execute(
                "select count(*) as count from order_state_events where order_id = %s and event_type = 'order_completed'",
                (order_id,),
            ).fetchone()["count"]
            reservation = conn.execute(
                "select status from business_capacity_reservations where order_id = %s",
                (order_id,),
            ).fetchone()
        confirm_ok = sum(response.status_code == 200 for response in confirm_responses) >= 1
        completion_ok = sum(response.status_code == 200 for response in completion_responses) >= 1
        passed = (
            confirm_ok
            and completion_ok
            and int(confirmed_events) == 1
            and int(consumed_ledgers) == 1
            and int(completed_events) == 1
            and reservation["status"] == "consumed"
        )
        if not passed:
            self._violations.append("concurrency:double_transitions")
        return {
            "confirm_statuses": sorted(response.status_code for response in confirm_responses),
            "completion_statuses": sorted(response.status_code for response in completion_responses),
            "payment_confirmed_events": int(confirmed_events),
            "credit_consume_rows": int(consumed_ledgers),
            "completed_events": int(completed_events),
            "reservation_status": reservation["status"],
            "passed": passed,
        }

    async def _payment_cancel_race(self, admin: dict) -> dict[str, Any]:
        fixture = self._business_fixture(
            admin=admin,
            label="payment_cancel_race",
            method_types=("zelle",),
            declared_capacity_usd=Decimal("50.00"),
            credits=3,
        )
        ad = self._create_ad(
            phase="setup",
            owner=fixture["owner"],
            payment_method_id=self._method_id(fixture, "zelle"),
            payment_method="zelle",
            label="payment_cancel_race",
        )
        remitter = self._actor(offset=410_001, label="payment_cancel_client")
        order = self._create_order(
            phase="setup",
            remitter=remitter,
            ad_id=ad["id"],
            label="payment_cancel_race",
        )
        self._request_data(
            "setup",
            "setup:share:payment_cancel_race",
            "POST",
            f"/api/v1/orders/{order['id']}/share-payment-details",
            headers=self.headers(fixture["owner"], "47p0_cancel_share"),
        )
        transport = httpx.ASGITransport(app=self.client.app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            report_response, cancel_response = await asyncio.gather(
                self._async_request(
                    client,
                    name="concurrency:orders:payment_vs_cancel:report",
                    method="POST",
                    path=f"/api/v1/orders/{order['id']}/payment-report",
                    headers=self.headers(
                        remitter,
                        "47p0_payment_cancel_report",
                        content_type=True,
                    ),
                    json={"payment_type": "zelle", "payment_amount": "50.00"},
                ),
                self._async_request(
                    client,
                    name="concurrency:orders:payment_vs_cancel:cancel",
                    method="POST",
                    path=f"/api/v1/orders/{order['id']}/cancel",
                    headers=self.headers(
                        remitter,
                        "47p0_payment_cancel_cancel",
                        content_type=True,
                    ),
                    json={
                        "reason": "choose_another_business",
                        "payment_not_sent_confirmed": True,
                    },
                ),
            )
        counts = self._db_counts(order["id"])
        winners = sum(response.status_code in {200, 201} for response in (report_response, cancel_response))
        consistent = (
            counts["status"] == "payment_reported"
            and counts["payment_reports"] == 1
            and counts["reservation_status"] == "reserved"
        ) or (
            counts["status"] == "cancelled"
            and counts["payment_reports"] == 0
            and counts["reservation_status"] == "released"
        )
        passed = winners == 1 and consistent
        if not passed:
            self._violations.append("concurrency:payment_cancel")
        return {
            "statuses": sorted([report_response.status_code, cancel_response.status_code]),
            "winner_count": winners,
            "db": counts,
            "passed": passed,
        }

    async def _payment_expiration_race(self, admin: dict) -> dict[str, Any]:
        fixture = self._business_fixture(
            admin=admin,
            label="payment_expiration_race",
            method_types=("zelle",),
            declared_capacity_usd=Decimal("50.00"),
            credits=3,
        )
        ad = self._create_ad(
            phase="setup",
            owner=fixture["owner"],
            payment_method_id=self._method_id(fixture, "zelle"),
            payment_method="zelle",
            label="payment_expiration_race",
        )
        remitter = self._actor(offset=420_001, label="payment_expiration_client")
        order = self._create_order(
            phase="setup",
            remitter=remitter,
            ad_id=ad["id"],
            label="payment_expiration_race",
        )
        self._request_data(
            "setup",
            "setup:share:payment_expiration_race",
            "POST",
            f"/api/v1/orders/{order['id']}/share-payment-details",
            headers=self.headers(fixture["owner"], "47p0_expiration_share"),
        )
        deadline = utc_now() + timedelta(seconds=2)
        with connect(self.db_url) as conn:
            conn.execute(
                "update orders set payment_report_deadline_at = %s, expires_at = %s where id = %s",
                (deadline, deadline, order["id"]),
            )
            conn.commit()

        async def run_worker() -> dict[str, Any]:
            return await asyncio.to_thread(
                self.client.app.state.expire_and_escalate_orders_worker.run,
                current_time=deadline + timedelta(seconds=1),
                batch_size=50,
                dry_run=False,
                request_id=f"47p0_expiration_race_{self.run_id}",
            )

        transport = httpx.ASGITransport(app=self.client.app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            report_response, worker_result = await asyncio.gather(
                self._async_request(
                    client,
                    name="concurrency:orders:payment_vs_expiration:report",
                    method="POST",
                    path=f"/api/v1/orders/{order['id']}/payment-report",
                    headers=self.headers(
                        remitter,
                        "47p0_expiration_report",
                        content_type=True,
                    ),
                    json={"payment_type": "zelle", "payment_amount": "50.00"},
                ),
                run_worker(),
            )
        counts = self._db_counts(order["id"])
        consistent = (
            counts["status"] == "payment_reported"
            and counts["payment_reports"] == 1
            and counts["reservation_status"] == "reserved"
        ) or (
            counts["status"] == "cancelled"
            and counts["payment_reports"] == 0
            and counts["reservation_status"] == "released"
        )
        worker_status = worker_result.get("job_run", {}).get("status")
        passed = (
            report_response.status_code in {201, 409}
            and consistent
            and worker_status in {"finished", "skipped"}
        )
        if not passed:
            self._violations.append("concurrency:payment_expiration")
        return {
            "report_status": report_response.status_code,
            "worker_status": worker_status,
            "db": counts,
            "passed": passed,
        }

    async def _run_concurrency_async(self) -> dict[str, Any]:
        admin = self._actor(offset=190_001, label="47p0_concurrency_admin", role="admin")
        return {
            "same_ad_50_clients": await self._same_ad_race(admin),
            "same_method_ad_publish": await self._ad_publish_race(
                admin=admin,
                label="same_method_publish",
                method_types=("zelle", "zelle"),
                amount_max_usd="40.00",
            ),
            "shared_capacity_ad_publish": await self._ad_publish_race(
                admin=admin,
                label="shared_capacity_publish",
                method_types=("zelle", "usdt_trc20"),
                amount_max_usd="60.00",
            ),
            "double_confirm_and_completion": await self._double_confirm_and_completion(admin),
            "payment_vs_cancel": await self._payment_cancel_race(admin),
            "payment_vs_expiration": await self._payment_expiration_race(admin),
        }

    def run_concurrency(self) -> dict[str, Any]:
        return asyncio.run(self._run_concurrency_async())

    def _phase_summary(self, phase: str) -> dict[str, Any]:
        return self._phase_metrics[phase].summary(
            started_at=self._phase_started[phase]
        )

    def run_baseline(self, *, scenario: str) -> dict[str, Any]:
        functional = self.run_functional() if scenario in {"functional", "all"} else None
        concurrency = self.run_concurrency() if scenario in {"concurrency", "all"} else None
        metrics = {
            phase: self._phase_summary(phase) for phase in self._phase_metrics
        }
        return {
            "slice": "47P0",
            "phase": "local_p2p_baseline",
            "run_id": self.run_id,
            "scenario": scenario,
            "environment": {
                "app_env": "local",
                "database": "local_postgresql",
                "redis": "local_redis",
                "storage": "local_private_storage",
                "external_providers": False,
            },
            "functional": functional,
            "concurrency": concurrency,
            "metrics": metrics,
            "private_header_checks": self._header_checks,
            "safe_steps": self._safe_steps,
            "query_families_for_47p3": [
                "marketplace_capacity_lateral",
                "surface_attention_updated_at",
                "order_messages_latest_window",
                "support_list_and_detail",
                "business_dashboard_aggregates",
            ],
            "invariant_violations": self._violations,
            "cost": "local_machine_only",
            "exit_code": 1 if self._violations else 0,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument(
        "--scenario",
        choices=("functional", "concurrency", "all"),
        default="all",
    )
    parser.add_argument("--same-ad-requests", type=int, default=50)
    parser.add_argument("--run-id", default=f"47p0_{int(time.time())}")
    parser.add_argument(
        "--output",
        default="evidence/slice_runs/slice_47P0_local_baseline.json",
    )
    args = parser.parse_args()
    if not 2 <= args.same_ad_requests <= 100:
        raise SystemExit("--same-ad-requests must be between 2 and 100")
    baseline = P2PBaselineLocal(
        env_file=Path(args.env_file),
        run_id=args.run_id,
        same_ad_requests=args.same_ad_requests,
    )
    payload = baseline.run_baseline(scenario=args.scenario)
    write_json(Path(args.output), payload)
    print(
        json.dumps(
            {
                "slice": payload["slice"],
                "run_id": payload["run_id"],
                "scenario": payload["scenario"],
                "exit_code": payload["exit_code"],
                "invariant_violations": payload["invariant_violations"],
                "output": str(args.output),
            },
            indent=2,
        )
    )
    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
