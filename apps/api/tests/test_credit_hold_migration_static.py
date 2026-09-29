from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
UP = ROOT / "database/migrations/0065_credit_hold_idempotency.up.sql"
DOWN = ROOT / "database/migrations/0065_credit_hold_idempotency.down.sql"


@pytest.mark.parametrize(
    "kind,key,suffix",
    [
        ("release", "related_ad_id", "ad"),
        ("consume", "related_order_id", "order"),
        ("expire", "related_ad_id", "ad"),
    ],
)
def test_each_duplicate_guard_has_a_partial_unique_index(kind, key, suffix):
    up = " ".join(UP.read_text(encoding="utf-8").split())
    down = DOWN.read_text(encoding="utf-8")
    name = f"credits_ledger_{kind}_{suffix}_unique_idx"
    assert (
        f"create unique index {name} on credits_ledger({key}) where type = '{kind}';"
        in up
    )
    assert f"drop index if exists {name};" in down


def test_migration_only_adds_constraints_and_rollback_only_drops_its_indexes():
    up = UP.read_text(encoding="utf-8")
    statements = (
        "\n".join(line for line in up.splitlines() if not line.startswith("--"))
        .strip()
        .split(";")
    )
    assert len([statement for statement in statements if statement.strip()]) == 3
    assert all(
        statement.strip().startswith("create unique index credits_ledger_")
        for statement in statements
        if statement.strip()
    )
    assert "if not exists" not in up.lower()
    down = DOWN.read_text(encoding="utf-8").splitlines()
    assert len(down) == 3
    assert all(line.startswith("drop index if exists credits_ledger_") for line in down)
