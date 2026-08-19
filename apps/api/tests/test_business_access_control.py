from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import replace
from datetime import timedelta
from urllib.parse import urlencode

from fastapi.testclient import TestClient


BOT_TOKEN = "123456:test-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"
VALID_TRON_TEST_WALLET = "TLa2f6VPqDgRE67v" + "1736s7bJ8Ray5wYjU7"


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-14B1",
        "NODO_BUILD_ID": "pytest-business-access-control-build",
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
from app.modules.businesses.access_control import business_access_diagnostic  # noqa: E402
from app.modules.businesses.models import BusinessAccessLinkRecord, BusinessRecord, new_id, utc_now  # noqa: E402
from app.modules.businesses.pin_security import hash_pin  # noqa: E402
from app.modules.businesses.row_mappers import access_link_from_row  # noqa: E402
from app.modules.users.models import UserRecord  # noqa: E402


def test_business_access_diagnostic_covers_each_gate_and_stable_owner_link_selection() -> None:
    now = utc_now()
    owner_id = new_id()
    business = BusinessRecord(
        id=new_id(),
        owner_user_id=owner_id,
        business_name="Casa Diagnostico",
        rif=None,
        address=None,
        phone=None,
        verification_status="approved",
    )
    owner = UserRecord(
        id=owner_id,
        telegram_id=14199,
        username="owner_diagnostic_matrix",
        first_name="Owner",
        last_name=None,
        role="business_owner",
        status="active",
    )
    active_link = BusinessAccessLinkRecord(
        id=new_id(),
        business_id=business.id,
        user_id=owner.id,
        telegram_id_snapshot=owner.telegram_id,
        role_in_business="owner",
        status="active",
        linked_at=now,
        created_at=now,
        updated_at=now,
    )

    cases = [
        (business, owner, [active_link], True, None, "none"),
        (replace(business, verification_status="blocked"), owner, [active_link], False, "BUSINESS_BLOCKED", "unblock_business"),
        (business, replace(owner, status="blocked"), [active_link], False, "USER_BLOCKED", "unblock_owner_user"),
        (business, replace(owner, role="remitter"), [active_link], False, "SURFACE_ACCESS_DENIED", "review_owner_binding"),
        (business, owner, [replace(active_link, status="suspended")], False, "BUSINESS_ACCESS_SUSPENDED", "reactivate_owner_link"),
        (business, owner, [replace(active_link, status="blocked")], False, "BUSINESS_ACCESS_BLOCKED", "reactivate_owner_link"),
        (business, owner, [replace(active_link, status="revoked")], False, "BUSINESS_ACCESS_REVOKED", "reactivate_owner_link"),
        (business, owner, [replace(active_link, role_in_business="operator")], False, "BUSINESS_ACCESS_LINK_REQUIRED", "create_owner_link"),
        (business, owner, [replace(active_link, telegram_id_snapshot=14200)], False, "SURFACE_ACCESS_DENIED", "regenerate_owner_link"),
        (business, owner, [], False, "BUSINESS_ACCESS_LINK_REQUIRED", "create_owner_link"),
    ]

    for case_business, case_owner, links, can_access, reason, action in cases:
        diagnostic = business_access_diagnostic(business=case_business, owner_user=case_owner, links=links)
        assert diagnostic["business_can_access_surface"] is can_access
        assert diagnostic["blocking_reason"] == reason
        assert diagnostic["recommended_admin_action"] == action

    newer_revoked_link = replace(
        active_link,
        id=new_id(),
        status="revoked",
        updated_at=now + timedelta(seconds=1),
    )
    conflict = business_access_diagnostic(
        business=business,
        owner_user=owner,
        links=[newer_revoked_link, active_link],
    )
    assert conflict["owner_link_id"] == active_link.id
    assert conflict["owner_link_conflict"] is True
    assert conflict["business_can_access_surface"] is True

    newer_operator_link = replace(
        active_link,
        id=new_id(),
        role_in_business="operator",
        updated_at=now + timedelta(seconds=2),
    )
    owner_preferred = business_access_diagnostic(
        business=business,
        owner_user=owner,
        links=[newer_operator_link, active_link],
    )
    assert owner_preferred["owner_link_id"] == active_link.id
    assert owner_preferred["owner_link_role"] == "owner"
    assert owner_preferred["owner_link_conflict"] is False
    assert owner_preferred["business_can_access_surface"] is True


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


def _accept_terms(client: TestClient, login: dict, telegram_id: int) -> dict:
    terms = client.post(
        "/api/v1/users/me/terms-acceptance",
        headers={"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": f"req_terms_{telegram_id}"},
        json={"terms_version": "2026-07-06"},
    )
    assert terms.status_code == 200, terms.text
    login["user"] = terms.json()["data"]
    return login


def _login(client: TestClient, telegram_id: int, username: str, *, accept_terms: bool = True) -> dict:
    response = client.post(
        "/api/v1/auth/telegram",
        headers={"X-Request-Id": f"req_login_{telegram_id}"},
        json={"init_data": _signed_init_data(telegram_id, username)},
    )
    assert response.status_code == 200, response.text
    login = response.json()["data"]
    return _accept_terms(client, login, telegram_id) if accept_terms else login


def _headers(login: dict, key: str = "idem") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {login['access_token']}",
        "X-Request-Id": f"req_{key}",
        "Idempotency-Key": key,
    }


def _bearer(login: dict, key: str = "req") -> dict[str, str]:
    return {"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": key}


def _business_headers(login: dict, key: str = "req") -> dict[str, str]:
    return {**_bearer(login, key), "X-NODO-Surface": "business_mini_app"}


def _create_approved_business(client: TestClient, owner: dict) -> dict:
    response = client.post(
        "/api/v1/businesses",
        headers={
            **_headers(owner, f"create_{owner['user']['id']}"),
            "Content-Type": "application/json",
            "X-NODO-Test-Fixture": "business_create",
        },
        json={"business_name": "Casa Link", "rif": "J-12345678-9", "address": "Av Principal", "phone": "+584121234567", "country": "VE"},
    )
    assert response.status_code == 201, response.text
    business = response.json()["data"]["business"]
    stored = client.app.state.business_repository.get_business(business["id"])
    stored.verification_status = "approved"
    stored.approved_at = stored.updated_at
    return business


def _admin_login(client: TestClient, telegram_id: int = 14001) -> dict:
    admin = _login(client, telegram_id, "admin")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    return admin


def _link_business_without_pin(client: TestClient, admin: dict, business: dict, owner: dict, key: str = "link") -> dict:
    response = client.post(
        f"/api/v1/admin/businesses/{business['id']}/access-links",
        headers={**_headers(admin, key), "Content-Type": "application/json"},
        json={"user_id": owner["user"]["id"], "role_in_business": "owner", "reason": "admin approved owner access"},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["access_link"]


def _link_business(client: TestClient, admin: dict, business: dict, owner: dict, key: str = "link") -> dict:
    link = _link_business_without_pin(client, admin, business, owner, key)
    client.app.state.business_repository.set_access_link_pin_hash(link_id=link["id"], pin_hash=hash_pin("1234"))
    client.app.state.business_repository.mark_access_link_pin_verified(link_id=link["id"], unlocked_until=utc_now() + timedelta(minutes=15))
    return link


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def test_access_link_mapper_coerces_pin_timestamp_strings() -> None:
    unlocked_until = (utc_now() + timedelta(minutes=10)).isoformat()
    locked_until = (utc_now() + timedelta(minutes=20)).isoformat()

    link = access_link_from_row(
        {
            "id": "link-1",
            "business_id": "business-1",
            "user_id": "user-1",
            "telegram_id_snapshot": 12345,
            "role_in_business": "owner",
            "status": "active",
            "linked_by_admin_id": None,
            "linked_at": utc_now(),
            "suspended_at": None,
            "blocked_at": None,
            "revoked_at": None,
            "reason": None,
            "business_pin_hash": "hash",
            "business_pin_set_at": unlocked_until,
            "business_pin_verified_at": unlocked_until,
            "business_pin_unlocked_until": unlocked_until,
            "business_pin_failed_attempts": 0,
            "business_pin_locked_until": locked_until,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
    )

    assert link.business_pin_set_at is not None
    assert link.business_pin_verified_at is not None
    assert link.business_pin_unlocked_until is not None
    assert link.business_pin_locked_until is not None
    assert link.business_pin_unlocked_until > utc_now()


def test_surface_session_allows_approved_business_with_active_link() -> None:
    client = _client()
    owner = _login(client, 14101, "owner")
    business = _create_approved_business(client, owner)
    admin = _admin_login(client)
    _link_business(client, admin, business, owner)

    response = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_surface_allowed"))

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["allowed"] is True
    assert data["surface"] == "business_mini_app"
    assert data["access_state"] == "allowed"
    assert data["business"]["id"] == business["id"]
    assert "risk_level" not in data["business"]
    assert "trust_level" not in data["business"]
    assert "telegram_id" not in data["user"]
    assert "business.ads.create" in data["capabilities"]


def test_surface_session_denies_active_operator_link_without_owner_link() -> None:
    client = _client()
    owner = _login(client, 14104, "operator_only")
    business = _create_approved_business(client, owner)
    admin = _admin_login(client, 14105)
    client.app.state.business_repository.create_access_link(
        business_id=business["id"],
        user_id=owner["user"]["id"],
        telegram_id_snapshot=14104,
        role_in_business="operator",
        linked_by_admin_id=admin["user"]["id"],
        reason="operator access does not authorize the owner surface",
    )

    response = client.get(
        "/api/v1/surface/session",
        headers=_business_headers(owner, "req_surface_operator_only"),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "BUSINESS_ACCESS_LINK_REQUIRED"


def test_surface_session_prefers_owner_link_when_operator_is_also_active() -> None:
    client = _client()
    owner = _login(client, 14108, "operator_and_owner")
    business = _create_approved_business(client, owner)
    admin = _admin_login(client, 14109)
    operator_link = client.app.state.business_repository.create_access_link(
        business_id=business["id"],
        user_id=owner["user"]["id"],
        telegram_id_snapshot=14108,
        role_in_business="operator",
        linked_by_admin_id=admin["user"]["id"],
        reason="operator role reserved for future use",
    )
    owner_link = client.app.state.business_repository.create_access_link(
        business_id=business["id"],
        user_id=owner["user"]["id"],
        telegram_id_snapshot=14108,
        role_in_business="owner",
        linked_by_admin_id=admin["user"]["id"],
        reason="owner access approved",
    )

    response = client.get(
        "/api/v1/surface/session",
        headers=_business_headers(owner, "req_surface_operator_and_owner"),
    )

    assert owner_link.id != operator_link.id
    assert response.status_code == 200, response.text
    assert response.json()["data"]["business"]["access_link"]["id"] == owner_link.id
    assert response.json()["data"]["business"]["access_link"]["role_in_business"] == "owner"


def test_surface_session_uses_approved_business_with_active_link_when_owner_has_duplicate_business_records() -> None:
    client = _client()
    owner = _login(client, 14106, "owner_duplicate_businesses")
    admin = _admin_login(client, 14107)
    owner_id = owner["user"]["id"]
    client.app.state.user_repository.set_user_role(owner_id, "business_owner")

    unlinked_business = BusinessRecord(
        id=new_id(),
        owner_user_id=owner_id,
        business_name="Ficha sin acceso",
        rif="J-00000000-1",
        address=None,
        phone=None,
        verification_status="pending",
    )
    linked_business = BusinessRecord(
        id=new_id(),
        owner_user_id=owner_id,
        business_name="Ficha con acceso",
        rif="J-00000000-2",
        address=None,
        phone=None,
        verification_status="approved",
        approved_at=utc_now(),
    )
    client.app.state.business_repository.businesses[unlinked_business.id] = unlinked_business
    client.app.state.business_repository.businesses[linked_business.id] = linked_business
    client.app.state.business_repository.create_access_link(
        business_id=linked_business.id,
        user_id=owner_id,
        telegram_id_snapshot=14106,
        role_in_business="owner",
        linked_by_admin_id=admin["user"]["id"],
        reason="admin approved owner access",
    )

    response = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_surface_duplicate_businesses"))

    assert response.status_code == 200, response.text
    assert response.json()["data"]["business"]["id"] == linked_business.id


def test_business_availability_requires_pin_and_idempotency() -> None:
    client = _client()
    admin = _admin_login(client, 14120)
    owner_without_pin = _login(client, 14121, "owner_availability_no_pin")
    business_without_pin = _create_approved_business(client, owner_without_pin)
    link_response = client.post(
        f"/api/v1/admin/businesses/{business_without_pin['id']}/access-links",
        headers={**_headers(admin, "link_availability_no_pin"), "Content-Type": "application/json"},
        json={"user_id": owner_without_pin["user"]["id"], "role_in_business": "owner", "reason": "admin approved owner access"},
    )
    assert link_response.status_code == 201, link_response.text

    locked = client.patch(
        "/api/v1/business/availability",
        headers={**_headers(owner_without_pin, "availability_without_pin"), "Content-Type": "application/json"},
        json={"accepting_orders": False},
    )
    assert locked.status_code == 423
    assert locked.json()["error"]["code"] == "BUSINESS_PIN_NOT_SET"

    owner = _login(client, 14122, "owner_availability")
    business = _create_approved_business(client, owner)
    _link_business(client, admin, business, owner, key="link_availability")

    missing_idempotency = client.patch(
        "/api/v1/business/availability",
        headers={**_bearer(owner, "availability_missing_idempotency"), "Content-Type": "application/json"},
        json={"accepting_orders": False},
    )
    assert missing_idempotency.status_code == 400
    assert missing_idempotency.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    headers = {**_headers(owner, "availability_offline_once"), "Content-Type": "application/json"}
    updated = client.patch("/api/v1/business/availability", headers=headers, json={"accepting_orders": False})
    replay = client.patch("/api/v1/business/availability", headers=headers, json={"accepting_orders": False})

    assert updated.status_code == 200, updated.text
    assert replay.status_code == 200, replay.text
    assert updated.json()["data"]["business"]["is_accepting_orders"] is False
    assert replay.json()["data"]["business"]["is_accepting_orders"] is False
    assert client.app.state.business_repository.get_business(business["id"]).is_accepting_orders is False


def test_business_payment_methods_require_idempotency_key() -> None:
    client = _client()
    owner = _login(client, 14123, "owner_zelle_idempotency")
    business = _create_approved_business(client, owner)
    admin = _admin_login(client, 14124)
    _link_business(client, admin, business, owner, key="link_zelle_idempotency")
    payment = client.app.state.business_repository.add_payment_method(
        business_id=business["id"],
        method_type="zelle",
        network=None,
        account_value="owner-zelle@example.com",
        account_masked="***.com",
        holder_name="Owner Zelle",
    )
    payment.verified_status = "approved"
    payment.active = True

    create_without_key = client.post(
        "/api/v1/business/payment-methods",
        headers={**_bearer(owner, "zelle_create_without_key"), "Content-Type": "application/json"},
        json={"zelle_account": "new-zelle@example.com", "holder_name": "New Zelle"},
    )
    update_without_key = client.patch(
        f"/api/v1/business/payment-methods/{payment.id}",
        headers={**_bearer(owner, "zelle_update_without_key"), "Content-Type": "application/json"},
        json={"holder_name": "Updated Holder"},
    )
    delete_without_key = client.delete(
        f"/api/v1/business/payment-methods/{payment.id}",
        headers=_bearer(owner, "zelle_delete_without_key"),
    )

    for response in (create_without_key, update_without_key, delete_without_key):
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_business_owner_must_accept_terms_before_sensitive_preparation_actions() -> None:
    client = _client()
    owner = _login(client, 14127, "owner_terms_gate", accept_terms=False)
    business = _create_approved_business(client, owner)
    admin = _admin_login(client, 14128)
    _link_business(client, admin, business, owner, key="link_terms_gate")

    blocked = client.post(
        "/api/v1/business/payment-methods",
        headers={**_headers(owner, "terms_gate_zelle"), "Content-Type": "application/json"},
        json={"zelle_account": "owner-terms@example.com", "holder_name": "Owner Terms"},
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "TERMS_ACCEPTANCE_REQUIRED"

    _accept_terms(client, owner, 14127)
    allowed = client.post(
        "/api/v1/business/payment-methods",
        headers={**_headers(owner, "terms_gate_zelle_after_accept"), "Content-Type": "application/json"},
        json={"zelle_account": "owner-terms@example.com", "holder_name": "Owner Terms"},
    )
    assert allowed.status_code == 201, allowed.text
    assert allowed.json()["data"]["payment_method"]["holder_name"] == "Owner Terms"


def test_business_can_self_manage_usdt_method_and_publish_ad() -> None:
    client = _client()
    owner = _login(client, 14125, "owner_usdt_method")
    business = _create_approved_business(client, owner)
    admin = _admin_login(client, 14126)
    _link_business(client, admin, business, owner, key="link_usdt_method")
    client.app.state.ad_repository.grant_test_credits(business_id=business["id"], amount=2, created_by=owner["user"]["id"])

    invalid_wallet = "abc"
    invalid = client.post(
        "/api/v1/business/payment-methods",
        headers={**_headers(owner, "create_invalid_usdt_method"), "Content-Type": "application/json"},
        json={"method_type": "usdt_trc20", "account_value": invalid_wallet, "holder_name": "Wallet USDT Invalid"},
    )
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "PAYMENT_METHOD_INVALID"

    ethereum_wallet = "0x" + ("a" * 40)
    evm_created = client.post(
        "/api/v1/business/payment-methods",
        headers={**_headers(owner, "create_evm_usdt_wallet"), "Content-Type": "application/json"},
        json={"method_type": "usdt_trc20", "account_value": ethereum_wallet, "holder_name": "Wallet Ethereum"},
    )
    assert evm_created.status_code == 201, evm_created.text
    evm_method = evm_created.json()["data"]["payment_method"]
    assert evm_method["receive_method"] == "usdt_trc20"
    assert evm_method["receive_display"] == "USDT"
    assert evm_method["network"] is None
    assert evm_method["masked_account"].endswith("aaaa")

    wallet = VALID_TRON_TEST_WALLET
    created = client.post(
        "/api/v1/business/payment-methods",
        headers={**_headers(owner, "create_usdt_wallet_method"), "Content-Type": "application/json"},
        json={"method_type": "usdt_trc20", "account_value": wallet, "holder_name": "Wallet USDT Principal"},
    )
    assert created.status_code == 201, created.text
    method = created.json()["data"]["payment_method"]
    assert method["receive_method"] == "usdt_trc20"
    assert method["receive_display"] == "USDT"
    assert method["network"] is None
    assert method["masked_account"].endswith("YjU7")
    assert wallet not in created.text

    listed = client.get("/api/v1/business/payment-methods", headers=_bearer(owner, "list_usdt_methods"))
    assert listed.status_code == 200, listed.text
    assert any(item["id"] == method["id"] and item["receive_method"] == "usdt_trc20" for item in listed.json()["data"])

    ad = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "create_usdt_ad"), "Content-Type": "application/json"},
        json={
            "payment_method_id": method["id"],
            "payment_method": "usdt_trc20",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "20.00",
            "amount_max_usd": "100.00",
        },
    )
    assert ad.status_code == 201, ad.text
    assert ad.json()["data"]["ad"]["payment_method"] == "usdt_trc20"


def test_usdt_method_creation_retries_after_first_pin_setup() -> None:
    client = _client()
    owner = _login(client, 14129, "owner_usdt_pin_setup")
    business = _create_approved_business(client, owner)
    admin = _admin_login(client, 14130)
    _link_business_without_pin(client, admin, business, owner, key="link_usdt_pin_setup")
    payload = {
        "method_type": "usdt_trc20",
        "account_value": VALID_TRON_TEST_WALLET,
        "holder_name": "Wallet USDT Principal",
    }
    headers = {**_headers(owner, "create_usdt_after_pin_setup"), "Content-Type": "application/json"}

    blocked = client.post("/api/v1/business/payment-methods", headers=headers, json=payload)
    assert blocked.status_code == 423
    assert blocked.json()["error"]["code"] == "BUSINESS_PIN_NOT_SET"

    setup = client.post(
        "/api/v1/business/security/pin/setup",
        headers={**_bearer(owner, "setup_usdt_pin"), "Content-Type": "application/json"},
        json={"pin": "1234"},
    )
    assert setup.status_code == 200, setup.text

    created = client.post("/api/v1/business/payment-methods", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["data"]["payment_method"]["receive_method"] == "usdt_trc20"


def test_usdt_method_creation_retries_after_pin_unlock() -> None:
    client = _client()
    owner = _login(client, 14131, "owner_usdt_pin_unlock")
    business = _create_approved_business(client, owner)
    admin = _admin_login(client, 14132)
    _link_business(client, admin, business, owner, key="link_usdt_pin_unlock")
    locked = client.post("/api/v1/business/security/pin/lock", headers=_bearer(owner, "lock_usdt_pin"))
    assert locked.status_code == 200, locked.text
    payload = {
        "method_type": "usdt_trc20",
        "account_value": VALID_TRON_TEST_WALLET,
        "holder_name": "Wallet USDT Principal",
    }
    headers = {**_headers(owner, "create_usdt_after_pin_unlock"), "Content-Type": "application/json"}

    blocked = client.post("/api/v1/business/payment-methods", headers=headers, json=payload)
    assert blocked.status_code == 423
    assert blocked.json()["error"]["code"] == "BUSINESS_PIN_REQUIRED"

    unlocked = client.post(
        "/api/v1/business/security/pin/verify",
        headers={**_bearer(owner, "unlock_usdt_pin"), "Content-Type": "application/json"},
        json={"pin": "1234"},
    )
    assert unlocked.status_code == 200, unlocked.text

    created = client.post("/api/v1/business/payment-methods", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["data"]["payment_method"]["receive_method"] == "usdt_trc20"


def test_business_pin_is_required_for_sensitive_business_mutations() -> None:
    client = _client()
    owner = _login(client, 14102, "owner_pin")
    business = _create_approved_business(client, owner)
    admin = _admin_login(client, 14103)
    link_response = client.post(
        f"/api/v1/admin/businesses/{business['id']}/access-links",
        headers={**_headers(admin, "link_pin"), "Content-Type": "application/json"},
        json={"user_id": owner["user"]["id"], "role_in_business": "owner", "reason": "admin approved owner access"},
    )
    assert link_response.status_code == 201, link_response.text
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
    client.app.state.ad_repository.grant_test_credits(business_id=business["id"], amount=2, created_by=owner["user"]["id"])

    session = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_surface_pin"))
    assert session.status_code == 200
    access_link = session.json()["data"]["business"]["access_link"]
    assert access_link["pin_required"] is True
    assert access_link["pin_configured"] is False
    assert access_link["pin_unlocked"] is False

    blocked = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "pin_missing_ad"), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment.id,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "20.00",
            "amount_max_usd": "100.00",
        },
    )
    assert blocked.status_code == 423
    assert blocked.json()["error"]["code"] == "BUSINESS_PIN_NOT_SET"
    assert blocked.json()["error"]["message"] == "Crea tu PIN para proteger esta accion."

    setup = client.post(
        "/api/v1/business/security/pin/setup",
        headers={**_bearer(owner, "req_pin_setup"), "Content-Type": "application/json"},
        json={"pin": "1234"},
    )
    assert setup.status_code == 200, setup.text
    assert setup.json()["data"]["pin"]["configured"] is True
    assert setup.json()["data"]["pin"]["unlocked"] is True
    assert "1234" not in setup.text

    allowed = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "pin_allowed_ad"), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment.id,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "20.00",
            "amount_max_usd": "100.00",
        },
    )
    assert allowed.status_code == 201, allowed.text

    locked = client.post("/api/v1/business/security/pin/lock", headers=_bearer(owner, "req_pin_lock"))
    assert locked.status_code == 200
    blocked_after_lock = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "pin_locked_ad"), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment.id,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "101.00",
            "amount_max_usd": "500.00",
        },
    )
    assert blocked_after_lock.status_code == 423
    assert blocked_after_lock.json()["error"]["code"] == "BUSINESS_PIN_REQUIRED"
    assert blocked_after_lock.json()["error"]["message"] == "Desbloquea tu PIN para completar esta accion."

    bad_pin = client.post(
        "/api/v1/business/security/pin/verify",
        headers={**_bearer(owner, "req_bad_pin"), "Content-Type": "application/json"},
        json={"pin": "9999"},
    )
    assert bad_pin.status_code == 403
    assert bad_pin.json()["error"]["code"] == "BUSINESS_PIN_INVALID"
    assert bad_pin.json()["error"]["message"] == "PIN incorrecto."
    ok_pin = client.post(
        "/api/v1/business/security/pin/verify",
        headers={**_bearer(owner, "req_ok_pin"), "Content-Type": "application/json"},
        json={"pin": "1234"},
    )
    assert ok_pin.status_code == 200
    assert ok_pin.json()["data"]["pin"]["unlocked"] is True
    assert "1234" not in ok_pin.text
    for event in client.app.state.audit_writer.events:
        metadata_text = json.dumps(event.metadata_json or {}, default=str)
        assert "1234" not in metadata_text
        assert "9999" not in metadata_text


def test_surface_session_denies_remitter_and_business_owner_without_link() -> None:
    client = _client()
    remitter = _login(client, 14111, "remitter")
    denied_remitter = client.get("/api/v1/surface/session", headers=_business_headers(remitter, "req_surface_remitter"))
    assert denied_remitter.status_code == 403
    assert denied_remitter.json()["error"]["code"] == "SURFACE_ACCESS_DENIED"

    owner = _login(client, 14112, "owner_without_link")
    _create_approved_business(client, owner)
    denied_owner = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_surface_no_link"))
    assert denied_owner.status_code == 403
    assert denied_owner.json()["error"]["code"] == "BUSINESS_ACCESS_LINK_REQUIRED"
    assert "surface_access_denied" in _event_types(client)


def test_surface_session_denies_link_statuses_and_business_user_statuses() -> None:
    client = _client()
    admin = _admin_login(client)
    for status, expected_code in [
        ("suspended", "BUSINESS_ACCESS_SUSPENDED"),
        ("revoked", "BUSINESS_ACCESS_REVOKED"),
        ("blocked", "BUSINESS_ACCESS_BLOCKED"),
    ]:
        owner = _login(client, 14200 + len(_event_types(client)), f"owner_{status}")
        business = _create_approved_business(client, owner)
        link = _link_business(client, admin, business, owner, key=f"link_{status}")
        client.app.state.business_repository.set_access_link_status(
            link=client.app.state.business_repository.get_access_link(link["id"]),
            status=status,
            reason=f"test {status}",
        )
        response = client.get("/api/v1/surface/session", headers=_business_headers(owner, f"req_surface_{status}"))
        assert response.status_code == 403
        assert response.json()["error"]["code"] == expected_code

    user_blocked = _login(client, 14220, "blocked_user")
    blocked_business = _create_approved_business(client, user_blocked)
    _link_business(client, admin, blocked_business, user_blocked, key="link_user_blocked")
    client.app.state.user_repository.set_user_status(user_blocked["user"]["id"], "blocked")
    response = client.get("/api/v1/surface/session", headers=_business_headers(user_blocked, "req_blocked_user"))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "USER_BLOCKED"

    suspended_business_owner = _login(client, 14221, "suspended_business")
    business = _create_approved_business(client, suspended_business_owner)
    _link_business(client, admin, business, suspended_business_owner, key="link_business_suspended")
    stored_business = client.app.state.business_repository.get_business(business["id"])
    stored_business.verification_status = "suspended"
    business_response = client.get("/api/v1/surface/session", headers=_business_headers(suspended_business_owner, "req_business_suspended"))
    assert business_response.status_code == 403
    assert business_response.json()["error"]["code"] == "BUSINESS_SUSPENDED"

    blocked_business_owner = _login(client, 14222, "blocked_business")
    blocked_business = _create_approved_business(client, blocked_business_owner)
    _link_business(client, admin, blocked_business, blocked_business_owner, key="link_business_blocked")
    stored_blocked_business = client.app.state.business_repository.get_business(blocked_business["id"])
    stored_blocked_business.verification_status = "blocked"
    blocked_business_response = client.get("/api/v1/surface/session", headers=_business_headers(blocked_business_owner, "req_business_blocked"))
    assert blocked_business_response.status_code == 403
    assert blocked_business_response.json()["error"]["code"] == "BUSINESS_BLOCKED"


def test_admin_access_link_lifecycle_requires_reason_idempotency_and_blocks_support() -> None:
    client = _client()
    owner = _login(client, 14301, "owner_lifecycle")
    business = _create_approved_business(client, owner)
    admin = _admin_login(client)
    support = _login(client, 14303, "support")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")

    no_idem = client.post(
        f"/api/v1/admin/businesses/{business['id']}/access-links",
        headers={**_bearer(admin, "req_no_idem"), "Content-Type": "application/json"},
        json={"user_id": owner["user"]["id"], "reason": "missing idempotency"},
    )
    assert no_idem.status_code == 400
    assert no_idem.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    support_attempt = client.post(
        f"/api/v1/admin/businesses/{business['id']}/access-links",
        headers={**_headers(support, "support_link"), "Content-Type": "application/json"},
        json={"user_id": owner["user"]["id"], "reason": "support cannot mutate"},
    )
    assert support_attempt.status_code == 403

    different_user = _login(client, 14304, "different_owner")
    wrong_owner_attempt = client.post(
        f"/api/v1/admin/businesses/{business['id']}/access-links",
        headers={**_headers(admin, "wrong_owner_link"), "Content-Type": "application/json"},
        json={"user_id": different_user["user"]["id"], "role_in_business": "owner", "reason": "cannot link a different owner"},
    )
    assert wrong_owner_attempt.status_code == 422
    assert wrong_owner_attempt.json()["error"]["code"] == "VALIDATION_ERROR"

    link = _link_business(client, admin, business, owner, key="link_lifecycle")
    replay = client.post(
        f"/api/v1/admin/businesses/{business['id']}/access-links",
        headers={**_headers(admin, "link_lifecycle"), "Content-Type": "application/json"},
        json={"user_id": owner["user"]["id"], "role_in_business": "owner", "reason": "admin approved owner access"},
    )
    assert replay.status_code in {200, 201}
    assert replay.json()["data"]["access_link"]["id"] == link["id"]

    for action, expected_status in [
        ("suspend", "suspended"),
        ("reactivate", "active"),
        ("revoke", "revoked"),
        ("block", "blocked"),
    ]:
        response = client.post(
            f"/api/v1/admin/businesses/{business['id']}/access-links/{link['id']}/{action}",
            headers={**_headers(admin, f"{action}_link"), "Content-Type": "application/json"},
            json={"reason": f"{action} access"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["data"]["access_link"]["status"] == expected_status

    assert {"business_access_linked", "business_access_suspended", "business_access_reactivated", "business_access_unlinked", "business_access_blocked"}.issubset(set(_event_types(client)))


def test_business_operations_fail_without_active_link_and_pass_with_link() -> None:
    client = _client()
    owner = _login(client, 14401, "owner_ops")
    business = _create_approved_business(client, owner)
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
    client.app.state.ad_repository.grant_test_credits(business_id=business["id"], amount=2, created_by=owner["user"]["id"])

    blocked = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "ad_without_link"), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment.id,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "20.00",
            "amount_max_usd": "100.00",
        },
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "BUSINESS_ACCESS_LINK_REQUIRED"

    admin = _admin_login(client)
    _link_business(client, admin, business, owner)
    allowed = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "ad_with_link"), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment.id,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "20.00",
            "amount_max_usd": "100.00",
        },
    )
    assert allowed.status_code == 201, allowed.text
