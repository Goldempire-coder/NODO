from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MIGRATION_UP = ROOT / "database" / "migrations" / "0062_credit_contract_watcher_index.up.sql"
MIGRATION_DOWN = ROOT / "database" / "migrations" / "0062_credit_contract_watcher_index.down.sql"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_contract_watcher_index_matches_pending_purchase_reader() -> None:
    migration = _read(MIGRATION_UP)
    down = _read(MIGRATION_DOWN)
    source = _read(ROOT / "apps" / "api" / "app" / "modules" / "credits" / "postgres_onchain.py")
    selection = source.split("def list_contract_pending_purchases_pg", 1)[1].split(
        "return [purchase_from_row",
        1,
    )[0]

    assert "credit_purchases_contract_pending_watcher_idx" in migration
    assert "on credit_purchases(created_at, id)" in migration
    assert "drop index if exists credit_purchases_contract_pending_watcher_idx" in down

    required_predicates = [
        "payment_method = 'base_usdc_contract'",
        "status in ('pending_payment', 'pending_onchain_confirmation', 'detected')",
        "expected_amount_units is not null",
        "destination_wallet_address is not null",
        "onchain_purchase_ref is not null",
        "onchain_payer_address is not null",
        "payment_contract_address is not null",
        "payment_contract_version is not null",
    ]
    for predicate in required_predicates:
        assert predicate in migration
        assert predicate in selection

    assert "order by created_at asc" in selection
    assert "base_usdc_onchain" not in migration
    assert "owner_dismissed_at" not in migration
