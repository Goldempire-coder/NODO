from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_slice_49a_migration_is_reversible_and_checks_existing_hash_duplicates() -> None:
    up = (
        ROOT
        / "database"
        / "migrations"
        / "0039_order_payment_cancellation_integrity.up.sql"
    ).read_text(encoding="utf-8")
    down = (
        ROOT
        / "database"
        / "migrations"
        / "0039_order_payment_cancellation_integrity.down.sql"
    ).read_text(encoding="utf-8")

    assert "payment_reports_network_tx_hash_unique_idx" in up
    assert "invalid payment report transaction hashes require review" in up
    assert "regexp_replace(lower(trim(tx_hash)), '^0x', '')" in up
    assert "payment_reports_tx_hash_format_check" in up
    assert "payment_reports_proof_file_unique_idx" in up
    assert "payment_reports_proof_content_sha256_unique_idx" in up
    assert "payment_reports_proof_content_sha256_check" in up
    assert "payment reports with proof files missing content hashes require controlled backfill" in up
    assert "invalid payment report proof content hashes require review" in up
    assert "having count(*) > 1" in up
    assert "orders_cancel_reason_check" in up
    assert "business_unavailable" in up
    assert "admin_cancelled" in up
    assert "order_cancelled_business_unavailable" in up
    assert "drop index if exists payment_reports_network_tx_hash_unique_idx" in down
    assert "payment_reports_tx_hash_format_check" in down
    assert "drop index if exists payment_reports_proof_file_unique_idx" in down
    assert "drop index if exists payment_reports_proof_content_sha256_unique_idx" in down
    assert "drop column if exists proof_content_sha256" in down
    assert "rolled_back_notification_type" in down
    assert "status = case" in down
    assert "delete from notification_jobs" not in down
    assert "business_unavailable" in down
    assert "admin_cancelled" in down


def test_slice_49a_frontend_exposes_structured_business_action_without_prepayment_chat() -> None:
    api = (ROOT / "apps" / "web" / "src" / "api" / "businessOrders.ts").read_text(
        encoding="utf-8"
    )
    hook = (
        ROOT
        / "apps"
        / "web"
        / "src"
        / "hooks"
        / "business-mini-app"
        / "useBusinessOrdersModel.ts"
    ).read_text(encoding="utf-8")
    screen = (
        ROOT
        / "apps"
        / "web"
        / "src"
        / "screens"
        / "business-app"
        / "BusinessOrdersScreens.tsx"
    ).read_text(encoding="utf-8")

    assert "/cannot-attend" in api
    assert '"cannot-attend"' in hook
    assert "No puedo atender" in screen
    assert 'can_decline_before_payment' in screen
    assert 'waiting_payment' not in (
        ROOT / "apps" / "api" / "app" / "modules" / "chat" / "policy.py"
    ).read_text(encoding="utf-8").split("require_message_state", 1)[1].split(
        "raise ApiError", 1
    )[0]


def test_slice_49a_does_not_enable_expiration_scheduler_implicitly() -> None:
    main = (ROOT / "apps" / "api" / "app" / "main.py").read_text(encoding="utf-8")
    contract = (
        ROOT
        / "control_plane"
        / "09_SLICES"
        / "slice_49A_order_payment_cancellation_integrity"
        / "README.md"
    ).read_text(encoding="utf-8")

    assert "_expire_and_escalate_orders_loop" not in main
    assert "Expiration automation is not enabled" in contract


def test_slice_49a_postgres_paths_lock_and_revalidate_inside_transactions() -> None:
    integrity = (
        ROOT
        / "apps"
        / "api"
        / "app"
        / "modules"
        / "orders"
        / "postgres_integrity.py"
    ).read_text(encoding="utf-8").lower()
    capacity = (
        ROOT
        / "apps"
        / "api"
        / "app"
        / "modules"
        / "business_capacity"
        / "postgres_repository.py"
    ).read_text(encoding="utf-8").lower()
    create_order = (
        ROOT
        / "apps"
        / "api"
        / "app"
        / "modules"
        / "orders"
        / "postgres_create_order.py"
    ).read_text(encoding="utf-8").lower()

    assert "select * from orders where id = %s for update" in integrity
    assert "clock_timestamp()" in integrity
    assert "where id = %s and status = 'waiting_payment'" in integrity
    assert "expire_hold_in_transaction" in integrity
    assert "for update of capacity, businesses" in capacity
    assert "lock_order_create_capacity_in_transaction" in capacity
    assert (
        create_order.index("lock_order_create_capacity_in_transaction")
        < create_order.index("_move_ad_to_in_order_or_raise")
        < create_order.index("_insert_order")
    )
    assert "active_order_limit" in capacity
    assert "select count(*) as active_count" in capacity
    assert "count already includes the order currently reserving capacity" in capacity
    assert 'active_count"]) > int(' in capacity
