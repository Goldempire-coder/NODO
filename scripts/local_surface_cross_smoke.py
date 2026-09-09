from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode

from fastapi.testclient import TestClient


BOT_TOKEN = "123456:test-bot-token"
BUSINESS_INTAKE_BOT_TOKEN = "123456:business-intake-test-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"


def _set_env() -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "local-surface-cross-smoke",
        "NODO_BUILD_ID": "local-surface-cross-smoke",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
        "BOT_TOKEN": BOT_TOKEN,
        "BUSINESS_INTAKE_BOT_TOKEN": BUSINESS_INTAKE_BOT_TOKEN,
        "JWT_SECRET": JWT_SECRET,
        "JWT_REFRESH_SECRET": JWT_REFRESH_SECRET,
        "AUTH_INIT_DATA_MAX_AGE_SECONDS": "86400",
        "ACCESS_TOKEN_TTL_SECONDS": "900",
        "REFRESH_TOKEN_TTL_SECONDS": "2592000",
        "AUTH_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "AUTH_RATE_LIMIT_WINDOW_SECONDS": "60",
        "BUSINESS_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "BUSINESS_RATE_LIMIT_WINDOW_SECONDS": "60",
        "NODO_CREDIT_RECEIVING_WALLET_BASE": "0x1111111111111111111111111111111111111111",
    }
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app  # noqa: E402
from app.routes.telegram_bot import telegram_webhook_secret  # noqa: E402


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
        headers={"X-Request-Id": f"req_cross_login_{telegram_id}"},
        json={"init_data": _signed_init_data(telegram_id, username)},
    )
    _assert_status(response, 200, "auth.login")
    return response.json()["data"]


def _headers(login: dict, key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {login['access_token']}",
        "X-Request-Id": f"req_cross_{key}",
        "Idempotency-Key": f"idem_cross_{key}",
    }


def _bearer(login: dict, key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": f"req_cross_{key}"}


def _assert_status(response, expected: int, label: str) -> None:  # type: ignore[no-untyped-def]
    if response.status_code != expected:
        raise RuntimeError(f"{label} expected {expected}, got {response.status_code}: {response.text}")


def _json_data(response) -> dict:  # type: ignore[no-untyped-def]
    return response.json()["data"]


def _create_approved_business(client: TestClient, owner: dict, admin: dict) -> tuple[dict, str]:
    response = client.post(
        "/api/v1/businesses",
        headers={**_headers(owner, "create_business"), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": "Casa Smoke", "rif": "J-12345678-9", "address": "Av Principal", "phone": "+584121234567", "country": "VE"},
    )
    _assert_status(response, 201, "business.create")
    business = _json_data(response)["business"]
    stored_business = client.app.state.business_repository.get_business(business["id"])
    stored_business.verification_status = "approved"
    stored_business.approved_at = stored_business.updated_at
    stored_business.max_order_amount_usd = stored_business.max_order_amount_usd * 20
    stored_user = client.app.state.user_repository.get_user_by_id(owner["user"]["id"])
    client.app.state.business_repository.create_access_link(
        business_id=business["id"],
        user_id=owner["user"]["id"],
        telegram_id_snapshot=stored_user.telegram_id,
        role_in_business="owner",
        linked_by_admin_id=admin["user"]["id"],
        reason="local cross-surface smoke",
    )
    payment = client.app.state.business_repository.add_payment_method(
        business_id=business["id"],
        method_type="zelle",
        network=None,
        account_value="owner@example.com",
        account_masked="***.com",
        holder_name="Owner Smoke",
    )
    payment.verified_status = "approved"
    payment.active = True
    client.app.state.ad_repository.grant_test_credits(business_id=business["id"], amount=3, created_by=admin["user"]["id"])
    return business, payment.id


def _setup_business_pin(client: TestClient, owner: dict) -> dict:
    response = client.post(
        "/api/v1/business/security/pin/setup",
        headers={**_bearer(owner, "business_pin_setup"), "Content-Type": "application/json"},
        json={"pin": "1234"},
    )
    _assert_status(response, 200, "business.pin_setup")
    return _json_data(response)["pin"]


def _make_staff_user(client: TestClient, super_admin: dict) -> tuple[dict, str]:
    support = _login(client, 880004, "surface_support")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")
    expires_at = "2099-01-01T00:00:00+00:00"
    invite = client.post(
        "/api/v1/admin/staff/invites",
        headers={**_headers(super_admin, "staff_invite"), "Content-Type": "application/json"},
        json={
            "target_user_id": support["user"]["id"],
            "staff_role": "support_lead",
            "expires_at": expires_at,
            "reason": "local cross-surface smoke",
            "permissions": [
                {"permission": "view_support_queue", "scope": "queue_scope"},
                {"permission": "view_assigned_support_tickets", "scope": "assigned_only"},
                {"permission": "reply_support_ticket", "scope": "queue_scope"},
                {"permission": "assign_support_ticket", "scope": "queue_scope"},
                {"permission": "escalate_support_ticket", "scope": "queue_scope"},
                {"permission": "resolve_support_ticket", "scope": "queue_scope"},
                {"permission": "close_support_ticket", "scope": "queue_scope"},
                {"permission": "view_support_attachment", "scope": "queue_scope"},
            ],
        },
    )
    _assert_status(invite, 201, "admin.staff_invite")
    profile_id = _json_data(invite)["invite"]["staff_profile_id"]
    staff_list = client.get("/api/v1/admin/staff?limit=20", headers=_bearer(super_admin, "staff_list"))
    _assert_status(staff_list, 200, "admin.staff_list")
    staff_detail = client.get(f"/api/v1/admin/staff/{profile_id}", headers=_bearer(super_admin, "staff_detail"))
    _assert_status(staff_detail, 200, "admin.staff_detail")
    return support, profile_id


def _run_client_onboarding(client: TestClient, remitter: dict) -> dict:
    terms = client.post(
        "/api/v1/users/me/terms-acceptance",
        headers={**_bearer(remitter, "client_terms"), "Content-Type": "application/json"},
        json={"terms_version": "2026-09-09"},
    )
    _assert_status(terms, 200, "client.terms")
    profile = client.post(
        "/api/v1/users/me/profile",
        headers={**_bearer(remitter, "client_profile"), "Content-Type": "application/json"},
        json={"first_name": "Cliente Smoke", "phone": "+584121234567"},
    )
    _assert_status(profile, 200, "client.profile")
    me = client.get("/api/v1/users/me", headers=_bearer(remitter, "client_me"))
    _assert_status(me, 200, "client.me")
    return _json_data(me)


def _run_business_intake_flow(client: TestClient, admin: dict) -> dict:
    bot_headers = {
        "X-NODO-Bot-Webhook-Secret": telegram_webhook_secret(BUSINESS_INTAKE_BOT_TOKEN),
        "X-Request-Id": "req_cross_intake_bot",
    }
    start = client.post(
        "/api/v1/business-intake/start",
        headers={**bot_headers, "Content-Type": "application/json"},
        json={"telegram_user_id": 990001, "telegram_chat_id": 990101, "telegram_update_id": 1, "referral_code": "REF-SMOKE"},
    )
    _assert_status(start, 201, "intake.start")
    intake_id = _json_data(start)["id"]
    contact = client.post(
        f"/api/v1/business-intake/{intake_id}/contact",
        headers={**bot_headers, "Content-Type": "application/json"},
        json={
            "telegram_update_id": 2,
            "telegram_user_id": 990001,
            "telegram_chat_id": 990101,
            "contact_user_id": 990001,
            "contact_phone": "+584121234567",
        },
    )
    _assert_status(contact, 200, "intake.contact")
    document = client.post(
        f"/api/v1/business-intake/{intake_id}/documents",
        headers=bot_headers,
        data={"document_kind": "rif_document", "telegram_update_id": "3"},
        files={"file": ("rif.pdf", b"%PDF-1.4 smoke", "application/pdf")},
    )
    _assert_status(document, 201, "intake.document")
    submit = client.post(
        f"/api/v1/business-intake/{intake_id}/submit",
        headers={**bot_headers, "Content-Type": "application/json"},
        json={
            "telegram_update_id": 4,
            "telegram_user_id": 990001,
            "telegram_chat_id": 990101,
            "business_name": "Casa Intake Smoke",
            "responsible_name": "Responsable Smoke",
            "city": "Caracas",
            "business_phone": "+584121234567",
            "operation": "both",
            "banks": ["Mercantil"],
            "methods": ["zelle", "usdt_trc20"],
            "min_amount_usd": "20.00",
            "max_amount_usd": "500.00",
            "schedule": "Lunes a viernes 9am-6pm",
            "references": ["Referencia Smoke"],
        },
    )
    _assert_status(submit, 200, "intake.submit")
    listing = client.get("/api/v1/admin/business-intake?status=submitted&limit=20", headers=_bearer(admin, "admin_intake_list"))
    _assert_status(listing, 200, "admin.intake_list")
    detail = client.get(f"/api/v1/admin/business-intake/{intake_id}", headers=_bearer(admin, "admin_intake_detail"))
    _assert_status(detail, 200, "admin.intake_detail")
    return {
        "intake_id": intake_id,
        "status": _json_data(submit)["status"],
        "admin_items": len(_json_data(listing)["items"]),
        "document_id": _json_data(document)["file"]["id"],
        "detail_status": _json_data(detail)["intake"]["status"],
    }


def _run_base_usdc_credit_flow(client: TestClient, owner: dict) -> dict:
    create = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "base_usdc_create"), "Content-Type": "application/json"},
        json={"package_code": "starter", "token_symbol": "USDC"},
    )
    _assert_status(create, 201, "business.base_usdc_create")
    purchase = _json_data(create)["purchase"]
    detail = client.get(f"/api/v1/business/credits/purchases/{purchase['id']}", headers=_bearer(owner, "base_usdc_detail"))
    _assert_status(detail, 200, "business.base_usdc_detail")
    admin_list = client.get("/api/v1/admin/credit-purchases?status=pending_payment&limit=20", headers=_bearer(owner, "base_usdc_admin_denied"))
    return {
        "purchase_id": purchase["id"],
        "status": purchase["status"],
        "payment_method": purchase["payment_method"],
        "network": _json_data(create)["payment"]["network"],
        "token_symbol": _json_data(create)["payment"]["token_symbol"],
        "destination_wallet_present": bool(_json_data(create)["payment"]["destination_wallet_address"]),
        "business_detail_status": _json_data(detail)["purchase"]["status"],
        "business_cannot_use_admin_credit_list": admin_list.status_code == 403,
    }


def _run_support_flow(client: TestClient, *, remitter: dict, owner: dict, support: dict, admin: dict, order: dict, business: dict, ad: dict) -> dict:
    client_ticket = client.post(
        "/api/v1/support/tickets",
        headers={**_headers(remitter, "client_support_ticket"), "Content-Type": "application/json", "X-NODO-Surface": "client_mini_app"},
        json={"scope": "client_order", "category": "order_help", "subject": "Ayuda con mi orden", "message": "Necesito soporte con esta orden.", "order_id": order["id"]},
    )
    _assert_status(client_ticket, 201, "client.support_ticket")
    ticket_id = _json_data(client_ticket)["id"]
    business_ticket = client.post(
        "/api/v1/support/tickets",
        headers={**_headers(owner, "business_support_ticket"), "Content-Type": "application/json", "X-NODO-Surface": "business_mini_app"},
        json={"scope": "business_ad", "category": "technical_issue", "subject": "Ayuda con anuncio", "message": "Necesito revisar este anuncio.", "ad_id": ad["id"]},
    )
    _assert_status(business_ticket, 201, "business.support_ticket")

    listed = client.get("/api/v1/admin/support/tickets?limit=20", headers=_bearer(support, "support_admin_list"))
    _assert_status(listed, 200, "support.admin_list")
    assigned = client.post(
        f"/api/v1/admin/support/tickets/{ticket_id}/assign",
        headers={**_headers(admin, "support_assign"), "Content-Type": "application/json"},
        json={"assigned_support_user_id": support["user"]["id"], "reason": "local cross-surface smoke"},
    )
    _assert_status(assigned, 200, "support.assign")
    support_reply = client.post(
        f"/api/v1/admin/support/tickets/{ticket_id}/messages",
        headers={**_headers(support, "support_reply"), "Content-Type": "application/json"},
        json={"body": "Soporte revisando tu caso.", "visibility": "participants"},
    )
    _assert_status(support_reply, 201, "support.reply")
    client_reply = client.post(
        f"/api/v1/support/tickets/{ticket_id}/messages",
        headers={**_headers(remitter, "client_support_reply"), "Content-Type": "application/json"},
        json={"body": "Gracias, quedo atento."},
    )
    _assert_status(client_reply, 201, "client.support_reply")
    resolved = client.post(
        f"/api/v1/admin/support/tickets/{ticket_id}/resolve",
        headers={**_headers(support, "support_resolve"), "Content-Type": "application/json"},
        json={"reason": "Resuelto en smoke funcional"},
    )
    _assert_status(resolved, 200, "support.resolve")
    closed = client.post(
        f"/api/v1/admin/support/tickets/{ticket_id}/close",
        headers={**_headers(support, "support_close"), "Content-Type": "application/json"},
        json={"reason": "Cerrado en smoke funcional"},
    )
    _assert_status(closed, 200, "support.close")
    return {
        "client_ticket_id": ticket_id,
        "business_ticket_id": _json_data(business_ticket)["id"],
        "admin_support_items": len(_json_data(listed)["items"]),
        "closed_status": _json_data(closed)["status"],
        "order_status_after_support": client.app.state.order_repository.get_by_id(order["id"]).status,
        "business_id_unchanged": business["id"] == client.app.state.ad_repository.get_ad(ad["id"]).business_id,
    }


def run_smoke() -> dict:
    client = TestClient(create_app())
    admin = _login(client, 880001, "surface_admin")
    owner = _login(client, 880002, "surface_owner")
    remitter = _login(client, 880003, "surface_client")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "super_admin")
    support, staff_profile_id = _make_staff_user(client, admin)
    client_profile = _run_client_onboarding(client, remitter)
    intake = _run_business_intake_flow(client, admin)

    business, payment_method_id = _create_approved_business(client, owner, admin)
    business_pin = _setup_business_pin(client, owner)
    base_usdc = _run_base_usdc_credit_flow(client, owner)

    surface = client.get("/api/v1/surface/session", headers={**_bearer(owner, "surface_session"), "X-NODO-Surface": "business_mini_app"})
    _assert_status(surface, 200, "business.surface_session")

    ad_response = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "create_ad"), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment_method_id,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "20.00",
            "amount_max_usd": "100.00",
        },
    )
    _assert_status(ad_response, 201, "business.create_ad")
    ad = _json_data(ad_response)["ad"]

    search = client.get(
        "/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&delivery_method=pago_movil_ve&sort=rate",
        headers=_bearer(remitter, "client_marketplace"),
    )
    _assert_status(search, 200, "client.marketplace_search")

    order_response = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "create_order"), "Content-Type": "application/json"},
        json={
            "ad_id": ad["id"],
            "amount_usd": "50.00",
            "receiver_data": {"bank": "Banco", "phone": "+584121234567", "document": "V12345678", "holder": "Receptor Smoke"},
        },
    )
    _assert_status(order_response, 201, "client.create_order")
    order = _json_data(order_response)["order"]

    instructions = client.get(f"/api/v1/orders/{order['id']}/payment-instructions", headers=_bearer(remitter, "client_instructions"))
    _assert_status(instructions, 200, "client.payment_instructions")

    evidence = client.post(
        f"/api/v1/orders/{order['id']}/payment-evidence",
        headers=_headers(remitter, "payment_evidence"),
        data={"file_type": "payment_evidence"},
        files={"file": ("proof.png", b"proof", "image/png")},
    )
    _assert_status(evidence, 201, "client.payment_evidence")
    evidence_data = _json_data(evidence)

    report = client.post(
        f"/api/v1/orders/{order['id']}/payment-report",
        headers={**_headers(remitter, "payment_report"), "Content-Type": "application/json"},
        json={
            "payment_type": "zelle",
            "payment_reference": "ABC123456",
            "payment_sender_name": "Client Smoke",
            "payment_sender_account_masked": "***1234",
            "payment_amount": "50.00",
            "proof_file_id": evidence_data["file"]["id"],
            "pending_payment_report_id": evidence_data["pending_payment_report_id"],
        },
    )
    _assert_status(report, 201, "client.payment_report")

    business_orders = client.get("/api/v1/business/orders?limit=20", headers=_bearer(owner, "business_orders"))
    _assert_status(business_orders, 200, "business.orders")

    client_message = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(remitter, "client_message"), "Content-Type": "application/json"},
        json={"body": "Hola, pago reportado."},
    )
    _assert_status(client_message, 201, "client.message")

    business_message = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(owner, "business_message"), "Content-Type": "application/json"},
        json={"body": "Recibido, revisando."},
    )
    _assert_status(business_message, 201, "business.message")

    messages = client.get(f"/api/v1/orders/{order['id']}/messages", headers=_bearer(remitter, "client_messages"))
    _assert_status(messages, 200, "client.messages")

    confirm = client.post(
        f"/api/v1/business/orders/{order['id']}/confirm-payment",
        headers={**_headers(owner, "business_confirm"), "Content-Type": "application/json"},
        json={"reason": "Pago recibido"},
    )
    _assert_status(confirm, 200, "business.confirm_payment")

    support_flow = _run_support_flow(client, remitter=remitter, owner=owner, support=support, admin=admin, order=order, business=business, ad=ad)

    admin_dashboard = client.get("/api/v1/admin/dashboard", headers=_bearer(admin, "admin_dashboard"))
    _assert_status(admin_dashboard, 200, "admin.dashboard")
    admin_order = client.get(f"/api/v1/admin/orders/{order['id']}", headers=_bearer(admin, "admin_order_detail"))
    _assert_status(admin_order, 200, "admin.order_detail")
    audit = client.get("/api/v1/admin/audit-logs", headers=_bearer(admin, "admin_audit"))
    _assert_status(audit, 200, "admin.audit_logs")

    wallet = client.app.state.ad_repository.get_wallet(business["id"])
    return {
        "status": "PASS",
        "surfaces": ["client_mini_app_backend", "business_mini_app_backend", "admin_web_backend"],
        "ids": {"business_id": business["id"], "ad_id": ad["id"], "order_id": order["id"]},
        "client": {
            "profile_phone_saved": bool(client_profile.get("phone")),
            "terms_accepted": bool(client_profile.get("terms_accepted_at")),
            "marketplace_items": len(_json_data(search)["items"]),
            "order_status_after_create": order["status"],
            "messages_seen": len(_json_data(messages)["items"]),
        },
        "business_intake_bot": intake,
        "base_usdc_credits": base_usdc,
        "business": {
            "surface_allowed": _json_data(surface)["allowed"],
            "pin_configured": business_pin["configured"],
            "pin_unlocked": business_pin["unlocked"],
            "orders_seen": len(_json_data(business_orders)["items"]),
            "confirm_status": _json_data(confirm)["order"]["status"],
            "wallet_available": wallet.available_credits,
            "wallet_consumed": wallet.consumed_credits,
        },
        "admin": {
            "dashboard_keys": sorted(_json_data(admin_dashboard).keys()),
            "order_detail_loaded": bool(_json_data(admin_order)["order"]["id"]),
            "audit_items": len(_json_data(audit)["items"]),
            "staff_profile_id": staff_profile_id,
        },
        "support": support_flow,
        "sensitive_scan": {
            "storage_path_in_responses": any("storage_path" in item for item in [instructions.text, evidence.text, admin_order.text, audit.text]),
            "full_account_in_admin_order": "owner@example.com" in admin_order.text,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local cross-surface smoke for client, business, and admin flows.")
    parser.add_argument("--output", default="evidence/slice_runs/local_surface_cross_smoke.json")
    args = parser.parse_args()
    result = run_smoke()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
