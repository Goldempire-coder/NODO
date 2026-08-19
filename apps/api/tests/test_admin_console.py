from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient


BOT_TOKEN = "123456:test-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-09",
        "NODO_BUILD_ID": "pytest-admin-console-build",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
        "BOT_TOKEN": BOT_TOKEN,
        "JWT_SECRET": JWT_SECRET,
        "JWT_REFRESH_SECRET": JWT_REFRESH_SECRET,
        "AUTH_INIT_DATA_MAX_AGE_SECONDS": "86400",
        "ACCESS_TOKEN_TTL_SECONDS": "900",
        "REFRESH_TOKEN_TTL_SECONDS": "2592000",
        "AUTH_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "AUTH_RATE_LIMIT_WINDOW_SECONDS": "60",
        "BUSINESS_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "BUSINESS_RATE_LIMIT_WINDOW_SECONDS": "60",
    }
    values.update(overrides)
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app  # noqa: E402
from app.core.config import load_settings  # noqa: E402
from app.modules.admin.service import AdminService  # noqa: E402
from app.modules.businesses.models import utc_now  # noqa: E402
from app.modules.businesses.pin_security import hash_pin  # noqa: E402
from app.modules.users.models import UserRecord  # noqa: E402
from app.shared.cache import InMemoryTTLCache  # noqa: E402
from photo_test_data import png_bytes  # noqa: E402


def _client(**env_overrides: str) -> TestClient:
    _set_env(**env_overrides)
    return TestClient(create_app())


def _signed_init_data(telegram_id: int, username: str) -> str:
    payload = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": telegram_id, "username": username, "first_name": username}, separators=(",", ":"), sort_keys=True),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


def _login(client: TestClient, telegram_id: int, username: str) -> dict:
    response = client.post(
        "/api/v1/auth/telegram",
        headers={"X-Request-Id": f"req_login_{telegram_id}"},
        json={"init_data": _signed_init_data(telegram_id, username)},
    )
    assert response.status_code == 200, response.text
    login = response.json()["data"]
    terms = client.post(
        "/api/v1/users/me/terms-acceptance",
        headers={"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": f"req_terms_{telegram_id}"},
        json={"terms_version": "2026-07-06"},
    )
    assert terms.status_code == 200, terms.text
    login["user"] = terms.json()["data"]
    return login


def _headers(login: dict, key: str = "idem") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {login['access_token']}",
        "X-Request-Id": f"req_{key}",
        "Idempotency-Key": key,
    }


def _bearer(login: dict, key: str = "req") -> dict[str, str]:
    return {"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": key}


def _create_business(client: TestClient, login: dict, key: str) -> dict:
    response = client.post(
        "/api/v1/businesses",
        headers={**_headers(login, key), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": f"Casa {key}", "rif": "J-12345678-9", "address": "Av Principal", "phone": "+584121234567", "country": "VE"},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["business"]


def _approved_business_with_method(client: TestClient, login: dict, *, credits: int = 5) -> tuple[dict, str]:
    business = _create_business(client, login, f"biz_{login['user']['id']}")
    stored_business = client.app.state.business_repository.get_business(business["id"])
    stored_business.verification_status = "approved"
    stored_business.approved_at = stored_business.updated_at
    stored_business.max_order_amount_usd = stored_business.max_order_amount_usd * 20
    stored_user = client.app.state.user_repository.get_user_by_id(login["user"]["id"])
    link = client.app.state.business_repository.create_access_link(
        business_id=business["id"],
        user_id=login["user"]["id"],
        telegram_id_snapshot=stored_user.telegram_id,
        role_in_business="owner",
        linked_by_admin_id=login["user"]["id"],
        reason="test_active_business_access",
    )
    client.app.state.business_repository.set_access_link_pin_hash(link_id=link.id, pin_hash=hash_pin("1234"))
    client.app.state.business_repository.mark_access_link_pin_verified(link_id=link.id, unlocked_until=utc_now() + timedelta(minutes=15))
    payment = client.app.state.business_repository.add_payment_method(
        business_id=business["id"],
        method_type="zelle",
        network=None,
        account_value="owner@example.com",
        account_masked="***.com",
        holder_name="Owner Test",
    )
    payment.verified_status = "approved"
    payment.active = True
    if credits:
        client.app.state.ad_repository.grant_test_credits(business_id=business["id"], amount=credits, created_by=login["user"]["id"])
    return business, payment.id


def _create_ad(client: TestClient, owner: dict, payment_method_id: str, *, key: str = "ad") -> dict:
    response = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, key), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment_method_id,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "20.00",
            "amount_max_usd": "100.00",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["ad"]


def _create_order(client: TestClient, remitter: dict, ad_id: str, *, key: str = "order") -> dict:
    response = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, key), "Content-Type": "application/json"},
        json={
            "ad_id": ad_id,
            "amount_usd": "50.00",
            "receiver_data": {"bank": "Banco", "phone": "+584121234567", "document": "V12345678", "holder": "Receptor Test"},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["order"]


def _upload_payment_evidence(client: TestClient, remitter: dict, order_id: str, key: str = "evidence") -> dict:
    content = png_bytes(f"proof:{order_id}:{key}".encode("utf-8"))
    response = client.post(
        f"/api/v1/orders/{order_id}/payment-evidence",
        headers=_headers(remitter, key),
        data={"file_type": "payment_evidence"},
        files={"file": ("proof.png", content, "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _report_payment(client: TestClient, remitter: dict, order: dict, *, key: str = "report") -> dict:
    stored_order = client.app.state.order_repository.get_by_id(order["id"])
    business = client.app.state.business_repository.get_business(
        stored_order.business_id
    )
    client.app.state.chat_repository.create_configured_payment_message_once(
        order_id=order["id"],
        sender_user_id=business.owner_user_id,
        body="Zelle del negocio: owner@example.com",
        account_value="owner@example.com",
        idempotency_key=f"fixture_share_{order['id']}",
    )
    evidence = _upload_payment_evidence(client, remitter, order["id"], key=f"{key}_evidence")
    response = client.post(
        f"/api/v1/orders/{order['id']}/payment-report",
        headers={**_headers(remitter, key), "Content-Type": "application/json"},
        json={
            "payment_type": "zelle",
            "payment_reference": "ABC123456",
            "payment_sender_name": "Remitter Test",
            "payment_sender_account_masked": "***1234",
            "payment_amount": "50.00",
            "proof_file_id": evidence["file"]["id"],
            "pending_payment_report_id": evidence["pending_payment_report_id"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _seed_disputed_order(client: TestClient, *, owner_id: int, remitter_id: int) -> tuple[dict, dict, dict, dict, dict, dict]:
    owner = _login(client, owner_id, f"owner_{owner_id}")
    business, method_id = _approved_business_with_method(client, owner, credits=2)
    ad = _create_ad(client, owner, method_id, key=f"ad_{owner_id}")
    remitter = _login(client, remitter_id, f"remitter_{remitter_id}")
    order = _create_order(client, remitter, ad["id"], key=f"order_{remitter_id}")
    _report_payment(client, remitter, order, key=f"report_{remitter_id}")
    dispute = client.post(
        f"/api/v1/orders/{order['id']}/disputes",
        headers={**_headers(remitter, f"dispute_{remitter_id}"), "Content-Type": "application/json"},
        json={"reason": "business_no_payment_confirmation", "description": "Sin respuesta", "evidence_file_ids": []},
    )
    assert dispute.status_code == 201, dispute.text
    return owner, business, ad, remitter, order, dispute.json()["data"]["dispute"]


def _seed_payment_rejected_order(client: TestClient, *, owner_id: int, remitter_id: int) -> tuple[dict, dict, dict, dict, dict]:
    owner = _login(client, owner_id, f"owner_{owner_id}")
    business, method_id = _approved_business_with_method(client, owner, credits=2)
    ad = _create_ad(client, owner, method_id, key=f"ad_rejected_{owner_id}")
    remitter = _login(client, remitter_id, f"remitter_{remitter_id}")
    order = _create_order(client, remitter, ad["id"], key=f"order_rejected_{remitter_id}")
    _report_payment(client, remitter, order, key=f"report_rejected_{remitter_id}")
    stored_order = client.app.state.order_repository.get_by_id(order["id"])
    stored_report = client.app.state.order_repository.get_submitted_payment_report_for_order(order["id"])
    assert stored_order is not None
    assert stored_report is not None
    client.app.state.order_repository.update_payment_report(stored_report, status="rejected")
    client.app.state.order_repository.update_order(stored_order, status="payment_rejected")
    order["status"] = "payment_rejected"
    return owner, business, ad, remitter, order


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


class _AdminReadModelRepository:
    def __init__(self) -> None:
        self.dashboard_calls = 0
        self.metrics_calls = 0

    def dashboard(self) -> dict:
        self.dashboard_calls += 1
        return {"queues": {"open_disputes": self.dashboard_calls}}

    def metrics(self) -> dict:
        self.metrics_calls += 1
        return {"source": "read_model", "orders": {"total": self.metrics_calls}}


class _AuditSpy:
    def __init__(self) -> None:
        self.events: list[str] = []

    def write(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.events.append(kwargs["event_type"])


class _AllowingRateLimiter:
    def allow(self, *_args, **_kwargs) -> bool:  # type: ignore[no-untyped-def]
        return True


def test_admin_operational_search_links_evidence_without_private_payloads() -> None:
    client = _client()
    admin = _login(client, 1201, "search_admin")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    owner, business, _ad, remitter, order, _dispute = _seed_disputed_order(client, owner_id=1202, remitter_id=1203)
    client.app.state.user_repository.update_profile(remitter["user"]["id"], first_name="Cliente Uno", phone="+17865550123")

    business_record = client.app.state.business_repository.get_business(business["id"])
    business_record.referral_code = "REF-CARLOS-46"
    intake = client.app.state.business_intake_repository.create_or_get_draft(
        telegram_user_id=4512001,
        telegram_chat_id=4512001,
        update_id=1,
        referral_code="REF-CARLOS-46",
    )
    client.app.state.business_intake_repository.submit(
        intake=intake,
        update_id=2,
        business_name="Cambio Centro",
        business_tax_id="J-22222222-2",
        responsible_name="Responsable Test",
        responsible_id_number="V-11111111",
        city="Maracaibo",
        business_phone="+584121111111",
        operation="both",
        banks=["Mercantil"],
        methods=["usdc"],
        min_amount_usd="20.00",
        max_amount_usd="100.00",
        daily_limit_usd="1000.00",
        schedule="online",
        references=["@cambio_centro"],
    )
    ticket = client.app.state.support_repository.create_ticket(
        requester_user_id=remitter["user"]["id"],
        requester_role="remitter",
        requester_surface="client_mini_app",
        scope="client_order",
        category="order_help",
        status="waiting_support",
        priority="normal",
        subject="No recuerdo el negocio exacto",
        business_id=business["id"],
        order_id=order["id"],
    )
    client.app.state.support_repository.create_message(
        ticket_id=ticket.id,
        sender_user_id=remitter["user"]["id"],
        sender_role="remitter",
        body="Pague y escribi una clave privada fuera de la lista",
        visibility="participants",
    )

    phone_search = client.get(
        "/api/v1/admin/investigation/search",
        params={"q": "+17865550123", "limit": "10"},
        headers=_bearer(admin, "req_search_phone"),
    )
    assert phone_search.status_code == 200, phone_search.text
    assert phone_search.headers["Cache-Control"] == "private, no-store"
    phone_data = phone_search.json()["data"]
    assert phone_data["result_counts"]["users"] == 1
    assert phone_data["result_counts"]["orders"] == 1
    assert phone_data["result_counts"]["support_tickets"] == 1
    assert phone_data["groups"]["orders"][0]["action_route"] == f"admin://order/{order['id']}"
    assert phone_data["groups"]["support_tickets"][0]["action_route"] == f"admin://support-ticket/{ticket.id}"

    referral_search = client.get(
        "/api/v1/admin/investigation/search",
        params={"q": "REF-CARLOS-46", "limit": "10"},
        headers=_bearer(admin, "req_search_referral"),
    )
    assert referral_search.status_code == 200, referral_search.text
    referral_data = referral_search.json()["data"]
    assert referral_data["result_counts"]["businesses"] == 1
    assert referral_data["result_counts"]["business_intakes"] == 1
    assert referral_data["groups"]["businesses"][0]["action_route"] == f"admin://business/{business['id']}"
    assert referral_data["groups"]["business_intakes"][0]["action_route"] == f"admin://business-intake/{intake.id}"

    combined = phone_search.text + referral_search.text
    assert "clave privada" not in combined
    assert "owner@example.com" not in combined
    assert "storage_path" not in combined
    assert "file_asset_id" not in combined
    search_events = [event for event in client.app.state.audit_writer.events if event.event_type == "admin_operational_search_performed"]
    assert len(search_events) == 2
    audit_payload = json.dumps([event.metadata_json for event in search_events], sort_keys=True)
    assert "+17865550123" not in audit_payload
    assert "REF-CARLOS-46" not in audit_payload
    assert all(event.metadata_json.get("query_hash") for event in search_events)
    assert owner["user"]["id"]


def test_admin_operational_search_rbac_and_short_queries() -> None:
    client = _client()
    admin = _login(client, 1211, "short_search_admin")
    business_owner = _login(client, 1212, "short_search_owner")
    support = _login(client, 1213, "short_search_support")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    client.app.state.user_repository.set_user_role(business_owner["user"]["id"], "business_owner")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")

    too_short = client.get(
        "/api/v1/admin/investigation/search",
        params={"q": "ab"},
        headers=_bearer(admin, "req_search_short"),
    )
    assert too_short.status_code == 400, too_short.text
    assert too_short.json()["error"]["code"] == "ADMIN_OPERATIONAL_SEARCH_QUERY_TOO_SHORT"

    forbidden = client.get(
        "/api/v1/admin/investigation/search",
        params={"q": "NODO"},
        headers=_bearer(business_owner, "req_search_forbidden"),
    )
    assert forbidden.status_code == 403, forbidden.text

    allowed = client.get(
        "/api/v1/admin/investigation/search",
        params={"q": "NODO"},
        headers=_bearer(support, "req_search_support"),
    )
    assert allowed.status_code == 200, allowed.text


def test_admin_dashboard_metrics_use_cache_but_audit_each_view() -> None:
    settings = load_settings(os.environ)
    repository = _AdminReadModelRepository()
    audit = _AuditSpy()
    service = AdminService(
        settings=settings,
        repository=repository,
        audit_writer=audit,
        rate_limiter=_AllowingRateLimiter(),
        read_model_cache=InMemoryTTLCache(),
    )
    admin = UserRecord(
        id="admin-cache-test",
        telegram_id=990001,
        username="admin_cache",
        first_name="Admin",
        last_name=None,
        role="admin",
        status="active",
    )

    first_dashboard = service.dashboard(user=admin, request_id="req_dashboard_1")
    second_dashboard = service.dashboard(user=admin, request_id="req_dashboard_2")
    first_metrics = service.metrics(user=admin, request_id="req_metrics_1")
    second_metrics = service.metrics(user=admin, request_id="req_metrics_2")

    assert repository.dashboard_calls == 1
    assert repository.metrics_calls == 1
    assert first_dashboard["queues"] == second_dashboard["queues"]
    assert first_metrics["orders"] == second_metrics["orders"]
    assert audit.events.count("admin_viewed_dashboard") == 2
    assert audit.events.count("admin_viewed_metrics") == 2


def test_admin_dashboard_metrics_and_read_rbac_are_masked() -> None:
    client = _client()
    _, _, _, _, _, dispute = _seed_disputed_order(client, owner_id=900, remitter_id=901)
    admin = _login(client, 902, "admin")
    support = _login(client, 903, "support")
    business_owner = _login(client, 904, "business_owner")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")
    client.app.state.user_repository.set_user_role(business_owner["user"]["id"], "business_owner")
    client.post(
        "/api/v1/users/me/profile",
        headers={**_bearer(_login(client, 905, "client_contact"), "req_client_profile"), "Content-Type": "application/json"},
        json={"first_name": "Cliente Contacto", "phone": "+58 414 000 1111"},
    )

    dashboard = client.get("/api/v1/admin/dashboard", headers=_bearer(admin, "req_admin_dashboard"))
    support_metrics = client.get("/api/v1/admin/metrics", headers=_bearer(support, "req_support_metrics"))
    forbidden = client.get("/api/v1/admin/dashboard", headers=_bearer(business_owner, "req_bo_dashboard"))
    disputes = client.get("/api/v1/admin/disputes?limit=20", headers=_bearer(support, "req_support_disputes"))

    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["data"]["queues"]["open_disputes"] == 1
    assert dashboard.headers["Cache-Control"] == "private, no-store"
    assert "users" not in dashboard.json()["data"]
    assert "+58 414 000 1111" not in dashboard.text
    assert support_metrics.status_code == 200, support_metrics.text
    assert support_metrics.json()["data"]["source"] == "read_model"
    assert support_metrics.json()["data"]["table_created"] is False
    assert forbidden.status_code == 403
    assert disputes.status_code == 200, disputes.text
    assert disputes.json()["data"]["items"][0]["id"] == dispute["id"]
    combined = dashboard.text + support_metrics.text + disputes.text
    assert "system_metrics" not in combined
    assert "storage_path" not in combined
    assert "account_value" not in combined
    assert "owner@example.com" not in combined
    assert {"admin_viewed_dashboard", "admin_viewed_metrics"}.issubset(set(_event_types(client)))


def test_admin_dashboard_is_private_and_omits_client_contact_details_for_read_roles() -> None:
    client = _client()
    contact = _login(client, 1901, "dashboard_contact")
    admin = _login(client, 1902, "dashboard_admin")
    support = _login(client, 1903, "dashboard_support")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")
    profile = client.post(
        "/api/v1/users/me/profile",
        headers={**_bearer(contact, "req_dashboard_contact_profile"), "Content-Type": "application/json"},
        json={"first_name": "Contacto Privado", "phone": "+58 414 555 0199"},
    )
    assert profile.status_code == 200, profile.text

    for reader, request_id in ((admin, "req_private_admin_dashboard"), (support, "req_private_support_dashboard")):
        response = client.get("/api/v1/admin/dashboard", headers=_bearer(reader, request_id))

        assert response.status_code == 200, response.text
        assert response.headers["Cache-Control"] == "private, no-store"
        assert "users" not in response.json()["data"]
        assert "+58 414 555 0199" not in response.text


def test_admin_incident_console_summarizes_operational_signals_without_sensitive_values() -> None:
    client = _client()
    admin = _login(client, 906, "incident_admin")
    support = _login(client, 907, "incident_support")
    business_owner = _login(client, 908, "incident_business_owner")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")
    client.app.state.user_repository.set_user_role(business_owner["user"]["id"], "business_owner")
    client.app.state.job_repository.create_job_run(
        job_type="notification_sender",
        status="failed",
        started_at=utc_now(),
        finished_at=utc_now(),
        failed_count=1,
        error_code="TELEGRAM_SEND_FAILED",
        error_message_safe="Telegram temporalmente no disponible.",
    )
    notification, _ = client.app.state.job_repository.enqueue_notification(
        notification_type="order_created_business",
        recipient_user_id=admin["user"]["id"],
        recipient_role=None,
        order_id=None,
        business_id=None,
        dispute_id=None,
        scheduled_for=utc_now(),
        max_attempts=3,
        dedupe_key="incident_console_notification",
        metadata_json={
            "channel": "telegram",
            "target_surface": "business_mini_app",
            "message_text": "Orden NODO",
            "account_value": "owner@example.com",
            "storage_path": "private/proof.png",
        },
    )
    client.app.state.job_repository.update_notification(
        notification,
        status="failed",
        attempts=1,
        last_error_code="TELEGRAM_SEND_FAILED",
    )
    client.app.state.audit_writer.write(
        event_type="credit_purchase_review_failed",
        actor_user_id=admin["user"]["id"],
        actor_role="admin",
        resource_type="credit_purchase",
        resource_id=None,
        request_id="req_incident_seed",
        metadata_json={"account_value": "owner@example.com", "safe": "ok"},
    )

    incident = client.get("/api/v1/admin/incident-console", headers=_bearer(admin, "req_incident_console"))
    support_incident = client.get("/api/v1/admin/incident-console", headers=_bearer(support, "req_support_incident_console"))
    forbidden = client.get("/api/v1/admin/incident-console", headers=_bearer(business_owner, "req_forbidden_incident_console"))

    assert incident.status_code == 200, incident.text
    assert support_incident.status_code == 200, support_incident.text
    assert forbidden.status_code == 403
    data = incident.json()["data"]
    assert data["status"] in {"critical", "degraded"}
    assert data["jobs"]["recent_failed"][0]["error_code"] == "TELEGRAM_SEND_FAILED"
    assert data["notifications"]["recent_problems"][0]["last_error_code"] == "TELEGRAM_SEND_FAILED"
    assert data["recommended_actions"]
    combined = incident.text + json.dumps(data, default=str)
    assert "owner@example.com" not in combined
    assert "private/proof.png" not in combined
    assert "storage_path" not in combined
    assert "account_value" not in combined
    assert "admin_viewed_incident_console" in _event_types(client)


def test_admin_opens_investigation_from_payment_rejected_without_releasing_obligations() -> None:
    client = _client()
    owner, business, ad, remitter, order = _seed_payment_rejected_order(client, owner_id=900, remitter_id=901)
    admin = _login(client, 902, "admin_open_investigation")
    support = _login(client, 903, "support_open_investigation")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")
    reservation_before = client.app.state.capacity_repository.get_reservation(order["id"])
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])

    for actor, key in (
        (owner, "owner_forbidden_open"),
        (remitter, "remitter_forbidden_open"),
        (support, "support_forbidden_open"),
    ):
        forbidden = client.post(
            f"/api/v1/admin/orders/{order['id']}/open-dispute",
            headers={**_headers(actor, key), "Content-Type": "application/json"},
            json={"reason": "Intento no autorizado"},
        )
        assert forbidden.status_code == 403

    missing_reason = client.post(
        f"/api/v1/admin/orders/{order['id']}/open-dispute",
        headers={**_headers(admin, "admin_open_missing_reason"), "Content-Type": "application/json"},
        json={"reason": "   "},
    )
    missing_key = client.post(
        f"/api/v1/admin/orders/{order['id']}/open-dispute",
        headers={**_bearer(admin, "req_admin_open_missing_key"), "Content-Type": "application/json"},
        json={"reason": "Falta clave de idempotencia"},
    )
    assert missing_reason.status_code == 422
    assert missing_key.status_code == 400
    assert missing_key.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    opened = client.post(
        f"/api/v1/admin/orders/{order['id']}/open-dispute",
        headers={**_headers(admin, "admin_open_rejected"), "Content-Type": "application/json"},
        json={"reason": "El pago reportado requiere investigacion administrativa"},
    )
    replay = client.post(
        f"/api/v1/admin/orders/{order['id']}/open-dispute",
        headers={**_headers(admin, "admin_open_rejected"), "Content-Type": "application/json"},
        json={"reason": "El pago reportado requiere investigacion administrativa"},
    )
    mismatch = client.post(
        f"/api/v1/admin/orders/{order['id']}/open-dispute",
        headers={**_headers(admin, "admin_open_rejected"), "Content-Type": "application/json"},
        json={"reason": "Carga diferente para la misma clave"},
    )

    assert opened.status_code == 201, opened.text
    assert opened.headers["Cache-Control"] == "private, no-store"
    assert replay.status_code == 201, replay.text
    assert replay.json()["data"] == opened.json()["data"]
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"
    data = opened.json()["data"]
    assert data["order"]["status"] == "disputed"
    assert data["dispute"]["status"] == "open"
    assert data["dispute"]["previous_order_status"] == "payment_rejected"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "in_order"
    reservation_after = client.app.state.capacity_repository.get_reservation(order["id"])
    assert reservation_before is not None and reservation_after is not None
    assert reservation_after.status == reservation_before.status == "reserved"
    wallet_after = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after.available_credits == wallet_before.available_credits
    assert wallet_after.blocked_credits == wallet_before.blocked_credits
    assert wallet_after.consumed_credits == wallet_before.consumed_credits
    disputes = [item for item in client.app.state.dispute_repository.disputes.values() if item.order_id == order["id"]]
    assert len(disputes) == 1
    order_events = [
        event
        for event in client.app.state.order_repository.events
        if event.order_id == order["id"] and event.event_type == "dispute_opened"
    ]
    assert len(order_events) == 1
    dispute_events = [
        event
        for event in client.app.state.dispute_repository.events
        if event.order_id == order["id"] and event.event_type == "dispute_opened"
    ]
    assert len(dispute_events) == 1
    audits = [
        event
        for event in client.app.state.audit_writer.events
        if event.event_type == "admin_order_dispute_opened" and event.resource_id == data["dispute"]["id"]
    ]
    assert len(audits) == 1
    notification_jobs = [
        job
        for job in client.app.state.job_repository.notification_jobs.values()
        if job.notification_type == "order_disputed_parties_admin" and job.order_id == order["id"]
    ]
    assert len(notification_jobs) == 4
    assert {job.recipient_user_id for job in notification_jobs if job.recipient_user_id} == {
        owner["user"]["id"],
        remitter["user"]["id"],
    }


def test_admin_open_investigation_rejects_non_rejected_order_and_then_reuses_resolution_flow() -> None:
    client = _client()
    _, business, ad, _, rejected_order = _seed_payment_rejected_order(client, owner_id=904, remitter_id=905)
    active_owner = _login(client, 906, "owner_invalid_admin_open")
    _, active_method_id = _approved_business_with_method(client, active_owner, credits=1)
    active_ad = _create_ad(client, active_owner, active_method_id, key="ad_invalid_admin_open")
    active_remitter = _login(client, 907, "remitter_invalid_admin_open")
    active_order = _create_order(client, active_remitter, active_ad["id"], key="order_invalid_admin_open")
    admin = _login(client, 908, "admin_open_then_resolve")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "super_admin")

    invalid = client.post(
        f"/api/v1/admin/orders/{active_order['id']}/open-dispute",
        headers={**_headers(admin, "admin_open_invalid_state"), "Content-Type": "application/json"},
        json={"reason": "Estado no permitido"},
    )
    opened = client.post(
        f"/api/v1/admin/orders/{rejected_order['id']}/open-dispute",
        headers={**_headers(admin, "admin_open_then_resolve"), "Content-Type": "application/json"},
        json={"reason": "Abrir investigacion y reutilizar resolucion"},
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "ORDER_STATUS_INVALID"
    assert opened.status_code == 201, opened.text

    resolved = client.post(
        f"/api/v1/admin/disputes/{opened.json()['data']['dispute']['id']}/resolve",
        headers={**_headers(admin, "resolve_admin_opened_dispute"), "Content-Type": "application/json"},
        json={"resolution_type": "keep_under_review", "reason": "La investigacion sigue abierta"},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.headers["Cache-Control"] == "private, no-store"
    assert resolved.json()["data"]["dispute"]["status"] == "in_review"
    assert resolved.json()["data"]["order"]["status"] == "disputed"
    assert resolved.json()["data"]["credit_effect"]["type"] == "none"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "in_order"
    assert client.app.state.capacity_repository.get_reservation(rejected_order["id"]).status == "reserved"
    assert client.app.state.ad_repository.get_wallet(business["id"]).blocked_credits == 1


@pytest.mark.parametrize(
    (
        "resolution_type",
        "expected_order_status",
        "expected_credit_effect",
        "expected_reservation_status",
    ),
    [
        ("cancelled", "cancelled", "release", "released"),
        ("remitter_favored", "cancelled", "consume", "released"),
        ("business_favored", "completed", "consume", "consumed"),
    ],
)
def test_admin_panel_resolution_sequence_applies_payment_rejected_contract_once(
    resolution_type: str,
    expected_order_status: str,
    expected_credit_effect: str,
    expected_reservation_status: str,
) -> None:
    client = _client()
    owner_id = 1000 + len(resolution_type)
    remitter_id = 1100 + len(resolution_type)
    _, business, ad, _, order = _seed_payment_rejected_order(
        client,
        owner_id=owner_id,
        remitter_id=remitter_id,
    )
    admin = _login(client, 1200 + len(resolution_type), f"admin_panel_{resolution_type}")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])
    available_before = wallet_before.available_credits
    blocked_before = wallet_before.blocked_credits
    consumed_before = wallet_before.consumed_credits

    opened = client.post(
        f"/api/v1/admin/orders/{order['id']}/open-dispute",
        headers={**_headers(admin, f"panel_open_{resolution_type}"), "Content-Type": "application/json"},
        json={"reason": "Revision operativa desde el detalle Admin"},
    )
    assert opened.status_code == 201, opened.text
    dispute_id = opened.json()["data"]["dispute"]["id"]
    resolution_headers = {
        **_headers(admin, f"panel_resolve_{resolution_type}"),
        "Content-Type": "application/json",
    }
    resolution_payload = {
        "resolution_type": resolution_type,
        "reason": "Decision documentada desde el detalle Admin",
    }
    resolved = client.post(
        f"/api/v1/admin/disputes/{dispute_id}/resolve",
        headers=resolution_headers,
        json=resolution_payload,
    )
    pause_after_resolution = client.app.state.business_repository.get_business(
        business["id"]
    ).ad_publication_paused_until
    replay = client.post(
        f"/api/v1/admin/disputes/{dispute_id}/resolve",
        headers=resolution_headers,
        json=resolution_payload,
    )
    pause_after_replay = client.app.state.business_repository.get_business(
        business["id"]
    ).ad_publication_paused_until

    assert resolved.status_code == 200, resolved.text
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"] == resolved.json()["data"]
    assert pause_after_resolution is not None
    assert pause_after_replay == pause_after_resolution
    assert resolved.json()["data"]["order"]["status"] == expected_order_status
    assert resolved.json()["data"]["credit_effect"]["type"] == expected_credit_effect
    assert client.app.state.capacity_repository.get_reservation(order["id"]).status == expected_reservation_status
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "archived"
    wallet_after = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after.blocked_credits == blocked_before - 1
    if expected_credit_effect == "release":
        assert wallet_after.available_credits == available_before + 1
        assert wallet_after.consumed_credits == consumed_before
    else:
        assert wallet_after.available_credits == available_before
        assert wallet_after.consumed_credits == consumed_before + 1
    resolution_notifications = [
        job
        for job in client.app.state.job_repository.notification_jobs.values()
        if job.order_id == order["id"]
        and (job.metadata_json or {}).get("dispute_update") == "resolution"
    ]
    assert len(resolution_notifications) == 2
    assert len([event for event in client.app.state.audit_writer.events if event.resource_id == dispute_id and event.event_type == "dispute_resolved"]) == 1


def test_client_order_history_projects_admin_rejected_payment_without_private_reason() -> None:
    client = _client()
    _, _, _, remitter, rejected_order = _seed_payment_rejected_order(
        client,
        owner_id=1300,
        remitter_id=1301,
    )
    admin = _login(client, 1302, "admin_client_rejected_projection")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    private_reason = "Referencia interna que no debe llegar al cliente"

    opened = client.post(
        f"/api/v1/admin/orders/{rejected_order['id']}/open-dispute",
        headers={**_headers(admin, "client_projection_open"), "Content-Type": "application/json"},
        json={"reason": private_reason},
    )
    assert opened.status_code == 201, opened.text
    resolved = client.post(
        f"/api/v1/admin/disputes/{opened.json()['data']['dispute']['id']}/resolve",
        headers={**_headers(admin, "client_projection_resolve"), "Content-Type": "application/json"},
        json={"resolution_type": "cancelled", "reason": private_reason},
    )
    assert resolved.status_code == 200, resolved.text

    detail = client.get(
        f"/api/v1/orders/{rejected_order['id']}",
        headers=_bearer(remitter, "req_client_projection_detail"),
    )
    history = client.get(
        "/api/v1/orders/mine?status=cancelled",
        headers=_bearer(remitter, "req_client_projection_history"),
    )

    assert detail.status_code == 200, detail.text
    assert history.status_code == 200, history.text
    assert detail.json()["data"]["order"]["terminal_display_status"] == "payment_rejected_admin_review"
    history_order = next(item for item in history.json()["data"]["items"] if item["id"] == rejected_order["id"])
    assert history_order["terminal_display_status"] == "payment_rejected_admin_review"
    client_payload = detail.text + history.text
    assert private_reason not in client_payload
    assert "resolution_reason" not in client_payload
    assert "previous_order_status" not in client_payload
    assert "storage_path" not in client_payload
    assert "account_value" not in client_payload


def test_client_order_history_does_not_label_other_admin_cancellations_as_rejected_payment() -> None:
    client = _client()
    _, _, _, remitter, order, dispute = _seed_disputed_order(
        client,
        owner_id=1303,
        remitter_id=1304,
    )
    admin = _login(client, 1305, "admin_non_rejected_projection")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")

    resolved = client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/resolve",
        headers={**_headers(admin, "non_rejected_projection_resolve"), "Content-Type": "application/json"},
        json={"resolution_type": "cancelled", "reason": "Cierre administrativo de otra disputa"},
    )
    detail = client.get(
        f"/api/v1/orders/{order['id']}",
        headers=_bearer(remitter, "req_non_rejected_projection_detail"),
    )

    assert resolved.status_code == 200, resolved.text
    resolved_order = client.app.state.order_repository.get_by_id(order["id"])
    assert resolved_order is not None
    assert resolved_order.cancel_reason == "admin_cancelled"
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["order"]["terminal_display_status"] is None


def test_admin_resolve_requires_admin_reason_idempotency_and_consumes_once() -> None:
    client = _client()
    _, business, ad, remitter, order, dispute = _seed_disputed_order(client, owner_id=910, remitter_id=911)
    admin = _login(client, 912, "admin")
    support = _login(client, 913, "support")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])
    blocked_before = wallet_before.blocked_credits
    consumed_before = wallet_before.consumed_credits

    support_resolve = client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/resolve",
        headers={**_headers(support, "support_resolve"), "Content-Type": "application/json"},
        json={"resolution_type": "business_favored", "reason": "Revision"},
    )
    missing_key = client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/resolve",
        headers={**_bearer(admin, "req_no_key"), "Content-Type": "application/json"},
        json={"resolution_type": "business_favored", "reason": "Revision"},
    )
    missing_reason = client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/resolve",
        headers={**_headers(admin, "missing_reason"), "Content-Type": "application/json"},
        json={"resolution_type": "business_favored", "reason": ""},
    )
    resolved = client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/resolve",
        headers={**_headers(admin, "resolve_business"), "Content-Type": "application/json"},
        json={"resolution_type": "business_favored", "reason": "Evidencia favorece al negocio"},
    )
    replay = client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/resolve",
        headers={**_headers(admin, "resolve_business"), "Content-Type": "application/json"},
        json={"resolution_type": "business_favored", "reason": "Evidencia favorece al negocio"},
    )
    mismatch = client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/resolve",
        headers={**_headers(admin, "resolve_business"), "Content-Type": "application/json"},
        json={"resolution_type": "completed", "reason": "Payload distinto"},
    )
    new_attempt = client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/resolve",
        headers={**_headers(admin, "resolve_again"), "Content-Type": "application/json"},
        json={"resolution_type": "completed", "reason": "Segundo intento"},
    )

    assert support_resolve.status_code == 403
    assert missing_key.status_code == 400
    assert missing_key.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert missing_reason.status_code in {400, 422}
    assert resolved.status_code == 200, resolved.text
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"]["order"]["id"] == order["id"]
    assert mismatch.status_code == 409
    assert new_attempt.status_code == 409
    assert new_attempt.json()["error"]["code"] == "DISPUTE_STATUS_INVALID"
    stored_order = client.app.state.order_repository.get_by_id(order["id"])
    assert stored_order.status == "completed"
    assert stored_order.completion_reason == "admin_resolved"
    assert client.app.state.dispute_repository.get_dispute(dispute["id"]).status == "resolved"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "archived"
    wallet_after = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after.blocked_credits == blocked_before - 1
    assert wallet_after.consumed_credits == consumed_before + 1
    consumes = [item for item in client.app.state.ad_repository.ledger.values() if item.type == "consume" and item.related_order_id == order["id"]]
    assert len(consumes) == 1
    assert resolved.json()["data"]["credit_effect"]["type"] == "consume"
    assert "dispute_resolved" in _event_types(client)
    resolution_notifications = [
        job
        for job in client.app.state.job_repository.notification_jobs.values()
        if job.order_id == order["id"]
        and (job.metadata_json or {}).get("dispute_update") == "resolution"
    ]
    assert len(resolution_notifications) == 2
    assert {job.recipient_user_id for job in resolution_notifications} == {
        client.app.state.business_repository.get_business(business["id"]).owner_user_id,
        remitter["user"]["id"],
    }
    assert resolved.json()["data"]["disclaimer"].startswith("La disputa queda registrada")
    combined = resolved.text + json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert "storage_path" not in combined
    assert "account_value" not in combined
    assert "owner@example.com" not in combined
    assert BOT_TOKEN not in combined
    assert JWT_SECRET not in combined
    assert JWT_REFRESH_SECRET not in combined


def test_admin_resolve_cancelled_releases_and_keep_under_review_has_no_credit_effect() -> None:
    client = _client()
    _, business_cancel, ad_cancel, _, order_cancel, dispute_cancel = _seed_disputed_order(client, owner_id=920, remitter_id=921)
    _, business_review, ad_review, _, order_review, dispute_review = _seed_disputed_order(client, owner_id=922, remitter_id=923)
    admin = _login(client, 924, "admin")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    cancel_wallet_before = client.app.state.ad_repository.get_wallet(business_cancel["id"])
    cancel_available_before = cancel_wallet_before.available_credits
    cancel_blocked_before = cancel_wallet_before.blocked_credits
    review_wallet_before = client.app.state.ad_repository.get_wallet(business_review["id"])
    review_blocked_before = review_wallet_before.blocked_credits

    cancelled = client.post(
        f"/api/v1/admin/disputes/{dispute_cancel['id']}/resolve",
        headers={**_headers(admin, "resolve_cancelled"), "Content-Type": "application/json"},
        json={"resolution_type": "cancelled", "reason": "Cancelacion admin por evidencia insuficiente"},
    )
    in_review = client.post(
        f"/api/v1/admin/disputes/{dispute_review['id']}/resolve",
        headers={**_headers(admin, "resolve_review"), "Content-Type": "application/json"},
        json={"resolution_type": "keep_under_review", "reason": "Falta revisar evidencia"},
    )

    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["data"]["order"]["status"] == "cancelled"
    assert cancelled.json()["data"]["credit_effect"]["type"] == "release"
    assert client.app.state.order_repository.get_by_id(order_cancel["id"]).cancel_reason == "admin_cancelled"
    assert client.app.state.ad_repository.get_ad(ad_cancel["id"]).status == "archived"
    cancel_wallet_after = client.app.state.ad_repository.get_wallet(business_cancel["id"])
    assert cancel_wallet_after.available_credits == cancel_available_before + 1
    assert cancel_wallet_after.blocked_credits == cancel_blocked_before - 1

    assert in_review.status_code == 200, in_review.text
    assert in_review.json()["data"]["dispute"]["status"] == "in_review"
    assert in_review.json()["data"]["order"]["status"] == "disputed"
    assert in_review.json()["data"]["credit_effect"]["type"] == "none"
    assert client.app.state.ad_repository.get_ad(ad_review["id"]).status == "in_order"
    review_wallet_after = client.app.state.ad_repository.get_wallet(business_review["id"])
    assert review_wallet_after.blocked_credits == review_blocked_before
    assert "dispute_marked_in_review" in _event_types(client)


@pytest.mark.parametrize(
    ("resolution_type", "expected_status", "expected_reason_field"),
    [
        ("remitter_favored", "cancelled", "admin_cancelled"),
        ("completed", "completed", "admin_resolved"),
    ],
)
def test_admin_resolve_remaining_terminal_types_follow_contract(resolution_type: str, expected_status: str, expected_reason_field: str) -> None:
    client = _client()
    _, business, ad, _, order, dispute = _seed_disputed_order(client, owner_id=940 + len(resolution_type), remitter_id=950 + len(resolution_type))
    admin = _login(client, 960 + len(resolution_type), f"admin_{resolution_type}")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])
    blocked_before = wallet_before.blocked_credits
    consumed_before = wallet_before.consumed_credits

    resolved = client.post(
        f"/api/v1/admin/disputes/{dispute['id']}/resolve",
        headers={**_headers(admin, f"resolve_{resolution_type}"), "Content-Type": "application/json"},
        json={"resolution_type": resolution_type, "reason": "Resolucion admin contratada"},
    )

    assert resolved.status_code == 200, resolved.text
    stored = client.app.state.order_repository.get_by_id(order["id"])
    assert stored.status == expected_status
    assert (stored.cancel_reason if expected_status == "cancelled" else stored.completion_reason) == expected_reason_field
    assert client.app.state.dispute_repository.get_dispute(dispute["id"]).status == "resolved"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "archived"
    wallet_after = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after.blocked_credits == blocked_before - 1
    assert wallet_after.consumed_credits == consumed_before + 1
    assert resolved.json()["data"]["credit_effect"]["type"] == "consume"
    assert "dispute_resolved" in _event_types(client)


def test_admin_business_order_audit_lists_are_masked_and_credit_screens_stay_slice_08() -> None:
    client = _client()
    _, _, _, _, order, _ = _seed_disputed_order(client, owner_id=930, remitter_id=931)
    admin = _login(client, 932, "admin")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")

    businesses = client.get("/api/v1/admin/businesses?limit=20", headers=_bearer(admin, "req_admin_businesses"))
    orders = client.get("/api/v1/admin/orders?limit=20", headers=_bearer(admin, "req_admin_orders"))
    detail = client.get(f"/api/v1/admin/orders/{order['id']}", headers=_bearer(admin, "req_admin_order_detail"))
    audit = client.get("/api/v1/admin/audit-logs?limit=20", headers=_bearer(admin, "req_admin_audit"))
    frontend_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("apps/web/src").rglob("*")
        if path.suffix in {".ts", ".tsx"}
    )

    assert businesses.status_code == 200, businesses.text
    assert orders.status_code == 200, orders.text
    assert detail.status_code == 200, detail.text
    assert audit.status_code == 200, audit.text
    assert all(item.get("id") for item in audit.json()["data"]["items"])
    combined = businesses.text + orders.text + detail.text + audit.text
    assert "storage_path" not in combined
    assert "account_value" not in combined
    assert "owner@example.com" not in combined
    assert "payment_instructions_snapshot" not in combined
    assert "admin_viewed_audit_logs" in _event_types(client)
    assert "credit-purchases" in frontend_source
    assert "credit-detail" in frontend_source
    assert "credit-adjustments" in frontend_source
    assert "system_metrics" not in frontend_source


def test_slice_09_migration_allows_admin_resolution_values() -> None:
    migration = open("database/migrations/0010_slice_09_admin_console.up.sql", encoding="utf-8").read()
    rollback = open("database/migrations/0010_slice_09_admin_console.down.sql", encoding="utf-8").read()

    for expected in [
        "disputes_resolution_type_check",
        "'remitter_favored'",
        "'business_favored'",
        "'cancelled'",
        "'completed'",
        "'keep_under_review'",
        "disputes_admin_resolution_required_check",
        "'dispute_marked_in_review'",
    ]:
        assert expected in migration
    assert "future_admin_resolution" not in migration
    assert "disputes_resolution_type_future_check" in rollback


def test_platform_emergency_mode_blocks_new_operations_but_keeps_existing_order_resolution_open() -> None:
    client = _client()
    owner = _login(client, 980, "emergency_owner")
    business, method_id = _approved_business_with_method(client, owner, credits=5)
    client.app.state.capacity_repository.set_declared_capacity(
        business_id=business["id"],
        amount_usd=Decimal("600.00"),
        actor_user_id=owner["user"]["id"],
    )
    usdt_method = client.app.state.business_repository.add_payment_method(
        business_id=business["id"],
        method_type="usdt_trc20",
        network="TRC20",
        account_value="TEmergencyWalletAddress",
        account_masked="TEme...ress",
        holder_name="Owner Test",
    )
    usdt_method.verified_status = "approved"
    usdt_method.active = True
    active_ad = _create_ad(client, owner, method_id, key="emergency_active_ad")
    second_ad_response = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "emergency_second_ad"), "Content-Type": "application/json"},
        json={
            "payment_method_id": usdt_method.id,
            "payment_method": "usdt_trc20",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "101.00",
            "amount_max_usd": "500.00",
        },
    )
    assert second_ad_response.status_code == 201, second_ad_response.text
    second_ad = second_ad_response.json()["data"]["ad"]
    remitter = _login(client, 981, "emergency_remitter")
    existing_order = _create_order(client, remitter, active_ad["id"], key="emergency_existing_order")
    admin = _login(client, 982, "emergency_admin")
    support = _login(client, 983, "emergency_support")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")

    readable = client.get("/api/v1/admin/emergency-mode", headers=_bearer(support, "req_emergency_read"))
    forbidden = client.post(
        "/api/v1/admin/emergency-mode/activate",
        headers={**_headers(support, "support_emergency"), "Content-Type": "application/json"},
        json={"reason": "Support no puede activar"},
    )
    missing_key = client.post(
        "/api/v1/admin/emergency-mode/activate",
        headers={**_bearer(admin, "req_emergency_no_key"), "Content-Type": "application/json"},
        json={"reason": "Incidente transporte"},
    )
    missing_reason = client.post(
        "/api/v1/admin/emergency-mode/activate",
        headers={**_headers(admin, "emergency_missing_reason"), "Content-Type": "application/json"},
        json={"reason": ""},
    )
    activated = client.post(
        "/api/v1/admin/emergency-mode/activate",
        headers={**_headers(admin, "emergency_activate"), "Content-Type": "application/json"},
        json={"reason": "Incidente de pagos", "message": "Estamos revisando NODO."},
    )
    replay = client.post(
        "/api/v1/admin/emergency-mode/activate",
        headers={**_headers(admin, "emergency_activate"), "Content-Type": "application/json"},
        json={"reason": "Incidente de pagos", "message": "Estamos revisando NODO."},
    )

    assert readable.status_code == 200, readable.text
    assert readable.json()["data"]["emergency_mode"]["enabled"] is False
    assert forbidden.status_code == 403
    assert missing_key.status_code == 400
    assert missing_key.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert missing_reason.status_code == 400
    assert missing_reason.json()["error"]["code"] == "ADMIN_REASON_REQUIRED"
    assert activated.status_code == 200, activated.text
    assert activated.json()["data"]["emergency_mode"]["enabled"] is True
    assert activated.json()["data"]["emergency_mode"]["message"] == "Estamos revisando NODO."
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"]["emergency_mode"]["enabled"] is True

    blocked_order = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "emergency_new_order"), "Content-Type": "application/json"},
        json={
            "ad_id": second_ad["id"],
            "amount_usd": "150.00",
            "receiver_data": {"bank": "Banco", "phone": "+584121234567", "document": "V12345678", "holder": "Receptor Test"},
        },
    )
    blocked_ad = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "emergency_new_ad"), "Content-Type": "application/json"},
        json={
            "payment_method_id": method_id,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "501.00",
            "amount_max_usd": "600.00",
        },
    )
    blocked_credit_purchase = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "emergency_credit_purchase"), "Content-Type": "application/json"},
        json={"package_code": "starter", "token_symbol": "USDC"},
    )
    blocked_reactivate = client.post(
        f"/api/v1/business/ads/{second_ad['id']}/reactivate",
        headers={**_headers(owner, "emergency_reactivate"), "Content-Type": "application/json"},
        json={"reason": "Intento en emergencia"},
    )

    assert blocked_order.status_code == 503
    assert blocked_order.json()["error"]["code"] == "PLATFORM_EMERGENCY_MODE_ACTIVE"
    assert blocked_ad.status_code == 503
    assert blocked_credit_purchase.status_code == 503
    assert blocked_reactivate.status_code == 503

    report = _report_payment(client, remitter, existing_order, key="emergency_report_existing")
    confirm = client.post(
        f"/api/v1/business/orders/{existing_order['id']}/confirm-payment",
        headers={**_headers(owner, "emergency_confirm_existing"), "Content-Type": "application/json"},
        json={"reason": "Pago revisado durante emergencia"},
    )

    assert report["payment_report"]["status"] == "submitted"
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["data"]["order"]["status"] == "payment_confirmed"

    deactivated = client.post(
        "/api/v1/admin/emergency-mode/deactivate",
        headers={**_headers(admin, "emergency_deactivate"), "Content-Type": "application/json"},
        json={"reason": "Incidente resuelto"},
    )
    dashboard = client.get("/api/v1/admin/dashboard", headers=_bearer(admin, "req_dashboard_after_emergency"))

    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["data"]["emergency_mode"]["enabled"] is False
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["data"]["emergency_mode"]["enabled"] is False
    events = _event_types(client)
    assert events.count("platform_emergency_mode_activated") == 1
    assert "platform_emergency_mode_deactivated" in events
    assert client.app.state.business_repository.get_business(business["id"]).verification_status == "approved"


def test_platform_emergency_mode_migration_contract_is_dedicated_and_reversible() -> None:
    migration = open("database/migrations/0025_platform_emergency_mode.up.sql", encoding="utf-8").read()
    rollback = open("database/migrations/0025_platform_emergency_mode.down.sql", encoding="utf-8").read()

    assert "create table if not exists platform_emergency_mode" in migration
    assert "enabled boolean not null default false" in migration
    assert "activated_by_user_id uuid references users(id)" in migration
    assert "insert into platform_emergency_mode" in migration
    assert "app_metadata" not in migration
    assert "drop table if exists platform_emergency_mode" in rollback


def test_admin_order_and_dispute_lists_reject_invalid_cursor_with_400() -> None:
    client = _client()
    admin = _login(client, 8900, "admin_cursor_invalid")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "super_admin")

    orders = client.get(
        "/api/v1/admin/orders?cursor=not-a-cursor",
        headers=_bearer(admin, "admin_order_cursor_invalid"),
    )
    disputes = client.get(
        "/api/v1/admin/disputes?cursor=not-a-cursor",
        headers=_bearer(admin, "admin_dispute_cursor_invalid"),
    )

    assert orders.status_code == 400
    assert orders.json()["error"]["code"] == "PAGINATION_CURSOR_INVALID"
    assert disputes.status_code == 400
    assert disputes.json()["error"]["code"] == "PAGINATION_CURSOR_INVALID"


def test_admin_orders_can_filter_by_public_order_code() -> None:
    client = _client()
    owner = _login(client, 8910, "admin_order_code_owner")
    business, method_id = _approved_business_with_method(client, owner, credits=4)
    client.app.state.capacity_repository.set_declared_capacity(
        business_id=business["id"],
        amount_usd=Decimal("800.00"),
        actor_user_id=owner["user"]["id"],
    )
    other_owner = _login(client, 8914, "admin_order_code_other_owner")
    other_business, other_method_id = _approved_business_with_method(client, other_owner, credits=4)
    client.app.state.capacity_repository.set_declared_capacity(
        business_id=other_business["id"],
        amount_usd=Decimal("800.00"),
        actor_user_id=other_owner["user"]["id"],
    )
    first_remitter = _login(client, 8911, "admin_order_code_first")
    second_remitter = _login(client, 8912, "admin_order_code_second")
    first_ad = _create_ad(client, owner, method_id, key="admin_code_first_ad")
    first_order = _create_order(client, first_remitter, first_ad["id"], key="admin_code_first_order")
    second_ad = _create_ad(client, other_owner, other_method_id, key="admin_code_second_ad")
    second_order = _create_order(client, second_remitter, second_ad["id"], key="admin_code_second_order")
    admin = _login(client, 8913, "admin_order_code_admin")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")

    exact = client.get(
        f"/api/v1/admin/orders?public_order_code={second_order['public_order_code']}",
        headers=_bearer(admin, "admin_order_code_exact"),
    )
    suffix = client.get(
        f"/api/v1/admin/orders?public_order_code={second_order['public_order_code'].replace('NODO-', '').lower()}",
        headers=_bearer(admin, "admin_order_code_suffix"),
    )
    mismatched_status = client.get(
        f"/api/v1/admin/orders?public_order_code={second_order['public_order_code']}&status=completed",
        headers=_bearer(admin, "admin_order_code_status"),
    )

    assert exact.status_code == 200, exact.text
    assert suffix.status_code == 200, suffix.text
    assert mismatched_status.status_code == 200, mismatched_status.text
    exact_items = exact.json()["data"]["items"]
    suffix_items = suffix.json()["data"]["items"]
    assert [item["id"] for item in exact_items] == [second_order["id"]]
    assert [item["id"] for item in suffix_items] == [second_order["id"]]
    assert first_order["id"] not in {item["id"] for item in exact_items}
    assert mismatched_status.json()["data"]["items"] == []
