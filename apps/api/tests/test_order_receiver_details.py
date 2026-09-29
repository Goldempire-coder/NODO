from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
from uuid import UUID

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
    ("document", "expected_document", "expected_mask"),
    [
        ("123456", "123456", "***456"),
        ("12345678", "12345678", "***678"),
        ("1234567890", "1234567890", "***890"),
        ("V12345678", "V12345678", "V***678"),
        ("V-12345678", "V12345678", "V***678"),
        ("e 12.345.678", "E12345678", "E***678"),
        ("J12345678", "J12345678", "J***678"),
        ("G12345678", "G12345678", "G***678"),
        ("P12345678", "P12345678", "P***678"),
    ],
)
def test_receiver_details_accept_document_with_optional_prefix(
    document: str,
    expected_document: str,
    expected_mask: str,
) -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(
        client,
        owner_id=5320,
        remitter_id=5321,
    )
    _confirm_payment(client, owner, order["id"], key="receiver_document_confirm")

    shared = _share_receiver_details(
        client,
        remitter,
        order["id"],
        key="receiver_document_share",
        payload={**RECEIVER_DETAILS, "document": document},
    )
    revealed = client.get(
        f"/api/v1/orders/{order['id']}/receiver-details",
        headers=_bearer(remitter, "receiver_document_reveal"),
    )

    assert shared.status_code == 200, shared.text
    assert shared.json()["data"]["receiver_details_masked"]["document"] == expected_mask
    assert revealed.status_code == 200, revealed.text
    assert revealed.headers["cache-control"] == "private, no-store"
    assert revealed.json()["data"]["document"] == expected_document


@pytest.mark.parametrize(
    "document",
    [
        "12345",
        "12345678901",
        "Q12345678",
        "V12345",
        "ABCDE123456",
        "<12345678>",
        "12/345678",
        "12345678; select 1",
    ],
)
def test_receiver_details_reject_unusable_or_unsafe_document_values(document: str) -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(
        client,
        owner_id=5330,
        remitter_id=5331,
    )
    _confirm_payment(client, owner, order["id"], key="receiver_bad_document_confirm")

    response = _share_receiver_details(
        client,
        remitter,
        order["id"],
        key="receiver_bad_document_share",
        payload={**RECEIVER_DETAILS, "document": document},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ORDER_RECEIVER_DETAILS_INVALID"


@pytest.mark.parametrize(
    "phone",
    [
        "0412 1234567",
        "0414 1234567",
        "0416-123-4567",
        "0424 123 4567",
        "0426 1234567",
        "+584121234567",
        "+584141234567",
        "+584261234567",
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


@pytest.mark.parametrize(
    "phone",
    [
        "123",
        "telefono 0414",
        "<04141234567>",
        "+14155552671",
        "0212 1234567",
        "0414 123456",
        "0414 12345678",
        "+5841412345678",
        "0414/1234567",
        "0414 1234567; select 1",
    ],
)
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
    assert client.app.state.business_repository.get_business(
        business["id"]
    ).ad_publication_paused_until is None

    first = client.post(
        f"/api/v1/orders/{order['id']}/confirm-received",
        headers=_headers(remitter, "receiver_complete"),
    )
    pause_after_first = client.app.state.business_repository.get_business(
        business["id"]
    ).ad_publication_paused_until
    replay = client.post(
        f"/api/v1/orders/{order['id']}/confirm-received",
        headers=_headers(remitter, "receiver_complete"),
    )
    pause_after_replay = client.app.state.business_repository.get_business(
        business["id"]
    ).ad_publication_paused_until

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
    assert pause_after_replay is not None
    assert pause_after_replay == pause_after_first
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


def _assert_receiver_fixture_chat_private(payload: dict, metadata: dict) -> None:
    private_values = (*RECEIVER_DETAILS.values(), "Banco de Venezuela")
    assert payload["data"]["order"]["receiver_data_masked"] == {
        "bank": "Banco",
        "phone": "***4567",
        "document": "***5678",
        "holder": "***st",
    }
    checked_metadata = set()

    def check_text(text: str) -> None:
        assert not any(value in text for value in private_values), "Receiver data exposed"

    def visit(value, path: tuple = ()) -> None:  # type: ignore[no-untyped-def]
        # Only explicit paths bound to fixture records can contain incidental digits.
        if path in metadata:
            kind, expected = metadata[path]
            assert value == expected, "Metadata differs from fixture record"
            if value is None:
                assert kind == "timestamp"
            else:
                assert isinstance(value, str)
                try:
                    if kind == "timestamp":
                        assert datetime.fromisoformat(value).tzinfo is not None
                    elif kind == "uuid":
                        assert str(UUID(value)) == value
                    elif kind == "public_code":
                        assert re.fullmatch(r"NODO-[0-9A-F]{8}", value)
                    elif kind == "system_id":
                        prefix, identifier = value.rsplit(":", 1)
                        assert prefix in {
                            "system:negotiation-created",
                            "system:payment-reported",
                            "system:payment-confirmed",
                            "system:receiver-details-shared",
                        }
                        assert str(UUID(identifier)) == identifier
                    else:
                        raise AssertionError("Unknown metadata kind")
                except ValueError:
                    raise AssertionError("Invalid metadata format") from None
            checked_metadata.add(path)
            return
        if isinstance(value, dict):
            for key, child in value.items():
                check_text(key)
                visit(child, (*path, key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, (*path, index))
        else:
            check_text(json.dumps(value, ensure_ascii=False))

    visit(payload)
    assert checked_metadata == set(metadata), "Expected metadata missing"


def _receiver_privacy_synthetic_case() -> tuple[dict, dict]:
    identifier = "10000000-0102-4000-8000-000000000001"
    timestamp = "2026-09-22T16:51:35.770102+00:00"
    payload = {
        "data": {
            "order": {
                "id": identifier,
                "public_order_code": "NODO-ABCD0102",
                "created_at": timestamp,
                "receiver_data_masked": {
                    "bank": "Banco", "phone": "***4567", "document": "***5678", "holder": "***st",
                },
            },
            "items": [{"body": "Mensaje ficticio", "attachments": [{"mime_type": "image/png"}]}],
            "system_messages": [{"id": f"system:receiver-details-shared:{identifier}", "body": "Aviso generico"}],
            "capabilities": {"receiver_details_shared": True},
            "extra": {"nested": [{}]},
        },
        "request_id": "req_synthetic_privacy",
    }
    metadata = {
        ("data", "order", "id"): ("uuid", identifier),
        ("data", "order", "public_order_code"): ("public_code", "NODO-ABCD0102"),
        ("data", "order", "created_at"): ("timestamp", timestamp),
        ("data", "system_messages", 0, "id"): ("system_id", f"system:receiver-details-shared:{identifier}"),
    }
    return payload, metadata


def test_receiver_privacy_check_accepts_verified_metadata_collisions_without_mutation() -> None:
    payload, metadata = _receiver_privacy_synthetic_case()
    original = deepcopy(payload)
    _assert_receiver_fixture_chat_private(payload, metadata)
    assert payload == original


@pytest.mark.parametrize("field", ["bank", "phone", "document", "holder", "bank_label"])
@pytest.mark.parametrize(
    "path",
    [
        ("data", "order", "extra"),
        ("data", "items", 0, "body"),
        ("data", "system_messages", 0, "body"),
        ("data", "items", 0, "attachments", 0, "extra"),
        ("data", "capabilities", "extra"),
        ("data", "extra", "nested", 0, "receiver_details"),
        ("data", "extra", "id"),
        ("data", "extra", "created_at"),
        ("request_id",),
    ],
)
def test_receiver_privacy_check_rejects_private_values_anywhere(field: str, path: tuple) -> None:
    payload, metadata = _receiver_privacy_synthetic_case()
    private_value = "Banco de Venezuela" if field == "bank_label" else RECEIVER_DETAILS[field]
    target = payload
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = f"Dato: {private_value}."
    with pytest.raises(AssertionError, match="Receiver data exposed"):
        _assert_receiver_fixture_chat_private(payload, metadata)


@pytest.mark.parametrize("field", ["bank", "phone", "document", "holder"])
def test_receiver_privacy_check_rejects_private_dictionary_keys(field: str) -> None:
    payload, metadata = _receiver_privacy_synthetic_case()
    payload["data"]["extra"][RECEIVER_DETAILS[field]] = None
    with pytest.raises(AssertionError, match="Receiver data exposed"):
        _assert_receiver_fixture_chat_private(payload, metadata)


@pytest.mark.parametrize("field", ["id", "created_at"])
def test_receiver_privacy_check_does_not_exempt_unknown_metadata_paths(field: str) -> None:
    payload, metadata = _receiver_privacy_synthetic_case()
    payload["data"]["extra"][field] = payload["data"]["order"][field]
    with pytest.raises(AssertionError, match="Receiver data exposed"):
        _assert_receiver_fixture_chat_private(payload, metadata)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("id", "20000000-0102-4000-8000-000000000001"),
        ("created_at", "2026-09-22T16:51:36.770102+00:00"),
        ("public_order_code", "NODO-FFFF0102"),
    ],
)
def test_receiver_privacy_check_rejects_metadata_from_another_record(field: str, replacement: str) -> None:
    payload, metadata = _receiver_privacy_synthetic_case()
    payload["data"]["order"][field] = replacement
    with pytest.raises(AssertionError, match="Metadata differs from fixture record"):
        _assert_receiver_fixture_chat_private(payload, metadata)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [("id", "0102"), ("created_at", "0102"), ("created_at", "2026-09-22T16:51:35"), ("public_order_code", "0102")],
)
def test_receiver_privacy_check_rejects_invalid_metadata_even_when_equal(field: str, replacement: str) -> None:
    payload, metadata = _receiver_privacy_synthetic_case()
    path = ("data", "order", field)
    payload["data"]["order"][field] = replacement
    metadata[path] = (metadata[path][0], replacement)
    with pytest.raises(AssertionError):
        _assert_receiver_fixture_chat_private(payload, metadata)


def test_receiver_privacy_check_rejects_missing_verified_metadata() -> None:
    payload, metadata = _receiver_privacy_synthetic_case()
    del payload["data"]["order"]["created_at"]
    with pytest.raises(AssertionError, match="Expected metadata missing"):
        _assert_receiver_fixture_chat_private(payload, metadata)


@pytest.mark.parametrize("field", ["bank", "phone", "document", "holder", "extra"])
def test_receiver_privacy_check_rejects_changed_legacy_mask(field: str) -> None:
    payload, metadata = _receiver_privacy_synthetic_case()
    payload["data"]["order"]["receiver_data_masked"][field] = "unexpected"
    with pytest.raises(AssertionError):
        _assert_receiver_fixture_chat_private(payload, metadata)


def test_receiver_details_never_enter_general_chat_or_message_payloads() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(
        client,
        owner_id=5900,
        remitter_id=5901,
    )
    _confirm_payment(client, owner, order["id"], key="receiver_chat_confirm")
    chat_repository = client.app.state.chat_repository
    order_repository = client.app.state.order_repository
    message_ids_before = set(chat_repository.messages)
    shared = _share_receiver_details(client, remitter, order["id"], key="receiver_chat_share")
    assert shared.status_code == 200, shared.text
    receiver = order_repository.get_receiver_details(order["id"])
    assert receiver is not None
    assert receiver.order_id == order["id"]
    assert receiver.shared_by_user_id == remitter["user"]["id"]
    assert {
        "bank": receiver.bank_code,
        "phone": receiver.phone,
        "document": receiver.document,
        "holder": receiver.holder,
    } == RECEIVER_DETAILS
    assert set(chat_repository.messages) == message_ids_before

    messages = client.get(
        f"/api/v1/orders/{order['id']}/messages?limit=50",
        headers=_bearer(remitter, "receiver_chat_list"),
    )
    assert messages.status_code == 200, messages.text
    assert messages.headers["cache-control"] == "private, no-store"
    payload = messages.json()
    stored_order = order_repository.get_by_id(order["id"])
    metadata = {
        ("data", "order_id"): ("uuid", stored_order.id),
        ("data", "order", "id"): ("uuid", stored_order.id),
        ("data", "order", "public_order_code"): ("public_code", stored_order.public_order_code),
    }
    for field in ("payment_report_deadline_at", "expires_at", "created_at", "delivered_at", "completed_at"):
        timestamp = getattr(stored_order, field)
        metadata[("data", "order", field)] = ("timestamp", timestamp.isoformat() if timestamp else None)

    report = order_repository.get_latest_payment_report_for_order(order["id"])
    assert report is not None
    evidence = order_repository.list_payment_evidence_for_report(report.id)
    assert evidence
    records = [message for message in chat_repository.messages.values() if message.order_id == order["id"]]
    attachments = chat_repository.list_attachments_for_messages([message.id for message in records])
    ordinary = {
        message.id: (
            "uuid",
            message.created_at,
            [(item.id, item.file_asset_id, item.created_at) for item in attachments.get(message.id, [])],
        )
        for message in records
    }
    system = {
        f"system:negotiation-created:{stored_order.id}": ("system_id", stored_order.created_at, []),
        f"system:payment-reported:{report.id}": (
            "system_id", report.created_at, [(file.id, file.id, file.created_at) for file in evidence],
        ),
        f"system:payment-confirmed:{stored_order.id}": ("system_id", stored_order.payment_confirmed_at, []),
        f"system:receiver-details-shared:{receiver.id}": ("system_id", receiver.shared_at, []),
    }
    for collection, expected_records in (("items", ordinary), ("system_messages", system)):
        items = payload["data"][collection]
        assert len(items) == len(expected_records)
        assert {item["id"] for item in items} == set(expected_records)
        for index, item in enumerate(items):
            kind, created_at, expected_attachments = expected_records[item["id"]]
            path = ("data", collection, index)
            metadata[(*path, "id")] = (kind, item["id"])
            metadata[(*path, "order_id")] = ("uuid", stored_order.id)
            metadata[(*path, "created_at")] = ("timestamp", created_at.isoformat())
            attachments_by_id = {identifier: (file_id, timestamp) for identifier, file_id, timestamp in expected_attachments}
            assert len(item["attachments"]) == len(attachments_by_id)
            assert {attachment["id"] for attachment in item["attachments"]} == set(attachments_by_id)
            for attachment_index, attachment in enumerate(item["attachments"]):
                file_id, timestamp = attachments_by_id[attachment["id"]]
                attachment_path = (*path, "attachments", attachment_index)
                metadata[(*attachment_path, "id")] = ("uuid", attachment["id"])
                metadata[(*attachment_path, "file_asset_id")] = ("uuid", file_id)
                metadata[(*attachment_path, "created_at")] = ("timestamp", timestamp.isoformat())

    assert payload["data"]["capabilities"]["receiver_details_shared"] is True
    assert payload["data"]["next_cursor"] is None
    _assert_receiver_fixture_chat_private(payload, metadata)


def test_slice_50b2_frontend_uses_structured_compact_chat_ui_and_copy_controls() -> None:
    root = __import__("pathlib").Path(__file__).resolve().parents[3]
    orders_api = (root / "apps/web/src/api/orders.ts").read_text(encoding="utf-8")
    client_chat = "\n".join(
        (root / path).read_text(encoding="utf-8")
        for path in (
            "apps/web/src/screens/client/ClientOrderChatScreen.tsx",
            "apps/web/src/screens/client/chat/ClientReceiverDetailsBubble.tsx",
        )
    )
    business_chat = "\n".join(
        (root / path).read_text(encoding="utf-8")
        for path in (
            "apps/web/src/screens/business-app/BusinessChatScreen.tsx",
            "apps/web/src/screens/business-app/chat/BusinessChatMessageList.tsx",
            "apps/web/src/screens/business-app/chat/BusinessReceiverDetailsBubble.tsx",
            "apps/web/src/screens/business-app/chat/BusinessChatActionDock.tsx",
            "apps/web/src/screens/business-app/chat/BusinessChatComposer.tsx",
        )
    )

    assert "/receiver-details" in orders_api
    assert "/confirm-received" in orders_api
    assert "shareReceiverDetails" in client_chat
    assert "receiverDetailsForm" in client_chat
    assert "setReceiverDetailsForm" in client_chat
    assert "<summary>Compartir datos Pago Movil</summary>" in client_chat
    assert ">Datos Pago Movil compartidos</span>" in client_chat
    assert "Escribe el numero completo" in client_chat
    assert "0414 1234567" not in client_chat
    assert 'placeholder="12345678"' in client_chat
    assert 'placeholder="V12345678"' not in client_chat
    assert 'placeholder="+584121234567"' not in client_chat
    assert 'type="text"' in client_chat
    assert 'type="tel"' in client_chat
    assert "confirmOrderReceived" in client_chat
    assert "Entrega pendiente" in business_chat
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


def test_slice_47p01_migration_reconciles_local_phone_formats_without_data_loss() -> None:
    root = __import__("pathlib").Path(__file__).resolve().parents[3]
    migration_up = (
        root
        / "database/migrations/0048_receiver_details_phone_constraint_local_formats.up.sql"
    ).read_text(encoding="utf-8")
    migration_down = (
        root
        / "database/migrations/0048_receiver_details_phone_constraint_local_formats.down.sql"
    ).read_text(encoding="utf-8")

    assert "0048 preflight failed" in migration_up
    assert "order_receiver_details_phone_check" in migration_up
    assert "char_length(phone) between 11 and 32" in migration_up
    assert "regexp_replace(phone" in migration_up
    assert "412|414|416|424|426" in migration_up
    assert "not valid" in migration_up
    assert "validate constraint order_receiver_details_phone_check" in migration_up
    assert "0048 rollback preflight failed" in migration_down
    assert "^\\+58[0-9]{10}$" in migration_down
    assert "validate constraint order_receiver_details_phone_check" in migration_down

    combined = f"{migration_up}\n{migration_down}".lower()
    assert "delete from order_receiver_details" not in combined
    assert "update order_receiver_details" not in combined
    assert "drop table" not in combined


def test_receiver_document_optional_prefix_migration_is_reversible_without_data_loss() -> None:
    root = __import__("pathlib").Path(__file__).resolve().parents[3]
    migration_up = (
        root
        / "database/migrations/0049_receiver_details_document_optional_prefix.up.sql"
    ).read_text(encoding="utf-8")
    migration_down = (
        root
        / "database/migrations/0049_receiver_details_document_optional_prefix.down.sql"
    ).read_text(encoding="utf-8")

    assert "0049 preflight failed" in migration_up
    assert "order_receiver_details_document_check" in migration_up
    assert "^([VEJGP])?[0-9]{6,10}$" in migration_up
    assert "not valid" in migration_up
    assert "validate constraint order_receiver_details_document_check" in migration_up
    assert "0049 rollback preflight failed" in migration_down
    assert "^[VEJGP][0-9]{6,10}$" in migration_down
    assert "validate constraint order_receiver_details_document_check" in migration_down

    combined = f"{migration_up}\n{migration_down}".lower()
    assert "delete from order_receiver_details" not in combined
    assert "update order_receiver_details" not in combined
    assert "drop table" not in combined
