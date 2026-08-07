from __future__ import annotations

from pathlib import Path

import test_support_ticket_center as support
from test_payment_instructions_reports import (
    _bearer,
    _client,
    _headers,
    _seed_order_context,
)
from photo_test_data import png_bytes


ROOT = Path(__file__).resolve().parents[3]
PRIVATE_NO_STORE = "private, no-store"


def test_private_order_chat_and_payment_evidence_responses_are_not_cacheable() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_order_context(
        client,
        owner_id=47_001,
        remitter_id=47_002,
    )

    thread = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(remitter, "47p0_chat_list"),
    )
    instructions = client.get(
        f"/api/v1/orders/{order['id']}/payment-instructions",
        headers=_bearer(remitter, "47p0_payment_instructions"),
    )
    evidence_response = client.post(
        f"/api/v1/orders/{order['id']}/payment-evidence",
        headers=_headers(remitter, "47p0_payment_evidence"),
        data={"file_type": "payment_evidence"},
        files={"file": ("proof.png", png_bytes(b"47p0-local-proof"), "image/png")},
    )
    created_message = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_headers(remitter, "47p0_chat_message"),
        json={"body": "Mensaje sintetico del baseline.", "attachment_ids": []},
    )

    assert thread.status_code == 200, thread.text
    assert instructions.status_code == 200, instructions.text
    assert evidence_response.status_code == 201, evidence_response.text
    assert created_message.status_code == 201, created_message.text
    evidence = evidence_response.json()["data"]
    assert thread.headers["cache-control"] == PRIVATE_NO_STORE
    assert instructions.headers["cache-control"] == PRIVATE_NO_STORE
    assert evidence_response.headers["cache-control"] == PRIVATE_NO_STORE
    assert created_message.headers["cache-control"] == PRIVATE_NO_STORE

    report = client.post(
        f"/api/v1/orders/{order['id']}/payment-report",
        headers={
            **_headers(remitter, "47p0_payment_report"),
            "Content-Type": "application/json",
        },
        json={
            "payment_type": "zelle",
            "payment_amount": "50.00",
            "proof_file_id": evidence["file"]["id"],
            "pending_payment_report_id": evidence["pending_payment_report_id"],
        },
    )
    assert report.status_code == 201, report.text
    assert report.headers["cache-control"] == PRIVATE_NO_STORE

    business_thread = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(owner, "47p0_business_chat_list"),
    )
    assert business_thread.status_code == 200, business_thread.text
    report_message = next(
        message
        for message in business_thread.json()["data"]["system_messages"]
        if message["id"].startswith("system:payment-reported:")
    )
    view = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments/"
        f"{report_message['attachments'][0]['id']}/view-url",
        headers=_headers(owner, "47p0_payment_evidence_view"),
    )
    assert view.status_code == 200, view.text
    assert view.headers["cache-control"] == PRIVATE_NO_STORE


def test_private_support_queue_and_thread_responses_are_not_cacheable() -> None:
    client = support._client()
    requester = support._login(client, 47_101, "47p0_support_requester")
    created_ticket = client.post(
        "/api/v1/support/tickets",
        headers={
            **support._headers(requester, "47p0_support_ticket"),
            "Content-Type": "application/json",
        },
        json={
            "scope": "client_general",
            "category": "technical_issue",
            "subject": "Baseline local",
            "message": "Solicitud sintetica para validar headers.",
        },
    )
    assert created_ticket.status_code == 201, created_ticket.text
    ticket = created_ticket.json()["data"]
    user_message = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/messages",
        headers={
            **support._headers(requester, "47p0_support_user_message"),
            "Content-Type": "application/json",
        },
        json={"body": "Seguimiento sintetico.", "attachment_ids": []},
    )
    assert user_message.status_code == 201, user_message.text
    admin = support._make_admin(client, 47_102, "admin")
    admin_message = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/messages",
        headers={
            **support._headers(admin, "47p0_support_admin_message"),
            "Content-Type": "application/json",
        },
        json={
            "body": "Respuesta sintetica.",
            "visibility": "participants",
            "attachment_ids": [],
        },
    )
    assert admin_message.status_code == 201, admin_message.text

    responses = [
        created_ticket,
        user_message,
        admin_message,
        client.get(
            "/api/v1/support/tickets",
            headers=support._bearer(requester, "47p0_support_list"),
        ),
        client.get(
            f"/api/v1/support/tickets/{ticket['id']}",
            headers=support._bearer(requester, "47p0_support_detail"),
        ),
        client.get(
            "/api/v1/admin/support/tickets",
            headers=support._bearer(admin, "47p0_admin_support_list"),
        ),
        client.get(
            f"/api/v1/admin/support/tickets/{ticket['id']}",
            headers=support._bearer(admin, "47p0_admin_support_detail"),
        ),
    ]

    for response in responses:
        assert response.status_code in {200, 201}, response.text
        assert response.headers["cache-control"] == PRIVATE_NO_STORE


def test_47p0_canonical_harness_covers_current_chat_first_flow_and_local_guards() -> None:
    harness_path = ROOT / "scripts" / "p2p_baseline_local.py"
    assert harness_path.exists()
    source = harness_path.read_text(encoding="utf-8")

    ordered_steps = [
        "/messages",
        "/share-payment-details",
        "/payment-report",
        "/confirm-payment",
        "/receiver-details",
        "/mark-delivered",
        "/confirm-received",
        "/rating",
    ]
    positions = [source.index(step) for step in ordered_steps]
    assert positions == sorted(positions)
    assert '"zelle"' in source
    assert '"usdt_trc20"' in source
    assert '"phone": "0414 1234567"' in source
    assert "receiver_data" not in source
    assert "same_ad_requests: int = 50" in source
    assert "assert_local_database_url" in source
    assert "DATABASE_URL" not in source.split("print", maxsplit=1)[-1]
    assert "nodo-api-production" not in source
    assert "nodo-staging" not in source
    assert "READY_FOR_REAL_USE" not in source


def test_47p0_baseline_document_records_memory_vs_postgres_and_polling_budget() -> None:
    document_path = (
        ROOT
        / "control_plane"
        / "09_SLICES"
        / "slice_47P_performance_cost_load_readiness"
        / "BASELINE_47P0.md"
    )
    assert document_path.exists()
    document = document_path.read_text(encoding="utf-8")

    for required in (
        "PostgreSQL real local",
        "In-memory",
        "| Superficie | Endpoint | Intervalo | Visible-only | No overlap | Backoff | Riesgo |",
        "NOT_TESTED",
        "No cache",
        "No indices",
    ):
        assert required in document
