from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


BOT_CREDENTIAL = "123456:test-case-file-credential"


def _set_env() -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-46b",
        "NODO_BUILD_ID": "pytest-admin-case-file",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
        "BOT_TOKEN": BOT_CREDENTIAL,
        "JWT_SECRET": "test-case-file-access-credential",
        "JWT_REFRESH_SECRET": "test-case-file-refresh-credential",
        "AUTH_INIT_DATA_MAX_AGE_SECONDS": "86400",
        "ACCESS_TOKEN_TTL_SECONDS": "900",
        "REFRESH_TOKEN_TTL_SECONDS": "2592000",
        "AUTH_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "AUTH_RATE_LIMIT_WINDOW_SECONDS": "60",
        "BUSINESS_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "BUSINESS_RATE_LIMIT_WINDOW_SECONDS": "60",
    }
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app  # noqa: E402
from app.modules.business_intake.models import BusinessIntakeDocumentRecord, BusinessIntakeRequestRecord  # noqa: E402
from app.modules.businesses.models import BusinessRecord, utc_now  # noqa: E402
from app.modules.orders.models import OrderRecord, PaymentReportRecord  # noqa: E402
from app.modules.support.models import SupportTicketRecord  # noqa: E402


def _client() -> TestClient:
    _set_env()
    return TestClient(create_app())


def _signed_init_data(telegram_id: int, username: str) -> str:
    payload = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": telegram_id, "username": username, "first_name": username}, separators=(",", ":"), sort_keys=True),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", BOT_CREDENTIAL.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


def _login(client: TestClient, telegram_id: int, username: str, *, role: str = "remitter") -> dict:
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
    if role != "remitter":
        client.app.state.user_repository.set_user_role(login["user"]["id"], role)
    return login


def _bearer(login: dict, request_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": request_id}


def _seed_case(client: TestClient, *, archived_ticket: bool = False) -> dict[str, str]:
    now = utc_now()
    remitter = _login(client, 46001, "case_client")
    owner = _login(client, 46002, "case_owner")
    business_id = str(uuid4())
    order_id = str(uuid4())
    ticket_id = str(uuid4())
    intake_id = str(uuid4())
    business = BusinessRecord(
        id=business_id,
        owner_user_id=owner["user"]["id"],
        business_name="Negocio Caso",
        rif="J-private",
        address="Direccion privada",
        phone="+584121234567",
        verification_status="approved",
        trust_level="premium",
        risk_level="under_review",
        created_at=now,
        updated_at=now,
    )
    client.app.state.business_repository.businesses[business.id] = business
    intake = BusinessIntakeRequestRecord(
        id=intake_id,
        telegram_user_id=46002,
        telegram_chat_id=999001,
        status="accepted",
        business_name="Negocio Caso",
        business_tax_id="J-private",
        responsible_name="Persona privada",
        responsible_id_number="V-private",
        city="Caracas",
        business_phone="+584121234567",
        references_json=["referencia privada"],
        created_business_id=business_id,
        linked_telegram_user_id=46002,
        created_at=now,
        updated_at=now,
    )
    client.app.state.business_intake_repository.intakes[intake.id] = intake
    order = OrderRecord(
        id=order_id,
        public_order_code="NODO-CASE460",
        ad_id=str(uuid4()),
        business_id=business_id,
        remitter_user_id=remitter["user"]["id"],
        status="completed",
        idempotency_key="private-idempotency",
        amount_usd=Decimal("50.00"),
        rate_snapshot=Decimal("39.50"),
        amount_bs_calculated=Decimal("1975.00"),
        business_name_snapshot="Negocio Caso",
        payment_method_snapshot="zelle-private",
        delivery_method_snapshot="pago_movil_ve",
        min_amount_snapshot=Decimal("20.00"),
        max_amount_snapshot=Decimal("100.00"),
        payment_instructions_snapshot={"account_value": "private@example.com"},
        receiver_data_json={"phone": "+584121234567", "document": "V-private"},
        payment_report_deadline_at=now + timedelta(minutes=15),
        expires_at=now + timedelta(hours=1),
        completed_at=now,
        created_at=now,
        updated_at=now,
    )
    client.app.state.order_repository.orders[order.id] = order
    report = PaymentReportRecord(
        id=str(uuid4()),
        order_id=order.id,
        reported_by_user_id=remitter["user"]["id"],
        status="confirmed",
        idempotency_key="private-report-key",
        payment_type="zelle",
        payment_amount=Decimal("50.00"),
        payment_reference="private-reference",
        payment_sender_name="Persona privada",
        payment_sender_account_masked="***1234",
        proof_file_id=str(uuid4()),
        created_at=now,
        updated_at=now,
    )
    client.app.state.order_repository.payment_reports[report.id] = report
    ticket = SupportTicketRecord(
        id=ticket_id,
        requester_user_id=remitter["user"]["id"],
        requester_role="remitter",
        requester_surface="client_mini_app",
        scope="client_order",
        category="order_help",
        status="resolved" if archived_ticket else "open",
        priority="normal",
        subject="Texto privado del ticket",
        business_id=business_id,
        order_id=order_id,
        created_at=now,
        updated_at=now,
        resolved_at=now if archived_ticket else None,
    )
    client.app.state.support_repository.tickets[ticket.id] = ticket
    client.app.state.support_repository.create_message(
        ticket_id=ticket.id,
        sender_user_id=remitter["user"]["id"],
        sender_role="remitter",
        body="Mensaje privado con PIN 1234 y wallet 0x1234567890.",
        visibility="participants",
    )
    client.app.state.chat_repository.create_message(
        order_id=order.id,
        sender_user_id=owner["user"]["id"],
        sender_role="business_owner",
        body="Chat privado de la orden.",
        idempotency_key="case-chat",
    )
    return {
        "user": remitter["user"]["id"],
        "business": business_id,
        "business_intake": intake_id,
        "order": order_id,
        "support_ticket": ticket_id,
    }


@pytest.mark.parametrize("anchor_type", ["user", "business", "business_intake", "order", "support_ticket"])
def test_admin_case_file_supports_five_exact_anchors_without_private_payloads(anchor_type: str) -> None:
    client = _client()
    anchors = _seed_case(client, archived_ticket=True)
    admin = _login(client, 46003, "case_admin", role="admin")

    response = client.get(
        f"/api/v1/admin/investigation/case-file?anchor_type={anchor_type}&anchor_id={anchors[anchor_type]}&include_archived=true",
        headers=_bearer(admin, f"req_case_{anchor_type}"),
    )

    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    payload = response.json()["data"]
    assert payload["anchor"]["type"] == anchor_type
    assert payload["anchor"]["id"] == anchors[anchor_type]
    assert payload["support_tickets"]["items"][0]["status"] == "resolved"
    assert payload["evidence"]["chat_evidence_available"] is True
    serialized = json.dumps(payload).lower()
    for forbidden in (
        "severity_hint",
        "suggested_next_step",
        "storage_path",
        "signed_url",
        "account_value",
        "payment_instructions_snapshot",
        "receiver_data_json",
        "risk_level",
        "trust_level",
        "texto privado",
        "mensaje privado",
        "chat privado",
        "private-reference",
        "private-idempotency",
        "+584121234567",
        "0x1234567890",
        "pin 1234",
    ):
        assert forbidden not in serialized
    audit = [event for event in client.app.state.audit_writer.events if event.event_type == "admin_investigation_case_file_viewed"]
    assert len(audit) == 1
    audit_serialized = json.dumps(audit[0].metadata_json).lower()
    assert "mensaje privado" not in audit_serialized
    assert "texto privado" not in audit_serialized


def test_case_file_requires_admin_surface_authentication() -> None:
    client = _client()
    anchors = _seed_case(client)
    remitter = _login(client, 46004, "unauthorized_case_user")

    no_session = client.get(f"/api/v1/admin/investigation/case-file?anchor_type=order&anchor_id={anchors['order']}")
    remitter_response = client.get(
        f"/api/v1/admin/investigation/case-file?anchor_type=order&anchor_id={anchors['order']}",
        headers=_bearer(remitter, "req_case_forbidden"),
    )

    assert no_session.status_code == 401
    assert remitter_response.status_code == 403


def test_case_file_rejects_invalid_anchor_and_malformed_cursor_safely() -> None:
    client = _client()
    anchors = _seed_case(client)
    admin = _login(client, 46011, "case_invalid_admin", role="admin")

    invalid_anchor = client.get(
        f"/api/v1/admin/investigation/case-file?anchor_type=unknown&anchor_id={anchors['order']}",
        headers=_bearer(admin, "req_case_invalid_anchor"),
    )
    invalid_cursor = client.get(
        (
            f"/api/v1/admin/investigation/case-file?anchor_type=order&anchor_id={anchors['order']}"
            "&section=orders&cursor=not-a-valid-cursor"
        ),
        headers=_bearer(admin, "req_case_invalid_cursor"),
    )

    assert invalid_anchor.status_code == 404
    assert invalid_anchor.json()["error"]["code"] == "ADMIN_CASE_FILE_ANCHOR_INVALID"
    assert invalid_cursor.status_code == 400
    assert invalid_cursor.json()["error"]["code"] == "ADMIN_CASE_FILE_CURSOR_INVALID"


def test_support_can_only_open_policy_visible_anchor_and_inactive_staff_is_hidden() -> None:
    client = _client()
    anchors = _seed_case(client)
    super_admin = _login(client, 46005, "case_super_admin", role="super_admin")
    support = _login(client, 46006, "case_support", role="support")
    profile = client.app.state.staff_repository.create_or_activate_profile(
        user_id=support["user"]["id"],
        staff_role="support_agent",
        display_name="Support Case",
        actor_id=super_admin["user"]["id"],
        reason="case file test",
    )
    client.app.state.staff_repository.replace_permissions(
        profile_id=profile.id,
        permissions=[{"permission": "view_support_queue", "scope": "queue_scope", "scope_value": None}],
        actor_id=super_admin["user"]["id"],
        reason="case file test",
    )

    visible = client.get(
        f"/api/v1/admin/investigation/case-file?anchor_type=support_ticket&anchor_id={anchors['support_ticket']}",
        headers=_bearer(support, "req_case_support_visible"),
    )
    hidden = client.get(
        f"/api/v1/admin/investigation/case-file?anchor_type=business_intake&anchor_id={anchors['business_intake']}",
        headers=_bearer(support, "req_case_support_hidden"),
    )
    assert visible.status_code == 200, visible.text
    assert visible.json()["data"]["evidence"]["documents"] == []
    assert hidden.status_code == 404

    client.app.state.staff_repository.set_profile_status(
        profile_id=profile.id,
        status="suspended",
        actor_id=super_admin["user"]["id"],
        reason="case file inactive staff",
    )
    inactive = client.get(
        f"/api/v1/admin/investigation/case-file?anchor_type=support_ticket&anchor_id={anchors['support_ticket']}",
        headers=_bearer(support, "req_case_support_inactive"),
    )
    assert inactive.status_code == 404


def test_case_file_section_cursor_is_bound_to_anchor_section_and_filter() -> None:
    client = _client()
    anchors = _seed_case(client)
    base_order = client.app.state.order_repository.orders[anchors["order"]]
    for index in range(3):
        order = replace(
            base_order,
            id=str(uuid4()),
            public_order_code=f"NODO-PAGE{index}",
            created_at=base_order.created_at - timedelta(minutes=index + 1),
            updated_at=base_order.updated_at - timedelta(minutes=index + 1),
        )
        client.app.state.order_repository.orders[order.id] = order
    admin = _login(client, 46007, "case_cursor_admin", role="admin")
    first = client.get(
        f"/api/v1/admin/investigation/case-file?anchor_type=user&anchor_id={anchors['user']}&section=orders&limit=1",
        headers=_bearer(admin, "req_case_cursor_first"),
    )
    assert first.status_code == 200, first.text
    first_data = first.json()["data"]
    cursor = first_data["orders"]["next_cursor"]
    assert cursor
    second = client.get(
        f"/api/v1/admin/investigation/case-file?anchor_type=user&anchor_id={anchors['user']}&section=orders&limit=1&cursor={cursor}",
        headers=_bearer(admin, "req_case_cursor_second"),
    )
    assert second.status_code == 200, second.text
    assert second.json()["data"]["orders"]["items"][0]["id"] != first_data["orders"]["items"][0]["id"]
    wrong_section = client.get(
        f"/api/v1/admin/investigation/case-file?anchor_type=user&anchor_id={anchors['user']}&section=support_tickets&limit=1&cursor={cursor}",
        headers=_bearer(admin, "req_case_cursor_wrong_section"),
    )
    wrong_filter = client.get(
        f"/api/v1/admin/investigation/case-file?anchor_type=user&anchor_id={anchors['user']}&section=orders&limit=1&include_archived=false&cursor={cursor}",
        headers=_bearer(admin, "req_case_cursor_wrong_filter"),
    )
    wrong_anchor = client.get(
        f"/api/v1/admin/investigation/case-file?anchor_type=business&anchor_id={anchors['business']}&section=orders&limit=1&cursor={cursor}",
        headers=_bearer(admin, "req_case_cursor_wrong_anchor"),
    )
    assert wrong_section.status_code == 400
    assert wrong_filter.status_code == 400
    assert wrong_anchor.status_code == 400


def test_case_file_evidence_has_its_own_cursor_without_exposing_file_ids() -> None:
    client = _client()
    anchors = _seed_case(client)
    now = utc_now()
    for index in range(2):
        document = BusinessIntakeDocumentRecord(
            id=str(uuid4()),
            owner_user_id=anchors["user"],
            resource_type="business_intake",
            resource_id=anchors["business_intake"],
            file_type="intake_document",
            storage_path=f"private/intake/{index}/secret.png",
            mime_type="image/png",
            size_bytes=100 + index,
            document_kind=f"document_{index}",
            created_at=now - timedelta(seconds=index),
        )
        client.app.state.business_intake_repository.documents[document.id] = document
    admin = _login(client, 46010, "case_evidence_admin", role="super_admin")

    first = client.get(
        f"/api/v1/admin/investigation/case-file?anchor_type=business_intake&anchor_id={anchors['business_intake']}&section=evidence&limit=1",
        headers=_bearer(admin, "req_case_evidence_first"),
    )

    assert first.status_code == 200, first.text
    evidence = first.json()["data"]["evidence"]
    assert evidence["truncated"] is True
    assert evidence["next_cursor"]
    assert len(evidence["documents"]) == 1
    assert "storage_path" not in json.dumps(evidence).lower()
    assert "file_asset_id" not in json.dumps(evidence).lower()
    second = client.get(
        (
            f"/api/v1/admin/investigation/case-file?anchor_type=business_intake"
            f"&anchor_id={anchors['business_intake']}&section=evidence&limit=1&cursor={evidence['next_cursor']}"
        ),
        headers=_bearer(admin, "req_case_evidence_second"),
    )
    assert second.status_code == 200, second.text
    assert second.json()["data"]["evidence"]["documents"][0]["document_type"] != evidence["documents"][0]["document_type"]


def test_case_file_keeps_other_sections_when_one_repository_section_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()
    anchors = _seed_case(client)
    admin = _login(client, 46008, "case_partial_admin", role="admin")

    def fail_orders(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("private database detail")

    monkeypatch.setattr(client.app.state.admin_case_file_repository, "page_orders", fail_orders)
    response = client.get(
        f"/api/v1/admin/investigation/case-file?anchor_type=order&anchor_id={anchors['order']}",
        headers=_bearer(admin, "req_case_partial"),
    )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["orders"]["status"] == "partial_error"
    assert payload["orders"]["error"]["code"] == "ADMIN_CASE_FILE_SECTION_UNAVAILABLE"
    assert "private database detail" not in json.dumps(payload)
    assert payload["support_tickets"]["status"] == "ok"
    assert payload["evidence"]["status"] == "ok"


def test_case_file_includes_active_and_archived_tickets_when_requested() -> None:
    client = _client()
    anchors = _seed_case(client, archived_ticket=True)
    archived = client.app.state.support_repository.tickets[anchors["support_ticket"]]
    active = replace(
        archived,
        id=str(uuid4()),
        status="open",
        resolved_at=None,
        created_at=archived.created_at + timedelta(seconds=1),
        updated_at=archived.updated_at + timedelta(seconds=1),
    )
    client.app.state.support_repository.tickets[active.id] = active
    admin = _login(client, 46009, "case_archive_admin", role="admin")

    response = client.get(
        f"/api/v1/admin/investigation/case-file?anchor_type=order&anchor_id={anchors['order']}&include_archived=true",
        headers=_bearer(admin, "req_case_archive"),
    )

    assert response.status_code == 200, response.text
    statuses = {item["status"] for item in response.json()["data"]["support_tickets"]["items"]}
    assert statuses == {"open", "resolved"}
    active_only = client.get(
        f"/api/v1/admin/investigation/case-file?anchor_type=order&anchor_id={anchors['order']}&include_archived=false",
        headers=_bearer(admin, "req_case_active_only"),
    )
    assert active_only.status_code == 200, active_only.text
    assert {item["status"] for item in active_only.json()["data"]["support_tickets"]["items"]} == {"open"}


def test_case_file_frontend_contract_is_separate_and_read_only() -> None:
    root = Path(__file__).resolve().parents[3]
    screen = (root / "apps/web/src/screens/admin-web/AdminInvestigationCaseFileScreen.tsx").read_text(encoding="utf-8")
    playbook = (root / "apps/web/src/screens/admin-web/AdminInvestigationCasePlaybookPanel.tsx").read_text(encoding="utf-8")
    model = (root / "apps/web/src/hooks/admin-web/useAdminInvestigationCaseFileModel.ts").read_text(encoding="utf-8")
    investigation = (root / "apps/web/src/screens/admin-web/AdminInvestigationScreens.tsx").read_text(encoding="utf-8")

    assert "Investigar" in investigation
    assert "case-file" in model
    assert "openOrder" in model
    assert "activeCaseKey" in model
    assert "openRequestSeq" in model
    assert "sectionRequestSeq" in model
    assert "readOnly" in screen
    assert "<textarea" not in screen
    assert "Enviar" not in screen
    assert "AdminInvestigationCasePlaybookPanel" in screen
    assert "Orden relacionada" in playbook
    assert "Reporte de pago" in playbook
    assert "Ticket relacionado" in playbook
    assert "Chat de orden" in playbook
    assert "Evidencia relacionada" in playbook
    assert "Intake relacionado" in playbook
    assert "Pantalla disponible" in playbook
    assert "onOpenRoute" in playbook
    assert "<textarea" not in playbook
    assert "fetch(" not in playbook
    assert "file_asset_id" not in playbook
    assert "storage_path" not in playbook
    assert "signed_url" not in playbook
    prohibited_claims = ("fraude", "culpa", "pago valido", "pago falso", "recuperacion garantizada")
    assert not any(claim in playbook.lower() for claim in prohibited_claims)
