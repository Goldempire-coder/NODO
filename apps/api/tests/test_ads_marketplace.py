from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import timedelta
from urllib.parse import urlencode

from fastapi.testclient import TestClient


BOT_TOKEN = "123456:test-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-03",
        "NODO_BUILD_ID": "pytest-ads-build",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
        "BOT_TOKEN": BOT_TOKEN,
        "JWT_SECRET": JWT_SECRET,
        "JWT_REFRESH_SECRET": JWT_REFRESH_SECRET,
        "AUTH_INIT_DATA_MAX_AGE_SECONDS": "86400",
        "ACCESS_TOKEN_TTL_SECONDS": "900",
        "REFRESH_TOKEN_TTL_SECONDS": "2592000",
        "MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS": "300",
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


def _client(**env_overrides: str) -> TestClient:
    _set_env(**env_overrides)
    return TestClient(create_app())


def _signed_init_data(telegram_id: int = 101, username: str = "user") -> str:
    payload = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": telegram_id, "username": username, "first_name": username}, separators=(",", ":"), sort_keys=True),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


def _login(client: TestClient, telegram_id: int = 101, username: str = "user") -> dict:
    response = client.post(
        "/api/v1/auth/telegram",
        headers={"X-Request-Id": f"req_login_{telegram_id}"},
        json={"init_data": _signed_init_data(telegram_id=telegram_id, username=username)},
    )
    assert response.status_code == 200
    return response.json()["data"]


def _headers(login: dict, key: str = "idem") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {login['access_token']}",
        "X-Request-Id": f"req_{key}",
        "Idempotency-Key": key,
    }


def _bearer(login: dict, key: str = "req") -> dict[str, str]:
    return {"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": key}


def _access_token(user_id: str, *, role: str = "remitter", status: str = "active", issued_at: int | None = None) -> str:
    now = issued_at or int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "role": role,
        "status": status,
        "iat": now,
        "exp": int(time.time()) + 900,
        "jti": f"test-jti-{user_id}",
    }

    def b64(raw: bytes) -> str:
        import base64

        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    signing_input = ".".join(
        [
            b64(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")),
            b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")),
        ]
    )
    signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{b64(signature)}"


def _create_business(client: TestClient, login: dict, key: str = "create") -> dict:
    response = client.post(
        "/api/v1/businesses",
        headers={**_headers(login, key), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": f"Casa {key}", "rif": "J-12345678-9", "address": "Av Principal", "phone": "+584121234567", "country": "VE"},
    )
    assert response.status_code == 201
    return response.json()["data"]["business"]


def _approved_business_with_method(client: TestClient, login: dict, *, credits: int = 5, approved: bool = True) -> tuple[dict, str]:
    business = _create_business(client, login, f"biz_{login['user']['id']}")
    stored_business = client.app.state.business_repository.get_business(business["id"])
    if approved:
        stored_business.verification_status = "approved"
        stored_business.approved_at = stored_business.updated_at
        stored_business.max_order_amount_usd = stored_business.max_order_amount_usd * 20
        stored_user = client.app.state.user_repository.get_user_by_id(login["user"]["id"])
        client.app.state.business_repository.create_access_link(
            business_id=business["id"],
            user_id=login["user"]["id"],
            telegram_id_snapshot=stored_user.telegram_id,
            role_in_business="owner",
            linked_by_admin_id=login["user"]["id"],
            reason="test_active_business_access",
        )
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


def _create_ad(client: TestClient, login: dict, payment_method_id: str, *, key: str = "ad", amount_min: str = "20.00", amount_max: str = "100.00") -> dict:
    response = client.post(
        "/api/v1/business/ads",
        headers={**_headers(login, key), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment_method_id,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": amount_min,
            "amount_max_usd": amount_max,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["ad"]


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def test_create_ad_requires_approved_business_owner_and_valid_payment_method() -> None:
    client = _client()
    owner = _login(client, 701, "owner")
    _, method_id = _approved_business_with_method(client, owner, approved=False)

    not_approved = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "not_approved"), "Content-Type": "application/json"},
        json={"payment_method_id": method_id, "payment_method": "zelle", "delivery_method": "pago_movil_ve", "rate_bs_per_usd": "39.5", "amount_min_usd": "20.00", "amount_max_usd": "100.00"},
    )
    assert not_approved.status_code == 409
    assert not_approved.json()["error"]["code"] == "BUSINESS_NOT_APPROVED"

    other = _login(client, 702, "other")
    client.app.state.user_repository.set_user_role(other["user"]["id"], "business_owner")
    forbidden = client.post(
        "/api/v1/business/ads",
        headers={**_headers(other, "other_ad"), "Content-Type": "application/json"},
        json={"payment_method_id": method_id, "payment_method": "zelle", "delivery_method": "pago_movil_ve", "rate_bs_per_usd": "39.5", "amount_min_usd": "20.00", "amount_max_usd": "100.00"},
    )
    assert forbidden.status_code in {403, 404}


def test_credit_cost_ranges_hold_and_insufficient_balance() -> None:
    client = _client()
    owner = _login(client, 711, "owner")
    business, method_id = _approved_business_with_method(client, owner, credits=6)

    ad_one = _create_ad(client, owner, method_id, key="ad_one", amount_min="20.00", amount_max="100.00")
    ad_two = _create_ad(client, owner, method_id, key="ad_two", amount_min="101.00", amount_max="500.00")
    ad_three = _create_ad(client, owner, method_id, key="ad_three", amount_min="501.00", amount_max="2000.00")
    assert [ad_one["required_credits"], ad_two["required_credits"], ad_three["required_credits"]] == [1, 2, 3]
    wallet = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet.available_credits == 0
    assert wallet.blocked_credits == 6
    assert "credits_held" in _event_types(client)

    blocked = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "over_2000"), "Content-Type": "application/json"},
        json={"payment_method_id": method_id, "payment_method": "zelle", "delivery_method": "pago_movil_ve", "rate_bs_per_usd": "39.5", "amount_min_usd": "20.00", "amount_max_usd": "2000.01"},
    )
    assert blocked.status_code == 400
    assert blocked.json()["error"]["code"] == "AD_AMOUNT_TOO_HIGH"

    no_credits_owner = _login(client, 712, "no_credits")
    _, no_credit_method = _approved_business_with_method(client, no_credits_owner, credits=0)
    insufficient = client.post(
        "/api/v1/business/ads",
        headers={**_headers(no_credits_owner, "no_credits_ad"), "Content-Type": "application/json"},
        json={"payment_method_id": no_credit_method, "payment_method": "zelle", "delivery_method": "pago_movil_ve", "rate_bs_per_usd": "39.5", "amount_min_usd": "20.00", "amount_max_usd": "100.00"},
    )
    assert insufficient.status_code == 409
    assert insufficient.json()["error"]["code"] == "CREDIT_BALANCE_INSUFFICIENT"


def test_payment_method_must_belong_to_business_be_approved_and_active() -> None:
    client = _client()
    owner = _login(client, 721, "owner")
    other = _login(client, 722, "other")
    _, method_id = _approved_business_with_method(client, owner, credits=5)
    _, other_method = _approved_business_with_method(client, other, credits=5)
    payment = client.app.state.business_repository.get_payment_method(method_id)
    payment.active = False

    inactive = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "inactive_method"), "Content-Type": "application/json"},
        json={"payment_method_id": method_id, "payment_method": "zelle", "delivery_method": "pago_movil_ve", "rate_bs_per_usd": "39.5", "amount_min_usd": "20.00", "amount_max_usd": "100.00"},
    )
    assert inactive.status_code == 400
    assert inactive.json()["error"]["code"] == "PAYMENT_METHOD_NOT_APPROVED"

    wrong_owner = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "wrong_method"), "Content-Type": "application/json"},
        json={"payment_method_id": other_method, "payment_method": "zelle", "delivery_method": "pago_movil_ve", "rate_bs_per_usd": "39.5", "amount_min_usd": "20.00", "amount_max_usd": "100.00"},
    )
    assert wrong_owner.status_code == 400
    assert wrong_owner.json()["error"]["code"] == "PAYMENT_METHOD_NOT_APPROVED"


def test_business_payment_methods_endpoint_returns_only_safe_approved_own_methods() -> None:
    client = _client()
    owner = _login(client, 723, "method_owner")
    business, method_id = _approved_business_with_method(client, owner, credits=0)
    stored = client.app.state.business_repository.get_payment_method(method_id)
    stored.account_value = "full-sensitive@example.com"
    stored.account_masked = "***.com"

    pending = client.app.state.business_repository.add_payment_method(
        business_id=business["id"],
        method_type="usdt_trc20",
        network="trc20",
        account_value="TFullSensitiveWallet",
        account_masked="TFull...llet",
        holder_name="Owner Test",
    )
    pending.verified_status = "pending"
    pending.active = True

    other = _login(client, 724, "other_method_owner")
    _, other_method_id = _approved_business_with_method(client, other, credits=0)
    other_method = client.app.state.business_repository.get_payment_method(other_method_id)
    other_method.account_value = "other-sensitive@example.com"

    response = client.get("/api/v1/business/payment-methods", headers=_bearer(owner, "req_methods"))
    assert response.status_code == 200
    payload = response.json()["data"]
    assert len(payload) == 1
    assert payload[0]["id"] == method_id
    assert payload[0]["label"] == "Recibo Zelle → Entrego Pago Móvil Bs."
    assert payload[0]["receive_display"] == "Zelle"
    assert payload[0]["delivery_display"] == "Pago Móvil"
    assert payload[0]["delivery_currency"] == "Bs."
    assert payload[0]["masked_account"] == "***.com"
    assert "account_value" not in response.text
    assert "storage_path" not in response.text
    assert "full-sensitive@example.com" not in response.text
    assert "TFullSensitiveWallet" not in response.text
    assert "other-sensitive@example.com" not in response.text


def test_business_payment_methods_endpoint_blocks_unapproved_business() -> None:
    client = _client()
    owner = _login(client, 725, "unapproved_methods")
    _approved_business_with_method(client, owner, credits=0, approved=False)

    response = client.get("/api/v1/business/payment-methods", headers=_bearer(owner, "req_methods_unapproved"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BUSINESS_NOT_APPROVED"


def test_overlapping_active_range_blocks_and_idempotency_replays_create() -> None:
    client = _client()
    owner = _login(client, 731, "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=5)

    first = _create_ad(client, owner, method_id, key="same_ad")
    replay = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "same_ad"), "Content-Type": "application/json"},
        json={"payment_method_id": method_id, "payment_method": "zelle", "delivery_method": "pago_movil_ve", "rate_bs_per_usd": "39.5000", "amount_min_usd": "20.00", "amount_max_usd": "100.00"},
    )
    assert replay.status_code == 200 or replay.status_code == 201
    assert replay.json()["data"]["ad"]["id"] == first["id"]

    overlap = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "overlap"), "Content-Type": "application/json"},
        json={"payment_method_id": method_id, "payment_method": "zelle", "delivery_method": "pago_movil_ve", "rate_bs_per_usd": "39.5000", "amount_min_usd": "90.00", "amount_max_usd": "100.00"},
    )
    assert overlap.status_code == 409
    assert overlap.json()["error"]["code"] == "AD_OVERLAP_NOT_ALLOWED"


def test_search_detail_exclude_unapproved_expired_and_do_not_consume_credit() -> None:
    client = _client()
    owner = _login(client, 741, "owner")
    business, method_id = _approved_business_with_method(client, owner, credits=3)
    ad = _create_ad(client, owner, method_id, key="searchable")
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"]).blocked_credits
    remitter = _login(client, 742, "remitter")

    search = client.get(
        "/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&delivery_method=pago_movil_ve&sort=rate",
        headers=_bearer(remitter, "req_search"),
    )
    assert search.status_code == 200
    assert [item["id"] for item in search.json()["data"]["items"]] == [ad["id"]]
    assert "account_value" not in search.text

    all_active = client.get("/api/v1/ads/search?sort=trust", headers=_bearer(remitter, "req_search_all"))
    assert all_active.status_code == 200
    assert ad["id"] in [item["id"] for item in all_active.json()["data"]["items"]]
    assert "account_value" not in all_active.text

    detail = client.get(f"/api/v1/ads/{ad['id']}", headers=_bearer(remitter, "req_detail"))
    assert detail.status_code == 200
    assert "account_value" not in detail.text
    assert client.app.state.ad_repository.get_wallet(business["id"]).blocked_credits == wallet_before

    stored = client.app.state.ad_repository.get_ad(ad["id"])
    stored.expires_at = stored.activated_at - timedelta(seconds=1)
    expired_detail = client.get(f"/api/v1/ads/{ad['id']}", headers=_bearer(remitter, "req_expired_detail"))
    assert expired_detail.status_code == 404
    assert expired_detail.json()["error"]["code"] == "AD_NOT_AVAILABLE"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "expired"
    assert "ad_expired" in _event_types(client)
    assert "credits_released" in _event_types(client)


def test_marketplace_search_uses_short_cache_and_ad_mutation_invalidates_it() -> None:
    client = _client()
    owner = _login(client, 743, "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=4)
    _create_ad(client, owner, method_id, key="cache_one", amount_min="20.00", amount_max="100.00")
    remitter = _login(client, 744, "remitter")
    original_list = client.app.state.ad_repository.list_marketplace_ads
    calls = {"count": 0}

    def counted_list_marketplace_ads(**kwargs):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        return original_list(**kwargs)

    client.app.state.ad_repository.list_marketplace_ads = counted_list_marketplace_ads
    query = "/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&delivery_method=pago_movil_ve&sort=rate"

    first = client.get(query, headers=_bearer(remitter, "req_cache_first"))
    second = client.get(query, headers=_bearer(remitter, "req_cache_second"))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"] == second.json()["data"]
    assert calls["count"] == 1

    _create_ad(client, owner, method_id, key="cache_two", amount_min="101.00", amount_max="200.00")
    third = client.get(query, headers=_bearer(remitter, "req_cache_third"))

    assert third.status_code == 200
    assert calls["count"] == 2


def test_marketplace_reads_use_fresh_jwt_claims_without_user_repository_lookup() -> None:
    client = _client(MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS="30")
    owner = _login(client, 745, "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=2)
    ad = _create_ad(client, owner, method_id, key="light_auth")
    remitter = _login(client, 746, "remitter")

    def fail_user_lookup(user_id: str):  # type: ignore[no-untyped-def]
        raise AssertionError(f"marketplace read should not load user {user_id}")

    client.app.state.user_repository.get_user_by_id = fail_user_lookup
    token = _access_token(remitter["user"]["id"])

    search = client.get(
        "/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&delivery_method=pago_movil_ve&sort=rate",
        headers={"Authorization": f"Bearer {token}", "X-Request-Id": "req_light_search"},
    )
    detail = client.get(
        f"/api/v1/ads/{ad['id']}",
        headers={"Authorization": f"Bearer {token}", "X-Request-Id": "req_light_detail"},
    )

    assert search.status_code == 200
    assert detail.status_code == 200
    assert "account_value" not in search.text + detail.text
    assert "storage_path" not in search.text + detail.text


def test_marketplace_read_claim_auth_default_ttl_is_five_minutes() -> None:
    client = _client()

    assert client.app.state.settings.marketplace_read_auth_claim_ttl_seconds == 300


def _profile_search_response(*, app_env: str = "test", enable_profile: str | None = None, include_header: bool = False) -> dict:
    env = {"APP_ENV": "test", "MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS": "30"}
    if enable_profile is not None:
        env["ENABLE_STAGING_PROFILING"] = enable_profile
    else:
        os.environ.pop("ENABLE_STAGING_PROFILING", None)
    client = _client(**env)
    os.environ["APP_ENV"] = app_env
    owner = _login(client, 760 + len(app_env) + (1 if include_header else 0), "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=2)
    _create_ad(client, owner, method_id, key=f"profile_{app_env}_{include_header}")
    remitter = _login(client, 780 + len(app_env) + (1 if include_header else 0), "remitter")
    headers = _bearer(remitter, f"req_profile_{app_env}_{include_header}")
    if include_header:
        headers["X-NODO-Profile"] = "1"
    response = client.get(
        "/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&delivery_method=pago_movil_ve&sort=rate",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_marketplace_profile_is_not_returned_without_full_staging_gate() -> None:
    assert "_profile" not in _profile_search_response(app_env="staging", enable_profile="1", include_header=False)
    assert "_profile" not in _profile_search_response(app_env="staging", enable_profile=None, include_header=True)
    assert "_profile" not in _profile_search_response(app_env="production", enable_profile="1", include_header=True)


def test_marketplace_profile_requires_staging_env_flag_and_header_and_is_sanitized() -> None:
    data = _profile_search_response(app_env="staging", enable_profile="1", include_header=True)

    profile = data["_profile"]
    stage_names = {stage["stage"] for stage in profile["stages"]}
    auth_stage_names = {stage["stage"] for stage in profile["dependency"]["auth"]["stages"]}

    assert profile["dependency"]["auth"]["mode"] == "marketplace_claims"
    assert "auth:marketplace_decode_access_token" in auth_stage_names
    assert "service:marketplace_access" in stage_names
    assert "service:rate_limit" in stage_names
    assert "cache:key_build" in stage_names
    assert "cache:hit" in stage_names
    assert "service:rank" in stage_names
    assert "service:payload" in stage_names

    serialized = json.dumps(profile)
    forbidden = ["account_value", "storage_path", "Authorization", "Bearer", "select ", " from ", "JWT_SECRET", "BOT_TOKEN"]
    assert not any(value in serialized for value in forbidden)


def test_marketplace_old_jwt_claim_falls_back_to_user_repository_status() -> None:
    client = _client(MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS="30")
    owner = _login(client, 747, "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=2)
    _create_ad(client, owner, method_id, key="stale_auth")
    remitter = _login(client, 748, "remitter")
    stored = client.app.state.user_repository.get_user_by_id(remitter["user"]["id"])
    stored.status = "blocked"
    stale_token = _access_token(remitter["user"]["id"], issued_at=int(time.time()) - 120)

    response = client.get(
        "/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&delivery_method=pago_movil_ve&sort=rate",
        headers={"Authorization": f"Bearer {stale_token}", "X-Request-Id": "req_stale_search"},
    )

    assert response.status_code == 403


def test_versioned_marketplace_cache_invalidates_stale_local_entries() -> None:
    from app.shared.cache import InMemoryTTLCache, VersionedLayeredTTLCache

    shared = InMemoryTTLCache()
    worker_one = VersionedLayeredTTLCache(local_cache=InMemoryTTLCache(), shared_cache=shared, namespace="marketplace:test")
    worker_two = VersionedLayeredTTLCache(local_cache=InMemoryTTLCache(), shared_cache=shared, namespace="marketplace:test")

    worker_one.set_json("marketplace:ads:50:zelle", {"items": [{"id": "old"}]}, 30)
    assert worker_two.get_json("marketplace:ads:50:zelle") == {"items": [{"id": "old"}]}

    worker_one.clear_prefix("marketplace:ads:")
    worker_one.set_json("marketplace:ads:50:zelle", {"items": [{"id": "new"}]}, 30)

    assert worker_two.get_json("marketplace:ads:50:zelle") == {"items": [{"id": "new"}]}


def test_versioned_marketplace_cache_can_cache_version_to_reduce_shared_reads() -> None:
    from app.shared.cache import InMemoryTTLCache, VersionedLayeredTTLCache

    class CountingSharedCache(InMemoryTTLCache):
        def __init__(self) -> None:
            super().__init__()
            self.version_gets = 0

        def get_text(self, key: str) -> str | None:
            if key == "marketplace:test:version":
                self.version_gets += 1
            return super().get_text(key)

    shared = CountingSharedCache()
    writer = VersionedLayeredTTLCache(local_cache=InMemoryTTLCache(), shared_cache=shared, namespace="marketplace:test")
    reader = VersionedLayeredTTLCache(
        local_cache=InMemoryTTLCache(),
        shared_cache=shared,
        namespace="marketplace:test",
        version_cache_ttl_seconds=30,
        shared_hit_local_ttl_seconds=30,
    )
    writer.set_json("marketplace:ads:50:zelle", {"items": [{"id": "cached"}]}, 30)
    shared.version_gets = 0

    assert reader.get_json("marketplace:ads:50:zelle") == {"items": [{"id": "cached"}]}
    assert reader.get_json("marketplace:ads:50:zelle") == {"items": [{"id": "cached"}]}

    assert shared.version_gets == 1


def test_pause_keeps_expiry_and_archive_releases_hold() -> None:
    client = _client()
    owner = _login(client, 751, "owner")
    business, method_id = _approved_business_with_method(client, owner, credits=2)
    ad = _create_ad(client, owner, method_id, key="pause")
    stored = client.app.state.ad_repository.get_ad(ad["id"])
    original_expires_at = stored.expires_at

    paused = client.post(f"/api/v1/business/ads/{ad['id']}/pause", headers=_headers(owner, "pause"))
    assert paused.status_code == 200
    assert paused.json()["data"]["ad"]["status"] == "paused"
    assert client.app.state.ad_repository.get_ad(ad["id"]).expires_at == original_expires_at

    archived = client.post(f"/api/v1/business/ads/{ad['id']}/archive", headers=_headers(owner, "archive"))
    assert archived.status_code == 200
    assert archived.json()["data"]["ad"]["status"] == "archived"
    wallet = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet.available_credits == 2
    assert wallet.blocked_credits == 0
    assert {"ad_paused", "ad_archived", "credits_released"}.issubset(set(_event_types(client)))


def test_archive_only_from_paused_or_expired_and_mutations_materialize_expired() -> None:
    client = _client()
    owner = _login(client, 761, "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=2)
    ad = _create_ad(client, owner, method_id, key="bad_archive")

    active_archive = client.post(f"/api/v1/business/ads/{ad['id']}/archive", headers=_headers(owner, "archive_active"))
    assert active_archive.status_code == 409
    assert active_archive.json()["error"]["code"] == "AD_STATUS_INVALID"

    stored = client.app.state.ad_repository.get_ad(ad["id"])
    stored.expires_at = stored.activated_at - timedelta(seconds=1)
    expired_update = client.put(
        f"/api/v1/business/ads/{ad['id']}",
        headers={**_headers(owner, "expired_update"), "Content-Type": "application/json"},
        json={"rate_bs_per_usd": "40.0000"},
    )
    assert expired_update.status_code == 409
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "expired"
    assert "ad_expired" in _event_types(client)


def test_owner_lists_active_and_archived_ads_with_cursor_shape() -> None:
    client = _client()
    owner = _login(client, 771, "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=2)
    ad = _create_ad(client, owner, method_id, key="list")
    client.post(f"/api/v1/business/ads/{ad['id']}/pause", headers=_headers(owner, "list_pause"))
    client.post(f"/api/v1/business/ads/{ad['id']}/archive", headers=_headers(owner, "list_archive"))

    active = client.get("/api/v1/business/ads", headers=_bearer(owner, "req_active_list"))
    archived = client.get("/api/v1/business/ads/archived", headers=_bearer(owner, "req_archived_list"))
    assert active.status_code == 200
    assert archived.status_code == 200
    assert active.json()["data"]["items"] == []
    assert archived.json()["data"]["items"][0]["status"] == "archived"
    assert "next_cursor" in archived.json()["data"]


def test_rate_limit_and_safe_errors_no_secret_or_private_data_leak() -> None:
    client = _client(BUSINESS_RATE_LIMIT_MAX_ATTEMPTS="1")
    owner = _login(client, 781, "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=2)
    _create_ad(client, owner, method_id, key="rate")

    first_list = client.get("/api/v1/business/ads", headers=_bearer(owner, "req_first_list"))
    assert first_list.status_code == 200
    limited = client.get("/api/v1/business/ads", headers=_bearer(owner, "req_limited"))
    assert limited.status_code == 429
    combined = limited.text + json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert BOT_TOKEN not in combined
    assert JWT_SECRET not in combined
    assert JWT_REFRESH_SECRET not in combined
    assert "owner@example.com" not in combined


def test_founder_access_can_publish_without_credit_debit() -> None:
    client = _client()
    owner = _login(client, 791, "founder")
    business, method_id = _approved_business_with_method(client, owner, credits=0)
    stored_business = client.app.state.business_repository.get_business(business["id"])
    stored_business.founder_status = "active"
    stored_business.founder_expires_at = stored_business.created_at + timedelta(days=7)

    ad = _create_ad(client, owner, method_id, key="founder")
    assert ad["status"] == "active"
    wallet = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet.available_credits == 0
    assert wallet.blocked_credits == 0


def test_migration_0004_contains_required_tables_constraints_and_indexes() -> None:
    migration = open("database/migrations/0004_slice_03_ads_marketplace.up.sql", encoding="utf-8").read()
    for text in [
        "create table if not exists ads",
        "create table if not exists credit_wallets",
        "create table if not exists credits_ledger",
        "ads_status_check",
        "credits_ledger_hold_reference_check",
        "credit_wallets_balances_check",
        "ads_marketplace_active_idx",
        "credits_ledger_active_hold_per_ad_idx",
    ]:
        assert text in migration
