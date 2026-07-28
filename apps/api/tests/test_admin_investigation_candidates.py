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
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


BOT_TOKEN = "123456:test-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"


def _set_env() -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-46c",
        "NODO_BUILD_ID": "pytest-admin-investigation-candidates",
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
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app  # noqa: E402
from app.modules.admin.investigation_candidates import normalize_candidate_filters  # noqa: E402
from app.modules.admin.investigation_candidates_repository import (  # noqa: E402
    PostgresAdminInvestigationCandidatesRepository,
    _escape_like_literal,
)
from app.modules.businesses.models import BusinessRecord, utc_now  # noqa: E402
from app.modules.orders.models import OrderRecord, PaymentReportRecord  # noqa: E402
from app.modules.support.models import SupportTicketRecord  # noqa: E402


def _client() -> TestClient:
    _set_env()
    return TestClient(create_app())


def _signed_init_data(telegram_id: int, username: str) -> str:
    payload = {
        "auth_date": str(int(time.time())),
        "user": json.dumps(
            {"id": telegram_id, "username": username, "first_name": username},
            separators=(",", ":"),
            sort_keys=True,
        ),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
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


def _seed_order(
    client: TestClient,
    *,
    client_login: dict,
    owner_login: dict,
    created_offset_minutes: int,
    amount: str = "50.00",
    status: str = "waiting_payment",
    ticket_status: str | None = None,
    ticket_scope: str = "client_order",
    assigned_support_user_id: str | None = None,
    with_payment_report: bool = False,
) -> dict[str, str]:
    now = utc_now() + timedelta(minutes=created_offset_minutes)
    business_id = str(uuid4())
    order_id = str(uuid4())
    business = BusinessRecord(
        id=business_id,
        owner_user_id=owner_login["user"]["id"],
        business_name=f"Negocio {owner_login['user']['username']}",
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
    order = OrderRecord(
        id=order_id,
        public_order_code=f"NODO-{order_id[:8].upper()}",
        ad_id=str(uuid4()),
        business_id=business_id,
        remitter_user_id=client_login["user"]["id"],
        status=status,
        idempotency_key="private-idempotency",
        amount_usd=Decimal(amount),
        rate_snapshot=Decimal("39.50"),
        amount_bs_calculated=Decimal(amount) * Decimal("39.50"),
        business_name_snapshot=business.business_name,
        payment_method_snapshot="zelle-private",
        delivery_method_snapshot="pago_movil_ve",
        min_amount_snapshot=Decimal("20.00"),
        max_amount_snapshot=Decimal("100.00"),
        payment_instructions_snapshot={"account_value": "private@example.com"},
        receiver_data_json={"phone": "+584121234567", "document": "V-private"},
        payment_report_deadline_at=now + timedelta(minutes=15),
        expires_at=now + timedelta(hours=1),
        created_at=now,
        updated_at=now,
    )
    client.app.state.order_repository.orders[order.id] = order
    ticket_id = ""
    if ticket_status:
        ticket_id = str(uuid4())
        ticket = SupportTicketRecord(
            id=ticket_id,
            requester_user_id=client_login["user"]["id"],
            requester_role="remitter",
            requester_surface="client_mini_app",
            scope=ticket_scope,
            category="order_help",
            status=ticket_status,
            priority="normal",
            subject="Texto privado que no debe salir",
            business_id=business_id,
            order_id=order_id,
            assigned_support_user_id=assigned_support_user_id,
            created_at=now,
            updated_at=now,
        )
        client.app.state.support_repository.tickets[ticket.id] = ticket
    if with_payment_report:
        report = PaymentReportRecord(
            id=str(uuid4()),
            order_id=order.id,
            reported_by_user_id=client_login["user"]["id"],
            status="reported",
            idempotency_key="private-report",
            payment_type="zelle",
            payment_amount=Decimal(amount),
            payment_reference="private-reference",
            payment_sender_name="Nombre privado",
            payment_sender_account_masked="***1234",
            proof_file_id=str(uuid4()),
            created_at=now,
            updated_at=now,
        )
        client.app.state.order_repository.payment_reports[report.id] = report
    return {"order_id": order_id, "business_id": business_id, "ticket_id": ticket_id}


def _valid_query(*, limit: int = 10) -> str:
    now = utc_now()
    return urlencode(
        {
            "amount_min_usd": "40.00",
            "amount_max_usd": "60.00",
            "created_from": (now - timedelta(days=1)).isoformat(),
            "created_to": (now + timedelta(days=1)).isoformat(),
            "limit": str(limit),
        }
    )


def test_admin_candidates_filters_with_and_and_returns_allowlisted_payload_and_safe_audit() -> None:
    client = _client()
    admin = _login(client, 46101, "candidate_admin", role="admin")
    remitter = _login(client, 46102, "cliente_privado")
    owner = _login(client, 46103, "negocio_match")
    client.app.state.user_repository.update_profile(
        remitter["user"]["id"],
        first_name="Cliente Uno",
        phone="+17865550123",
    )
    seeded = _seed_order(
        client,
        client_login=remitter,
        owner_login=owner,
        created_offset_minutes=0,
        ticket_status="open",
        with_payment_report=True,
    )

    now = utc_now()
    query = urlencode(
        {
            "client_hint": "5550123",
            "business_hint": "negocio_match",
            "amount_min_usd": "49.00",
            "amount_max_usd": "51.00",
            "created_from": (now - timedelta(hours=1)).isoformat(),
            "created_to": (now + timedelta(hours=1)).isoformat(),
            "order_status": "waiting_payment",
            "support_status_group": "active",
        }
    )
    response = client.get(
        f"/api/v1/admin/investigation/order-candidates?{query}",
        headers=_bearer(admin, "req_candidates_safe"),
    )

    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    payload = response.json()["data"]
    assert [item["order_id"] for item in payload["items"]] == [seeded["order_id"]]
    item = payload["items"][0]
    assert item["payment_report_present"] is True
    assert item["support_ticket_count"] == 1
    assert item["client"]["telegram_hint"]
    assert item["signals"] == sorted(
        {
            "amount_in_range",
            "business_hint_match",
            "client_hint_match",
            "created_in_window",
            "order_status_match",
            "payment_report_present",
            "support_ticket_related",
        }
    )
    serialized = json.dumps(payload).lower()
    for forbidden in (
        "severity_hint",
        "suggested_next_step",
        "storage_path",
        "signed_url",
        "file_asset_id",
        "account_value",
        "payment_instructions_snapshot",
        "receiver_data_json",
        "risk_level",
        "trust_level",
        "private-reference",
        "private-idempotency",
        "texto privado",
        "+17865550123",
        "+584121234567",
    ):
        assert forbidden not in serialized

    events = [
        event
        for event in client.app.state.audit_writer.events
        if event.event_type == "admin_investigation_candidates_searched"
    ]
    assert len(events) == 1
    audit = json.dumps(events[0].metadata_json).lower()
    assert "5550123" not in audit
    assert "negocio_match" not in audit
    assert "client_hint_present" in audit
    assert "business_hint_present" in audit


@pytest.mark.parametrize(
    ("query", "expected_code"),
    [
        ("client_hint=cliente", "ADMIN_INVESTIGATION_FILTER_REQUIRED"),
        ("client_hint=cliente&amount_min_usd=10", "ADMIN_INVESTIGATION_AMOUNT_RANGE_INVALID"),
        ("client_hint=cliente&created_from=2026-07-01T00%3A00%3A00%2B00%3A00", "ADMIN_INVESTIGATION_DATE_RANGE_INVALID"),
        (
            "client_hint=cliente&created_from=2026-05-01T00%3A00%3A00%2B00%3A00"
            "&created_to=2026-07-01T00%3A00%3A00%2B00%3A00",
            "ADMIN_INVESTIGATION_DATE_RANGE_INVALID",
        ),
    ],
)
def test_admin_candidates_rejects_unsafe_filter_combinations(query: str, expected_code: str) -> None:
    client = _client()
    admin = _login(client, 46110, "candidate_validation_admin", role="admin")

    response = client.get(
        f"/api/v1/admin/investigation/order-candidates?{query}",
        headers=_bearer(admin, "req_candidates_invalid"),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == expected_code


def test_admin_candidates_support_status_filters_before_limit_and_cursor_is_bound() -> None:
    client = _client()
    admin = _login(client, 46120, "candidate_cursor_admin", role="super_admin")
    remitter = _login(client, 46121, "candidate_cursor_client")
    owner = _login(client, 46122, "candidate_cursor_owner")
    archived = _seed_order(
        client,
        client_login=remitter,
        owner_login=owner,
        created_offset_minutes=-10,
        ticket_status="resolved",
    )
    for offset in range(6):
        _seed_order(
            client,
            client_login=remitter,
            owner_login=owner,
            created_offset_minutes=offset,
            ticket_status="open",
        )

    archived_query = f"{_valid_query(limit=1)}&support_status_group=archived"
    first = client.get(
        f"/api/v1/admin/investigation/order-candidates?{archived_query}",
        headers=_bearer(admin, "req_candidates_archived"),
    )
    assert first.status_code == 200, first.text
    assert [item["order_id"] for item in first.json()["data"]["items"]] == [archived["order_id"]]

    base_query = _valid_query(limit=2)
    all_first = client.get(
        f"/api/v1/admin/investigation/order-candidates?{base_query}",
        headers=_bearer(admin, "req_candidates_page_1"),
    )
    assert all_first.status_code == 200, all_first.text
    cursor = all_first.json()["data"]["next_cursor"]
    assert cursor
    all_second = client.get(
        f"/api/v1/admin/investigation/order-candidates?{base_query}&cursor={cursor}",
        headers=_bearer(admin, "req_candidates_page_2"),
    )
    assert all_second.status_code == 200, all_second.text
    first_ids = {item["order_id"] for item in all_first.json()["data"]["items"]}
    second_ids = {item["order_id"] for item in all_second.json()["data"]["items"]}
    assert first_ids.isdisjoint(second_ids)

    tampered = client.get(
        f"/api/v1/admin/investigation/order-candidates?{base_query}&cursor={cursor}x",
        headers=_bearer(admin, "req_candidates_cursor_tampered"),
    )
    reused = client.get(
        f"/api/v1/admin/investigation/order-candidates?{base_query}&order_status=completed&cursor={cursor}",
        headers=_bearer(admin, "req_candidates_cursor_reused"),
    )
    other_admin = _login(client, 46123, "candidate_other_admin", role="admin")
    other_actor = client.get(
        f"/api/v1/admin/investigation/order-candidates?{base_query}&cursor={cursor}",
        headers=_bearer(other_admin, "req_candidates_cursor_actor"),
    )
    assert tampered.status_code == 400
    assert reused.status_code == 400
    assert other_actor.status_code == 400
    assert tampered.json()["error"]["code"] == "ADMIN_INVESTIGATION_CURSOR_INVALID"


def test_support_permissions_and_ticket_scope_are_applied_before_limit() -> None:
    client = _client()
    super_admin = _login(client, 46130, "candidate_permissions_admin", role="super_admin")
    support = _login(client, 46131, "candidate_scoped_support", role="support")
    remitter = _login(client, 46132, "candidate_scoped_client")
    owner = _login(client, 46133, "candidate_scoped_owner")
    profile = client.app.state.staff_repository.create_or_activate_profile(
        user_id=support["user"]["id"],
        staff_role="support_agent",
        display_name="Support Scoped",
        actor_id=super_admin["user"]["id"],
        reason="candidate scope test",
    )
    client.app.state.staff_repository.replace_permissions(
        profile_id=profile.id,
        permissions=[{"permission": "view_support_queue", "scope": "category_scope", "scope_value": "order_help"}],
        actor_id=super_admin["user"]["id"],
        reason="candidate scope test",
    )
    visible = _seed_order(
        client,
        client_login=remitter,
        owner_login=owner,
        created_offset_minutes=-10,
        ticket_status="open",
    )
    for offset in range(5):
        seeded = _seed_order(
            client,
            client_login=remitter,
            owner_login=owner,
            created_offset_minutes=offset,
            ticket_status="open",
        )
        client.app.state.support_repository.tickets[seeded["ticket_id"]].category = "technical_issue"

    response = client.get(
        f"/api/v1/admin/investigation/order-candidates?{_valid_query(limit=1)}",
        headers=_bearer(support, "req_candidates_support_scope"),
    )
    assert response.status_code == 200, response.text
    assert [item["order_id"] for item in response.json()["data"]["items"]] == [visible["order_id"]]

    client.app.state.staff_repository.replace_permissions(
        profile_id=profile.id,
        permissions=[],
        actor_id=super_admin["user"]["id"],
        reason="candidate remove scope",
    )
    forbidden = client.get(
        f"/api/v1/admin/investigation/order-candidates?{_valid_query()}",
        headers=_bearer(support, "req_candidates_support_forbidden"),
    )
    assert forbidden.status_code == 403

    client.app.state.staff_repository.replace_permissions(
        profile_id=profile.id,
        permissions=[{"permission": "view_orders_masked", "scope": "global_readonly", "scope_value": None}],
        actor_id=super_admin["user"]["id"],
        reason="candidate masked orders",
    )
    masked = client.get(
        f"/api/v1/admin/investigation/order-candidates?{_valid_query(limit=1)}",
        headers=_bearer(support, "req_candidates_support_masked"),
    )
    assert masked.status_code == 200, masked.text
    serialized = json.dumps(masked.json()["data"]).lower()
    assert "risk_level" not in serialized
    assert "trust_level" not in serialized
    assert "+584121234567" not in serialized


def test_support_cursor_uses_canonical_permission_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()
    super_admin = _login(client, 46134, "candidate_cursor_permissions_admin", role="super_admin")
    support = _login(client, 46135, "candidate_cursor_permissions_support", role="support")
    remitter = _login(client, 46136, "candidate_cursor_permissions_client")
    owner = _login(client, 46137, "candidate_cursor_permissions_owner")
    profile = client.app.state.staff_repository.create_or_activate_profile(
        user_id=support["user"]["id"],
        staff_role="support_agent",
        display_name="Support Cursor",
        actor_id=super_admin["user"]["id"],
        reason="candidate cursor permission test",
    )
    client.app.state.staff_repository.replace_permissions(
        profile_id=profile.id,
        permissions=[
            {"permission": "view_support_queue", "scope": "category_scope", "scope_value": "order_help"},
            {"permission": "view_support_queue", "scope": "queue_scope", "scope_value": "client_order"},
        ],
        actor_id=super_admin["user"]["id"],
        reason="candidate cursor permission test",
    )
    for offset in range(3):
        _seed_order(
            client,
            client_login=remitter,
            owner_login=owner,
            created_offset_minutes=offset,
            ticket_status="open",
        )

    staff_repository = client.app.state.staff_repository
    list_permissions = staff_repository.list_active_permissions_for_user
    initial_rules = list_permissions(support["user"]["id"])
    monkeypatch.setattr(
        staff_repository,
        "list_active_permissions_for_user",
        lambda _user_id: [initial_rules[0], initial_rules[1], initial_rules[0]],
    )
    query = _valid_query(limit=1)
    first = client.get(
        f"/api/v1/admin/investigation/order-candidates?{query}",
        headers=_bearer(support, "req_candidates_permission_cursor_first"),
    )
    assert first.status_code == 200, first.text
    cursor = first.json()["data"]["next_cursor"]
    assert cursor

    monkeypatch.setattr(
        staff_repository,
        "list_active_permissions_for_user",
        lambda _user_id: [initial_rules[1], initial_rules[0]],
    )
    reordered = client.get(
        f"/api/v1/admin/investigation/order-candidates?{query}&cursor={cursor}",
        headers=_bearer(support, "req_candidates_permission_cursor_reordered"),
    )
    assert reordered.status_code == 200, reordered.text

    staff_repository.replace_permissions(
        profile_id=profile.id,
        permissions=[
            {"permission": "view_support_queue", "scope": "category_scope", "scope_value": "order_help"},
        ],
        actor_id=super_admin["user"]["id"],
        reason="candidate cursor permission changed",
    )
    monkeypatch.setattr(staff_repository, "list_active_permissions_for_user", list_permissions)
    changed = client.get(
        f"/api/v1/admin/investigation/order-candidates?{query}&cursor={cursor}",
        headers=_bearer(support, "req_candidates_permission_cursor_changed"),
    )
    assert changed.status_code == 400
    assert changed.json()["error"]["code"] == "ADMIN_INVESTIGATION_CURSOR_INVALID"


def test_candidate_search_rejects_non_admin_surfaces_and_inactive_staff() -> None:
    client = _client()
    remitter = _login(client, 46140, "candidate_forbidden_client")
    support = _login(client, 46141, "candidate_inactive_support", role="support")

    no_session = client.get(f"/api/v1/admin/investigation/order-candidates?{_valid_query()}")
    client_response = client.get(
        f"/api/v1/admin/investigation/order-candidates?{_valid_query()}",
        headers=_bearer(remitter, "req_candidates_client"),
    )
    support_response = client.get(
        f"/api/v1/admin/investigation/order-candidates?{_valid_query()}",
        headers=_bearer(support, "req_candidates_support_inactive"),
    )

    assert no_session.status_code == 401
    assert client_response.status_code == 403
    assert support_response.status_code == 403


@pytest.mark.parametrize(
    ("raw_hint", "escaped_hint"),
    [
        ("abc%def", r"abc\%def"),
        ("abc_def", r"abc\_def"),
        ("abc\\def", r"abc\\def"),
    ],
)
def test_like_hint_escape_is_literal(raw_hint: str, escaped_hint: str) -> None:
    assert _escape_like_literal(raw_hint) == escaped_hint


def test_postgres_candidate_query_escapes_like_wildcards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class Result:
        @staticmethod
        def fetchall() -> list:
            return []

    class Connection:
        @staticmethod
        def execute(query: str, params: list[object]) -> Result:
            captured["query"] = query
            captured["params"] = params
            return Result()

    class Context:
        @staticmethod
        def __enter__() -> Connection:
            return Connection()

        @staticmethod
        def __exit__(*args) -> None:  # type: ignore[no-untyped-def]
            return None

    monkeypatch.setattr(
        "app.modules.admin.investigation_candidates_repository.pooled_connect",
        lambda _database_url: Context(),
    )
    filters = normalize_candidate_filters(
        client_hint="%_\\",
        business_hint="%_\\",
        amount_min_usd=None,
        amount_max_usd=None,
        created_from=None,
        created_to=None,
        order_status=None,
        support_status_group="all",
    )
    repository = PostgresAdminInvestigationCandidatesRepository("postgresql://unused")

    repository.search(
        filters=filters,
        visibility={"mode": "admin"},
        position=None,
        limit=10,
    )

    escaped_pattern = r"%\%\_\\%"
    assert captured["params"][:9] == [escaped_pattern] * 9
    query = str(captured["query"]).lower()
    assert query.count("escape e'\\\\'") == 9
    assert query.index("where") < query.index("order by")
    assert query.index("order by") < query.index("limit")


def test_admin_candidates_frontend_contract_is_separate_from_quick_search() -> None:
    root = Path(__file__).resolve().parents[3]
    screen = (root / "apps/web/src/screens/admin-web/AdminInvestigationCandidatesScreen.tsx").read_text(encoding="utf-8")
    hook = (root / "apps/web/src/hooks/admin-web/useAdminInvestigationCandidatesModel.ts").read_text(encoding="utf-8")
    quick = (root / "apps/web/src/screens/admin-web/AdminInvestigationScreens.tsx").read_text(encoding="utf-8")

    assert "Filtros avanzados" in quick
    assert "searchAdminInvestigationCandidates" in hook
    assert "Abrir orden" in screen
    assert "Investigar" in screen
    assert "openCaseFile" in hook
    assert "executedFiltersRef" in hook
    assert "requestSequenceRef" in hook
    assert "setResults(null)" in hook
    assert "filtersKey(executedFilters) !== filtersKey(currentFilters)" in hook
    assert "requestSequence !== requestSequenceRef.current" in hook
    assert "textarea" not in screen
    assert "chat" not in screen.lower()
