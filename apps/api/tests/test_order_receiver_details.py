from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
import pytest

from test_business_order_ops import (
    _bearer,
    _client,
    _headers,
    _login,
    _seed_reported_order,
)


RECEIVER_DETAILS = {
    "bank": "0102",
    "phone": "+584121234567",
    "document": "V12345678",
    "holder": "Receptor Test",
}


def _confirm_payment(client, owner: dict, order_id: str, *, key: str) -> None:  # type: ignore[no-untyped-def]
    response = client.post(
        f"/api/v1/business/orders/{order_id}/confirm-payment",
        headers={**_headers(owner, key), "Content-Type": "application/json"},
        json={"reason": "Pago recibido"},
    )
    assert response.status_code == 200, response.text


def _share_receiver_details(client, remitter: dict, order_id: str, *, key: str, payload: dict | None = None):  # type: ignore[no-untyped-def]
    return client.put(
        f"/api/v1/orders/{order_id}/receiver-details",
        headers={**_headers(remitter, key), "Content-Type": "application/json"},
        json=payload or RECEIVER_DETAILS,
    )


def _mark_delivered(client, owner: dict, order_id: str, *, key: str):  # type: ignore[no-untyped-def]
    return client.post(
        f"/api/v1/business/orders/{order_id}/mark-delivered",
        headers={**_headers(owner, key), "Content-Type": "application/json"},
        json={"reason": "Pago movil enviado"},
    )


def _receiver_audits(client) -> list:  # type: ignore[no-untyped-def]
    return [
        event
        for event in client.app.state.audit_writer.events
        if event.event_type.startswith("order_receiver_details_")
    ]


def _receiver_notifications(client) -> list:  # type: ignore[no-untyped-def]
    return [
        job
        for job in client.app.state.job_repository.notification_jobs.values()
        if job.notification_type == "order_receiver_details_shared_business"
    ]


def test_receiver_details_are_first_write_immutable_idempotent_and_private() -> None:
    client = _client()
    owner, business, _, remitter, order = _seed_reported_order(
        client,
        owner_id=5000,
        remitter_id=5001,
    )
    _confirm_payment(client, owner, order["id"], key="receiver_confirm")

    first = _share_receiver_details(client, remitter, order["id"], key="receiver_share")
    replay = _share_receiver_details(client, remitter, order["id"], key="receiver_share")
    same_payload_new_key = _share_receiver_details(
        client,
        remitter,
        order["id"],
        key="receiver_share_second_key",
    )
    mismatch_same_key = _share_receiver_details(
        client,
        remitter,
        order["id"],
        key="receiver_share",
        payload={**RECEIVER_DETAILS, "holder": "Otra Persona"},
    )
    changed_new_key = _share_receiver_details(
        client,
        remitter,
        order["id"],
        key="receiver_share_changed",
        payload={**RECEIVER_DETAILS, "holder": "Otra Persona"},
    )

    assert first.status_code == 200, first.text
    assert replay.status_code == 200, replay.text
    assert same_payload_new_key.status_code == 200, same_payload_new_key.text
    assert mismatch_same_key.status_code == 409
    assert mismatch_same_key.json()["error"]["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"
    assert changed_new_key.status_code == 409
    assert changed_new_key.json()["error"]["code"] == "ORDER_RECEIVER_DETAILS_ALREADY_SHARED"
    assert first.json()["data"] == replay.json()["data"] == same_payload_new_key.json()["data"]
    assert len(_receiver_audits(client)) == 1
    assert len(_receiver_notifications(client)) == 1
    assert _receiver_notifications(client)[0].recipient_user_id == client.app.state.business_repository.get_business(business["id"]).owner_user_id
    notification_text = _receiver_notifications(client)[0].metadata_json["message_text"].lower()
    for forbidden in ("pago movil", "zelle", "usdt", "wallet", "+584121234567", "v12345678"):
        assert forbidden not in notification_text

    combined = first.text + json.dumps(
        [event.__dict__ for event in _receiver_audits(client)]
        + [job.__dict__ for job in _receiver_notifications(client)],
        default=str,
    )
    assert "+584121234567" not in combined
    assert "V12345678" not in combined
    assert "Receptor Test" not in combined
    assert "storage_path" not in combined
    assert "signed_url" not in combined


@pytest.mark.parametrize(
    "status",
    ["waiting_payment", "payment_reported", "delivered", "completed", "cancelled"],
)
def test_receiver_details_first_creation_rejects_invalid_order_states(status: str) -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(
        client,
        owner_id=5100 + len(status),
        remitter_id=5200 + len(status),
    )
    stored = client.app.state.order_repository.get_by_id(order["id"])
    if status == "payment_reported":
        pass
    elif status == "waiting_payment":
        client.app.state.order_repository.update_order(stored, status=status)
    else:
        _confirm_payment(client, owner, order["id"], key=f"confirm_{status}")
        client.app.state.order_repository.update_order(stored, status=status)

    response = _share_receiver_details(
        client,
        remitter,
        order["id"],
        key=f"receiver_invalid_{status}",
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ORDER_STATUS_INVALID"


def test_receiver_details_validate_payload_and_reject_extra_fields() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(
        client,
        owner_id=5300,
        remitter_id=5301,
    )
    _confirm_payment(client, owner, order["id"], key="receiver_validate_confirm")

    invalid = _share_receiver_details(
        client,
        remitter,
        order["id"],
        key="receiver_invalid_payload",
        payload={**RECEIVER_DETAILS, "bank": "Banco inventado", "extra": "no"},
    )

    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "ORDER_RECEIVER_DETAILS_INVALID"


@pytest.mark.parametrize(
    "phone",
    [
        "0414 1234567",
        "0416-123-4567",
        "+58 (414) 123-4567",
    ],
)
def test_receiver_details_accept_common_phone_formats_without_forcing_country_code(phone: str) -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(
        client,
        owner_id=5350 + len(phone),
        remitter_id=5450 + len(phone),
    )
    _confirm_payment(client, owner, order["id"], key=f"receiver_local_phone_confirm_{len(phone)}")

    shared = _share_receiver_details(
        client,
        remitter,
        order["id"],
        key=f"receiver_local_phone_share_{len(phone)}",
        payload={**RECEIVER_DETAILS, "phone": phone},
    )
    revealed = client.get(
        f"/api/v1/orders/{order['id']}/receiver-details",
        headers=_bearer(remitter, f"receiver_local_phone_reveal_{len(phone)}"),
    )

    assert shared.status_code == 200, shared.text
    assert revealed.status_code == 200, revealed.text
    assert revealed.json()["data"]["phone"] == phone
    assert not shared.json()["data"]["receiver_details_masked"]["phone"].startswith("+58")


@pytest.mark.parametrize("phone", ["123", "telefono 0414", "<04141234567>"])
def test_receiver_details_reject_unusable_or_unsafe_phone_values(phone: str) -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(
        client,
        owner_id=5550 + len(phone),
        remitter_id=5650 + len(phone),
    )
    _confirm_payment(client, owner, order["id"], key=f"receiver_bad_phone_confirm_{len(phone)}")

    response = _share_receiver_details(
        client,
        remitter,
        order["id"],
        key=f"receiver_bad_phone_share_{len(phone)}",
        payload={**RECEIVER_DETAILS, "phone": phone},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ORDER_RECEIVER_DETAILS_INVALID"


def test_receiver_details_reveal_is_participant_only_audited_and_no_store() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(
        client,
        owner_id=5400,
        remitter_id=5401,
    )
    _confirm_payment(client, owner, order["id"], key="receiver_reveal_confirm")
    assert _share_receiver_details(client, remitter, order["id"], key="receiver_reveal_share").status_code == 200

    remitter_reveal = client.get(
        f"/api/v1/orders/{order['id']}/receiver-details",
        headers=_bearer(remitter, "receiver_reveal_remitter"),
    )
    business_reveal = client.get(
        f"/api/v1/orders/{order['id']}/receiver-details",
        headers=_bearer(owner, "receiver_reveal_business"),
    )
    outsider = _login(client, 5402, "receiver_outsider")
    outsider_reveal = client.get(
        f"/api/v1/orders/{order['id']}/receiver-details",
        headers=_bearer(outsider, "receiver_reveal_outsider"),
    )
    admin = _login(client, 5403, "receiver_admin")
    client.app.state.user_repository.get_user_by_id(admin["user"]["id"]).role = "admin"
    admin_reveal = client.get(
        f"/api/v1/orders/{order['id']}/receiver-details",
        headers=_bearer(admin, "receiver_reveal_admin"),
    )
    support = _login(client, 5404, "receiver_support")
    client.app.state.user_repository.get_user_by_id(support["user"]["id"]).role = "support"
    support_reveal = client.get(
        f"/api/v1/orders/{order['id']}/receiver-details",
        headers=_bearer(support, "receiver_reveal_support"),
    )

    for response in (remitter_reveal, business_reveal):
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "private, no-store"
        assert response.json()["data"]["phone"] == RECEIVER_DETAILS["phone"]
    assert outsider_reveal.status_code == 404
    assert admin_reveal.status_code == 403
    assert support_reveal.status_code == 403
    assert len(_receiver_audits(client)) == 3
    audit_dump = json.dumps([event.__dict__ for event in _receiver_audits(client)], default=str)
    for private_value in RECEIVER_DETAILS.values():
        assert private_value not in audit_dump


def test_mark_delivered_requires_structured_payment_mobile_details() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(
        client,
        owner_id=5500,
        remitter_id=5501,
    )
    _confirm_payment(client, owner, order["id"], key="receiver_gate_confirm")

    blocked = _mark_delivered(client, owner, order["id"], key="receiver_gate_blocked")

    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["error"]["code"] == "ORDER_RECEIVER_DETAILS_REQUIRED"
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "payment_confirmed"

    shared = _share_receiver_details(client, remitter, order["id"], key="receiver_gate_share")
    delivered = _mark_delivered(client, owner, order["id"], key="receiver_gate_delivered")

    assert shared.status_code == 200, shared.text
    assert delivered.status_code == 200, delivered.text
    assert delivered.json()["data"]["order"]["status"] == "delivered"


def test_confirm_received_completes_once_consumes_capacity_and_not_credit() -> None:
    client = _client()
    owner, business, _, remitter, order = _seed_reported_order(
        client,
        owner_id=5600,
        remitter_id=5601,
    )
    _confirm_payment(client, owner, order["id"], key="receiver_complete_confirm")
    assert _share_receiver_details(client, remitter, order["id"], key="receiver_complete_share").status_code == 200
    assert _mark_delivered(client, owner, order["id"], key="receiver_complete_deliver").status_code == 200
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])
    consumed_credits_before = wallet_before.consumed_credits

    first = client.post(
        f"/api/v1/orders/{order['id']}/confirm-received",
        headers=_headers(remitter, "receiver_complete"),
    )
    replay = client.post(
        f"/api/v1/orders/{order['id']}/confirm-received",
        headers=_headers(remitter, "receiver_complete"),
    )

    assert first.status_code == 200, first.text
    assert replay.status_code == 200, replay.text
    assert first.json()["data"] == replay.json()["data"]
    assert first.json()["data"]["order"]["status"] == "completed"
    assert first.json()["data"]["order"]["completion_reason"] == "manual_confirmed"
    assert first.json()["data"]["rating"] == {
        "can_rate": True,
        "already_rated": False,
        "stars": None,
    }
    reservation = client.app.state.capacity_repository.get_reservation(order["id"])
    assert reservation.status == "consumed"
    assert client.app.state.ad_repository.get_wallet(business["id"]).consumed_credits == consumed_credits_before
    assert len(
        [
            event
            for event in client.app.state.order_repository.events
            if event.order_id == order["id"] and event.event_type == "order_completed"
        ]
    ) == 1
    completed_jobs = [
        job
        for job in client.app.state.job_repository.notification_jobs.values()
        if job.notification_type == "order_completed_business" and job.order_id == order["id"]
    ]
    assert len(completed_jobs) == 1


def test_confirm_received_rejects_wrong_state_and_open_dispute() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(
        client,
        owner_id=5700,
        remitter_id=5701,
    )
    _confirm_payment(client, owner, order["id"], key="receiver_dispute_confirm")
    before_delivery = client.post(
        f"/api/v1/orders/{order['id']}/confirm-received",
        headers=_headers(remitter, "receiver_before_delivery"),
    )
    assert before_delivery.status_code == 409
    assert before_delivery.json()["error"]["code"] == "ORDER_RECEIPT_CONFIRMATION_NOT_ALLOWED"

    assert _share_receiver_details(client, remitter, order["id"], key="receiver_dispute_share").status_code == 200
    assert _mark_delivered(client, owner, order["id"], key="receiver_dispute_deliver").status_code == 200
    dispute = client.post(
        f"/api/v1/orders/{order['id']}/disputes",
        headers={**_headers(remitter, "receiver_open_dispute"), "Content-Type": "application/json"},
        json={
            "reason": "payment_mobile_not_received",
            "description": "El receptor no confirma la recepcion.",
            "evidence_file_ids": [],
        },
    )
    assert dispute.status_code == 201, dispute.text
    blocked = client.post(
        f"/api/v1/orders/{order['id']}/confirm-received",
        headers=_headers(remitter, "receiver_blocked_dispute"),
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] in {
        "ORDER_COMPLETION_BLOCKED_BY_DISPUTE",
        "ORDER_RECEIPT_CONFIRMATION_NOT_ALLOWED",
    }
    assert client.app.state.capacity_repository.get_reservation(order["id"]).status == "reserved"


def test_confirm_received_and_dispute_race_has_one_terminal_winner() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(
        client,
        owner_id=5800,
        remitter_id=5801,
    )
    _confirm_payment(client, owner, order["id"], key="receiver_race_confirm")
    assert _share_receiver_details(client, remitter, order["id"], key="receiver_race_share").status_code == 200
    assert _mark_delivered(client, owner, order["id"], key="receiver_race_deliver").status_code == 200

    def complete():  # type: ignore[no-untyped-def]
        return client.post(
            f"/api/v1/orders/{order['id']}/confirm-received",
            headers=_headers(remitter, "receiver_race_complete"),
        )

    def dispute():  # type: ignore[no-untyped-def]
        return client.post(
            f"/api/v1/orders/{order['id']}/disputes",
            headers={**_headers(remitter, "receiver_race_dispute"), "Content-Type": "application/json"},
            json={
                "reason": "payment_mobile_not_received",
                "description": "Revision concurrente.",
                "evidence_file_ids": [],
            },
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = [executor.submit(complete), executor.submit(dispute)]
        results = [future.result() for future in responses]

    assert sum(response.status_code in {200, 201} for response in results) == 1
    assert client.app.state.order_repository.get_by_id(order["id"]).status in {
        "completed",
        "disputed",
    }
    reservation = client.app.state.capacity_repository.get_reservation(order["id"])
    expected_reservation_status = (
        "consumed"
        if client.app.state.order_repository.get_by_id(order["id"]).status == "completed"
        else "reserved"
    )
    assert reservation.status == expected_reservation_status


def test_receiver_details_never_enter_general_chat_or_message_payloads() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(
        client,
        owner_id=5900,
        remitter_id=5901,
    )
    _confirm_payment(client, owner, order["id"], key="receiver_chat_confirm")
    _share_receiver_details(client, remitter, order["id"], key="receiver_chat_share")

    messages = client.get(
        f"/api/v1/orders/{order['id']}/messages?limit=50",
        headers=_bearer(remitter, "receiver_chat_list"),
    )
    assert messages.status_code == 200, messages.text
    for private_value in RECEIVER_DETAILS.values():
        assert private_value not in messages.text


def test_slice_50b2_frontend_uses_structured_compact_chat_ui_and_copy_controls() -> None:
    root = __import__("pathlib").Path(__file__).resolve().parents[3]
    orders_api = (root / "apps/web/src/api/orders.ts").read_text(encoding="utf-8")
    client_chat = (root / "apps/web/src/screens/client/ClientOrderChatScreen.tsx").read_text(encoding="utf-8")
    business_chat = (root / "apps/web/src/screens/business-app/BusinessChatScreen.tsx").read_text(encoding="utf-8")

    assert "/receiver-details" in orders_api
    assert "/confirm-received" in orders_api
    assert "shareReceiverDetails" in client_chat
    assert "receiverDetailsForm" in client_chat
    assert "setReceiverDetailsForm" in client_chat
    assert "Compartir Pago Movil" in client_chat
    assert "Pago Movil compartido" in client_chat
    assert "0414 1234567" in client_chat
    assert 'placeholder="+584121234567"' not in client_chat
    assert 'type="text"' in client_chat
    assert 'type="tel"' in client_chat
    assert "confirmOrderReceived" in client_chat
    assert "Pago Movil pendiente" in business_chat
    assert "revealReceiverDetails" in business_chat
    assert "Copiar telefono" in business_chat
    assert "Copiar cedula" in business_chat
    assert "Copiar banco" in business_chat
    assert "Copiar todo" in business_chat
    assert "navigator.clipboard" in business_chat


def test_slice_50b1_migration_is_reversible_and_keeps_receiver_values_out_of_messages() -> None:
    root = __import__("pathlib").Path(__file__).resolve().parents[3]
    migration_up = (
        root
        / "database/migrations/0040_order_receiver_details_and_manual_completion.up.sql"
    ).read_text(encoding="utf-8")
    migration_down = (
        root
        / "database/migrations/0040_order_receiver_details_and_manual_completion.down.sql"
    ).read_text(encoding="utf-8")

    assert "create table if not exists order_receiver_details" in migration_up
    assert "order_id uuid not null unique" in migration_up
    assert "payload_hash ~ '^[a-f0-9]{64}$'" in migration_up
    assert "order_receiver_details_shared_business" in migration_up
    assert "order_completed_business" in migration_up
    assert "insert into messages" not in migration_up.lower()
    assert "drop table if exists order_receiver_details" in migration_down
