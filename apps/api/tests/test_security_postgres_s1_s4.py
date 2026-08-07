from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from photo_test_data import photo_bytes, png_bytes


POSTGRES_OPT_IN = "NODO_RUN_SECURITY_POSTGRES"
POSTGRES_URL_ENV = "NODO_SECURITY_POSTGRES_URL"
VALID_TRON_TEST_WALLET = "TLa2f6VPqDgRE67v" + "1736s7bJ8Ray5wYjU7"


@dataclass
class SecurityPostgresContext:
    client: TestClient
    database_url: str
    sequence: int = 0

    def key(self, label: str) -> str:
        self.sequence += 1
        return f"security_pg_{label}_{self.sequence}_{uuid4().hex[:8]}"


def _require_disposable_local_database() -> str:
    if os.environ.get(POSTGRES_OPT_IN) != "1":
        pytest.skip(f"set {POSTGRES_OPT_IN}=1 for disposable local PostgreSQL validation")
    database_url = os.environ.get(POSTGRES_URL_ENV, "")
    parsed = urlparse(database_url)
    database_name = parsed.path.removeprefix("/").lower()
    if parsed.hostname not in {"127.0.0.1", "localhost"} or not database_name.startswith("nodo_security_"):
        raise RuntimeError("security PostgreSQL tests require a disposable localhost nodo_security_* database")
    return database_url


@pytest.fixture(scope="module")
def postgres_security() -> SecurityPostgresContext:
    database_url = _require_disposable_local_database()
    os.environ.update(
        {
            "APP_ENV": "local",
            "APP_NAME": "NODO",
            "APP_VERSION": "security-postgres-local",
            "NODO_BUILD_ID": "security-postgres-local",
            "DATABASE_URL": database_url,
            "REDIS_URL": "redis://127.0.0.1:1/15",
            "API_CORS_ORIGINS": "http://localhost:3000",
            "BOT_TOKEN": "123456:security-postgres-local-bot",
            "JWT_SECRET": "security-postgres-local-access-secret",
            "JWT_REFRESH_SECRET": "security-postgres-local-refresh-secret",
            "AUTH_RATE_LIMIT_MAX_ATTEMPTS": "1000",
            "BUSINESS_RATE_LIMIT_MAX_ATTEMPTS": "1000",
            "ORDER_NOTIFICATION_SENDER_ENABLED": "0",
            "ONCHAIN_CREDIT_WATCHER_ENABLED": "0",
            "PRIVATE_STORAGE_MODE": "unavailable",
            "NODO_DB_POOL_WARM_SIZE": "2",
        }
    )

    from app.main import create_app
    from app.modules.jobs.lock import InMemoryJobLockManager
    from app.shared.cache import InMemoryTTLCache
    from app.shared.idempotency.store import InMemoryIdempotencyStore
    from app.shared.rate_limit.in_memory import InMemoryRateLimiter
    from app.shared.storage.private import InMemoryPrivateStorage

    app = create_app()
    app.state.rate_limiter = InMemoryRateLimiter()
    app.state.marketplace_rate_limiter = InMemoryRateLimiter()
    app.state.idempotency_store = InMemoryIdempotencyStore()
    app.state.marketplace_cache = InMemoryTTLCache()
    app.state.admin_read_model_cache = InMemoryTTLCache()
    app.state.auth_user_cache = None
    app.state.private_storage = InMemoryPrivateStorage()
    app.state.job_lock_manager = InMemoryJobLockManager()
    client = TestClient(app)

    with psycopg.connect(database_url) as conn:
        current_database = conn.execute("select current_database()").fetchone()[0]
        sessions_column = conn.execute(
            "select 1 from information_schema.columns where table_name = 'sessions' and column_name = 'access_token_jti'"
        ).fetchone()
    assert current_database.lower().startswith("nodo_security_")
    assert sessions_column is not None

    yield SecurityPostgresContext(client=client, database_url=database_url)
    client.close()


def _actor(
    context: SecurityPostgresContext,
    *,
    telegram_id: int,
    username: str,
    role: str = "remitter",
    access_ttl_seconds: int = 900,
) -> dict:
    from app.auth.jwt import create_access_token, create_refresh_token, hash_refresh_token
    from app.modules.users.models import utc_now
    from app.modules.users.presenters import public_user_payload
    from app.modules.users.terms import CURRENT_TERMS_VERSION

    repository = context.client.app.state.user_repository
    user, _ = repository.upsert_telegram_user(
        telegram_id=telegram_id,
        username=username,
        first_name=username,
        last_name=None,
    )
    if user.role != role:
        repository.set_user_role(user.id, role)
        user = repository.get_user_by_id(user.id)
    user = repository.accept_terms(user.id, CURRENT_TERMS_VERSION)
    settings = context.client.app.state.settings
    access_token, access_token_jti, _ = create_access_token(
        user_id=user.id,
        role=user.role,
        status=user.status,
        secret=settings.jwt_secret,
        ttl_seconds=access_ttl_seconds,
    )
    refresh_token = create_refresh_token()
    repository.create_session(
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(refresh_token, settings.jwt_refresh_secret),
        access_token_jti=access_token_jti,
        expires_at=utc_now() + timedelta(days=1),
        ip_hash=None,
        user_agent="security-postgres-test",
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": public_user_payload(user),
    }


def _headers(actor: dict, key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {actor['access_token']}",
        "X-Request-Id": f"req_{key}",
        "Idempotency-Key": key,
    }


def _bearer(actor: dict, key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {actor['access_token']}",
        "X-Request-Id": f"req_{key}",
    }


def _business_order_fixture(
    context: SecurityPostgresContext,
    *,
    admin: dict,
    method_type: str,
) -> dict:
    from app.modules.businesses.pin_security import hash_pin
    from app.modules.users.models import utc_now

    key = context.key(method_type)
    actor_suffix = int(uuid4().hex[:8], 16) % 800_000_000
    owner = _actor(
        context,
        telegram_id=8_100_000_000 + actor_suffix,
        username=f"owner_{key}",
        role="business_owner",
    )
    remitter = _actor(
        context,
        telegram_id=9_000_000_000 + actor_suffix,
        username=f"remitter_{key}",
    )
    business_repository = context.client.app.state.business_repository
    business = business_repository.create_business(
        owner_user_id=owner["user"]["id"],
        business_name=f"Casa Security {key}",
        rif=f"J-{10_000_000 + (actor_suffix % 89_999_999):08d}-9",
        address="Av Local 1",
        phone="0414 1234567",
        country="VE",
    )
    with psycopg.connect(context.database_url) as conn:
        conn.execute(
            """
            update businesses
            set verification_status = 'approved', approved_at = now(),
                min_order_amount_usd = 20.00, max_order_amount_usd = 1000.00,
                daily_limit_usd = 1000.00, active_order_limit = 2,
                is_accepting_orders = true, updated_at = now()
            where id = %s
            """,
            (business.id,),
        )
    owner_record = context.client.app.state.user_repository.get_user_by_id(owner["user"]["id"])
    link = business_repository.create_access_link(
        business_id=business.id,
        user_id=owner_record.id,
        telegram_id_snapshot=owner_record.telegram_id,
        role_in_business="owner",
        linked_by_admin_id=admin["user"]["id"],
        reason="security postgres local fixture",
    )
    business_repository.set_access_link_pin_hash(link_id=link.id, pin_hash=hash_pin("1234"))
    business_repository.mark_access_link_pin_verified(
        link_id=link.id,
        unlocked_until=utc_now() + timedelta(minutes=30),
    )
    account_value = f"{key}@example.local" if method_type == "zelle" else VALID_TRON_TEST_WALLET
    payment_method = business_repository.add_payment_method(
        business_id=business.id,
        method_type=method_type,
        network="TRC20" if method_type == "usdt_trc20" else None,
        account_value=account_value,
        account_masked="***@example.local" if method_type == "zelle" else "TLa2f...wYjU7",
        holder_name="Owner Local",
    )
    with psycopg.connect(context.database_url) as conn:
        conn.execute(
            "update business_payment_methods set verified_status = 'approved', active = true, updated_at = now() where id = %s",
            (payment_method.id,),
        )
    context.client.app.state.capacity_repository.set_declared_capacity(
        business_id=business.id,
        amount_usd=Decimal("100.00"),
        actor_user_id=owner["user"]["id"],
    )
    credits = context.client.post(
        "/api/v1/admin/credits/adjust",
        headers={**_headers(admin, context.key("credits")), "Content-Type": "application/json"},
        json={
            "business_id": business.id,
            "amount": 3,
            "direction": "add",
            "reason": "security_postgres_local_fixture",
        },
    )
    assert credits.status_code == 200, credits.text
    ad_response = context.client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, context.key("ad")), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment_method.id,
            "payment_method": method_type,
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "20.00",
            "amount_max_usd": "100.00",
        },
    )
    assert ad_response.status_code == 201, ad_response.text
    ad = ad_response.json()["data"]["ad"]
    order_response = context.client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, context.key("order")), "Content-Type": "application/json"},
        json={"ad_id": ad["id"], "amount_usd": "50.00"},
    )
    assert order_response.status_code == 201, order_response.text
    return {
        "owner": owner,
        "remitter": remitter,
        "business_id": business.id,
        "account_value": account_value,
        "order": order_response.json()["data"]["order"],
    }


def _payment_report_payload(method_type: str, *, seed: int) -> dict:
    payload = {"payment_type": method_type, "payment_amount": "50.00"}
    if method_type == "usdt_trc20":
        payload.update({"tx_hash": f"{seed:064x}", "network": "TRC20"})
    return payload


def _assert_error(response, *, status_code: int, code: str) -> None:  # type: ignore[no-untyped-def]
    assert response.status_code == status_code, response.text
    assert response.json()["error"]["code"] == code


def test_postgres_official_payment_marker_controls_zelle_and_usdt_reports(
    postgres_security: SecurityPostgresContext,
) -> None:
    admin = _actor(postgres_security, telegram_id=8_000_000_001, username="security_admin", role="admin")

    for method_type in ("zelle", "usdt_trc20"):
        fixture = _business_order_fixture(
            postgres_security,
            admin=admin,
            method_type=method_type,
        )
        order_id = fixture["order"]["id"]
        report_payload = _payment_report_payload(method_type, seed=int(uuid4().hex, 16))
        before_share = postgres_security.client.post(
            f"/api/v1/orders/{order_id}/payment-report",
            headers={**_headers(fixture["remitter"], postgres_security.key("report_before")), "Content-Type": "application/json"},
            json=report_payload,
        )
        _assert_error(before_share, status_code=409, code="ORDER_PAYMENT_DETAILS_NOT_SHARED")

        forged = postgres_security.client.post(
            f"/api/v1/orders/{order_id}/messages",
            headers={
                **_headers(fixture["owner"], f"official_payment_details:{postgres_security.key('forged')}"),
                "Content-Type": "application/json",
            },
            json={"body": fixture["account_value"], "attachment_ids": []},
        )
        _assert_error(forged, status_code=400, code="VALIDATION_ERROR")

        free_message = postgres_security.client.post(
            f"/api/v1/orders/{order_id}/messages",
            headers={**_headers(fixture["owner"], postgres_security.key("free_payment_text")), "Content-Type": "application/json"},
            json={
                "body": f"WhatsApp +584141234567. Datos: {fixture['account_value']}",
                "attachment_ids": [],
            },
        )
        assert free_message.status_code == 201, free_message.text
        chat_before_share = postgres_security.client.get(
            f"/api/v1/orders/{order_id}/messages",
            headers=_bearer(fixture["remitter"], postgres_security.key("chat_before_share")),
        )
        assert chat_before_share.status_code == 200, chat_before_share.text
        assert chat_before_share.json()["data"]["capabilities"]["can_report_payment"] is False
        after_free_text = postgres_security.client.post(
            f"/api/v1/orders/{order_id}/payment-report",
            headers={**_headers(fixture["remitter"], postgres_security.key("report_after_free")), "Content-Type": "application/json"},
            json=report_payload,
        )
        _assert_error(after_free_text, status_code=409, code="ORDER_PAYMENT_DETAILS_NOT_SHARED")

        with psycopg.connect(postgres_security.database_url) as conn:
            alert_count = conn.execute(
                "select count(*) from audit_logs where event_type = 'order_chat_off_platform_solicitation_detected' and metadata_json ->> 'order_id' = %s",
                (order_id,),
            ).fetchone()[0]
        assert alert_count == 1

        share = postgres_security.client.post(
            f"/api/v1/orders/{order_id}/share-payment-details",
            headers=_headers(fixture["owner"], postgres_security.key("official_share")),
        )
        assert share.status_code == 201, share.text
        chat_after_share = postgres_security.client.get(
            f"/api/v1/orders/{order_id}/messages",
            headers=_bearer(fixture["remitter"], postgres_security.key("chat_after_share")),
        )
        assert chat_after_share.status_code == 200, chat_after_share.text
        assert chat_after_share.json()["data"]["capabilities"]["can_report_payment"] is True

        with psycopg.connect(postgres_security.database_url) as conn:
            official_keys = conn.execute(
                "select idempotency_key from messages where order_id = %s and position(%s in idempotency_key) = 1",
                (order_id, "official_payment_details:"),
            ).fetchall()
            alert_count_after_share = conn.execute(
                "select count(*) from audit_logs where event_type = 'order_chat_off_platform_solicitation_detected' and metadata_json ->> 'order_id' = %s",
                (order_id,),
            ).fetchone()[0]
        assert len(official_keys) == 1
        assert official_keys[0][0].startswith("official_payment_details:")
        assert alert_count_after_share == 1

        report = postgres_security.client.post(
            f"/api/v1/orders/{order_id}/payment-report",
            headers={**_headers(fixture["remitter"], postgres_security.key("report_after_share")), "Content-Type": "application/json"},
            json=report_payload,
        )
        assert report.status_code == 201, report.text
        with psycopg.connect(postgres_security.database_url) as conn:
            report_count = conn.execute(
                "select count(*) from payment_reports where order_id = %s",
                (order_id,),
            ).fetchone()[0]
        assert report_count == 1


def test_postgres_photo_uploads_reject_disguised_files_and_store_canonical_metadata(
    postgres_security: SecurityPostgresContext,
) -> None:
    admin = _actor(postgres_security, telegram_id=8_000_000_010, username="upload_admin", role="admin")
    fixture = _business_order_fixture(
        postgres_security,
        admin=admin,
        method_type="zelle",
    )
    order_id = fixture["order"]["id"]
    remitter = fixture["remitter"]

    chat_html = postgres_security.client.post(
        f"/api/v1/orders/{order_id}/message-attachments",
        headers=_headers(remitter, postgres_security.key("chat_html")),
        files={"file": ("photo.jpg", b"<html>not a photo</html>", "image/jpeg")},
    )
    chat_pdf = postgres_security.client.post(
        f"/api/v1/orders/{order_id}/message-attachments",
        headers=_headers(remitter, postgres_security.key("chat_pdf")),
        files={"file": ("document.pdf", b"%PDF-1.7", "application/pdf")},
    )
    chat_png = postgres_security.client.post(
        f"/api/v1/orders/{order_id}/message-attachments",
        headers=_headers(remitter, postgres_security.key("chat_png")),
        files={"file": ("renamed.bin", png_bytes(b"security-postgres-chat"), "image/png")},
    )
    chat_mismatch = postgres_security.client.post(
        f"/api/v1/orders/{order_id}/message-attachments",
        headers=_headers(remitter, postgres_security.key("chat_mismatch")),
        files={"file": ("photo.jpg", png_bytes(b"security-postgres-mismatch"), "image/jpeg")},
    )
    evidence_pdf = postgres_security.client.post(
        f"/api/v1/orders/{order_id}/payment-evidence",
        headers=_headers(remitter, postgres_security.key("evidence_pdf")),
        data={"file_type": "payment_evidence"},
        files={"file": ("proof.pdf", b"%PDF-1.7", "application/pdf")},
    )
    evidence_webp = postgres_security.client.post(
        f"/api/v1/orders/{order_id}/payment-evidence",
        headers=_headers(remitter, postgres_security.key("evidence_webp")),
        data={"file_type": "payment_evidence"},
        files={"file": ("proof.any", photo_bytes("WEBP", b"security-postgres-evidence"), "image/webp")},
    )

    _assert_error(chat_html, status_code=400, code="MESSAGE_ATTACHMENT_INVALID")
    _assert_error(chat_pdf, status_code=400, code="MESSAGE_ATTACHMENT_TYPE_NOT_ALLOWED")
    _assert_error(chat_mismatch, status_code=400, code="MESSAGE_ATTACHMENT_INVALID")
    _assert_error(evidence_pdf, status_code=400, code="INVALID_PAYMENT_EVIDENCE")
    assert chat_png.status_code == 201, chat_png.text
    assert evidence_webp.status_code == 201, evidence_webp.text
    chat_file_id = chat_png.json()["data"]["attachment"]["file_asset_id"]
    evidence_file_id = evidence_webp.json()["data"]["file"]["id"]

    with psycopg.connect(postgres_security.database_url, row_factory=dict_row) as conn:
        rows = conn.execute(
            "select id::text, storage_path, mime_type from file_assets where id = any(%s)",
            ([chat_file_id, evidence_file_id],),
        ).fetchall()
    stored = {row["id"]: row for row in rows}
    assert stored[chat_file_id]["mime_type"] == "image/png"
    assert stored[chat_file_id]["storage_path"].endswith(".png")
    assert not stored[chat_file_id]["storage_path"].endswith(".bin")
    assert stored[evidence_file_id]["mime_type"] == "image/webp"
    assert stored[evidence_file_id]["storage_path"].endswith(".webp")
    assert not stored[evidence_file_id]["storage_path"].endswith(".any")


def test_postgres_blocked_users_lose_private_access_on_the_next_request(
    postgres_security: SecurityPostgresContext,
) -> None:
    admin = _actor(postgres_security, telegram_id=8_000_000_020, username="block_admin", role="admin")
    fixture = _business_order_fixture(
        postgres_security,
        admin=admin,
        method_type="zelle",
    )
    order_id = fixture["order"]["id"]
    remitter = fixture["remitter"]
    before = postgres_security.client.get(
        f"/api/v1/orders/{order_id}/messages",
        headers=_bearer(remitter, postgres_security.key("before_block")),
    )
    assert before.status_code == 200, before.text
    blocked = postgres_security.client.post(
        f"/api/v1/admin/users/{remitter['user']['id']}/block",
        headers={**_headers(admin, postgres_security.key("block_remitter")), "Content-Type": "application/json"},
        json={"reason": "security local revocation test"},
    )
    assert blocked.status_code == 200, blocked.text

    attempts = [
        postgres_security.client.get(
            f"/api/v1/orders/{order_id}/messages",
            headers=_bearer(remitter, postgres_security.key("blocked_read")),
        ),
        postgres_security.client.post(
            f"/api/v1/orders/{order_id}/messages",
            headers={**_headers(remitter, postgres_security.key("blocked_write")), "Content-Type": "application/json"},
            json={"body": "must not persist", "attachment_ids": []},
        ),
        postgres_security.client.post(
            f"/api/v1/orders/{order_id}/payment-evidence",
            headers=_headers(remitter, postgres_security.key("blocked_evidence")),
            data={"file_type": "payment_evidence"},
            files={"file": ("proof.png", png_bytes(b"blocked-evidence"), "image/png")},
        ),
        postgres_security.client.post(
            f"/api/v1/orders/{order_id}/payment-report",
            headers={**_headers(remitter, postgres_security.key("blocked_report")), "Content-Type": "application/json"},
            json={"payment_type": "zelle", "payment_amount": "50.00"},
        ),
        postgres_security.client.post(
            f"/api/v1/orders/{order_id}/cancel",
            headers={**_headers(remitter, postgres_security.key("blocked_cancel")), "Content-Type": "application/json"},
            json={"reason": "choose_another_business", "payment_not_sent_confirmed": True},
        ),
    ]
    for attempt in attempts:
        _assert_error(attempt, status_code=403, code="USER_SUSPENDED")

    owner_fixture = _business_order_fixture(
        postgres_security,
        admin=admin,
        method_type="usdt_trc20",
    )
    owner = owner_fixture["owner"]
    owner_blocked = postgres_security.client.post(
        f"/api/v1/admin/users/{owner['user']['id']}/block",
        headers={**_headers(admin, postgres_security.key("block_owner")), "Content-Type": "application/json"},
        json={"reason": "security local business revocation test"},
    )
    assert owner_blocked.status_code == 200, owner_blocked.text
    owner_order_id = owner_fixture["order"]["id"]
    owner_attempts = [
        postgres_security.client.post(
            f"/api/v1/orders/{owner_order_id}/messages",
            headers={**_headers(owner, postgres_security.key("blocked_owner_message")), "Content-Type": "application/json"},
            json={"body": "must not persist", "attachment_ids": []},
        ),
        postgres_security.client.post(
            f"/api/v1/orders/{owner_order_id}/share-payment-details",
            headers=_headers(owner, postgres_security.key("blocked_owner_share")),
        ),
        postgres_security.client.post(
            f"/api/v1/business/orders/{owner_order_id}/confirm-payment",
            headers={**_headers(owner, postgres_security.key("blocked_owner_confirm")), "Content-Type": "application/json"},
            json={"reason": "must not run"},
        ),
        postgres_security.client.post(
            f"/api/v1/business/orders/{owner_order_id}/mark-delivered",
            headers={**_headers(owner, postgres_security.key("blocked_owner_delivered")), "Content-Type": "application/json"},
            json={"reason": "must not run"},
        ),
    ]
    for attempt in owner_attempts:
        _assert_error(attempt, status_code=403, code="USER_SUSPENDED")


def test_postgres_logout_revokes_only_the_matching_access_session(
    postgres_security: SecurityPostgresContext,
) -> None:
    from app.auth.jwt import decode_access_token

    telegram_id = 8_300_000_030
    first = _actor(postgres_security, telegram_id=telegram_id, username="logout_user")
    second = _actor(postgres_security, telegram_id=telegram_id, username="logout_user")
    first_headers = _bearer(first, postgres_security.key("first_session"))
    second_headers = _bearer(second, postgres_security.key("second_session"))
    assert postgres_security.client.get("/api/v1/users/me", headers=first_headers).status_code == 200
    assert postgres_security.client.get("/api/v1/users/me", headers=second_headers).status_code == 200

    logout = postgres_security.client.post(
        "/api/v1/auth/logout",
        headers=first_headers,
        json={"refresh_token": first["refresh_token"]},
    )
    first_after = postgres_security.client.get("/api/v1/users/me", headers=first_headers)
    second_after = postgres_security.client.get("/api/v1/users/me", headers=second_headers)
    refresh_after = postgres_security.client.post(
        "/api/v1/auth/refresh",
        headers={"X-Request-Id": postgres_security.key("refresh_after_logout")},
        json={"refresh_token": first["refresh_token"]},
    )
    assert logout.status_code == 200, logout.text
    _assert_error(first_after, status_code=401, code="SESSION_EXPIRED")
    _assert_error(refresh_after, status_code=401, code="SESSION_EXPIRED")
    assert second_after.status_code == 200, second_after.text

    first_jti = decode_access_token(first["access_token"], postgres_security.client.app.state.settings.jwt_secret)["jti"]
    second_jti = decode_access_token(second["access_token"], postgres_security.client.app.state.settings.jwt_secret)["jti"]
    with psycopg.connect(postgres_security.database_url, row_factory=dict_row) as conn:
        sessions = conn.execute(
            "select access_token_jti, status from sessions where access_token_jti = any(%s)",
            ([first_jti, second_jti],),
        ).fetchall()
        index_exists = conn.execute(
            "select 1 from pg_indexes where schemaname = 'public' and indexname = 'sessions_access_token_jti_idx'",
        ).fetchone()
    statuses = {row["access_token_jti"]: row["status"] for row in sessions}
    assert statuses == {first_jti: "revoked", second_jti: "active"}
    assert index_exists is not None

    malformed_session = _actor(
        postgres_security,
        telegram_id=8_300_000_031,
        username="malformed_logout_user",
    )
    malformed_logout = postgres_security.client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer malformed", "X-Request-Id": postgres_security.key("malformed_logout")},
        json={"refresh_token": malformed_session["refresh_token"]},
    )
    assert malformed_logout.status_code == 200, malformed_logout.text

    expired_session = _actor(
        postgres_security,
        telegram_id=8_300_000_032,
        username="expired_logout_user",
        access_ttl_seconds=-1,
    )
    expired_logout = postgres_security.client.post(
        "/api/v1/auth/logout",
        headers={
            "Authorization": f"Bearer {expired_session['access_token']}",
            "X-Request-Id": postgres_security.key("expired_logout"),
        },
        json={"refresh_token": expired_session["refresh_token"]},
    )
    assert expired_logout.status_code == 200, expired_logout.text

    serialized = json.dumps(
        {
            "logout": logout.json(),
            "malformed_logout": malformed_logout.json(),
            "expired_logout": expired_logout.json(),
        }
    )
    assert first["access_token"] not in serialized
    assert first["refresh_token"] not in serialized
