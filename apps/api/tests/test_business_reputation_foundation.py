from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.ads.models import AdRecord
from app.modules.ads.presenters import ad_payload
from app.modules.businesses.models import BusinessRecord
from app.modules.businesses.presenters import business_payload
from app.modules.businesses.reputation import (
    calculate_reputation_tier,
    calculate_success_rate,
)


ROOT = Path(__file__).resolve().parents[3]


def _business(**overrides: object) -> BusinessRecord:
    values: dict[str, object] = {
        "id": "business-reputation-test",
        "owner_user_id": "owner-reputation-test",
        "business_name": "Casa Reputation",
        "rif": None,
        "address": None,
        "phone": None,
        "verification_status": "approved",
        "trust_level": "plus",
        "risk_level": "under_review",
    }
    values.update(overrides)
    return BusinessRecord(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("completed", "ratings", "rating_avg", "success_rate", "expected"),
    [
        (0, 0, None, None, "new"),
        (4, 30, Decimal("5.00"), Decimal("100.00"), "new"),
        (5, 2, Decimal("5.00"), Decimal("100.00"), "new"),
        (5, 3, Decimal("4.00"), Decimal("90.00"), "active"),
        (25, 10, Decimal("4.20"), Decimal("95.00"), "reliable"),
        (100, 30, Decimal("4.50"), Decimal("97.00"), "elite"),
        (100, 30, Decimal("4.49"), Decimal("100.00"), "reliable"),
    ],
)
def test_reputation_tiers_require_every_approved_minimum(
    completed: int,
    ratings: int,
    rating_avg: Decimal | None,
    success_rate: Decimal | None,
    expected: str,
) -> None:
    assert (
        calculate_reputation_tier(
            completed_orders_count=completed,
            ratings_count=ratings,
            rating_avg=rating_avg,
            success_rate=success_rate,
        )
        == expected
    )


def test_reputation_calculation_does_not_modify_trust_level() -> None:
    business = _business(trust_level="pro")

    tier = calculate_reputation_tier(
        completed_orders_count=100,
        ratings_count=30,
        rating_avg=Decimal("4.50"),
        success_rate=Decimal("97.00"),
    )

    assert tier == "elite"
    assert business.trust_level == "pro"


def test_success_rate_is_backend_decimal_and_has_safe_empty_state() -> None:
    assert calculate_success_rate(completed_orders_count=0, business_failure_orders_count=0) is None
    assert calculate_success_rate(completed_orders_count=97, business_failure_orders_count=3) == Decimal("97.00")
    assert calculate_success_rate(completed_orders_count=1, business_failure_orders_count=2) == Decimal("33.33")


def test_marketplace_business_dto_exposes_reputation_without_internal_controls() -> None:
    business = _business(
        reputation_tier="reliable",
        rating_avg=Decimal("4.35"),
        ratings_count=12,
        completed_orders_count=31,
        business_failure_orders_count=1,
        success_rate=Decimal("96.88"),
        average_delivery_seconds=540,
    )
    ad = AdRecord(
        id="ad-reputation-test",
        business_id=business.id,
        payment_method_id="payment-method-test",
        payment_method="zelle",
        delivery_method="pago_movil_ve",
        rate_bs_per_usd=Decimal("40.00"),
        amount_min_usd=Decimal("20.00"),
        amount_max_usd=Decimal("100.00"),
        required_credits=1,
        status="active",
        credit_hold_ledger_id=None,
        credit_consumed_ledger_id=None,
        created_at=business.created_at,
        updated_at=business.updated_at,
        activated_at=business.created_at,
        expires_at=None,
        last_rate_updated_at=None,
    )

    payload = ad_payload(ad, business=business)
    public_business = payload["business"]

    assert "risk_level" not in public_business
    assert "trust_level" not in public_business
    assert "business_failure_orders_count" not in public_business
    assert "lost_disputes_count" not in public_business
    assert public_business["reputation"] == {
        "tier": "reliable",
        "label": "Confiable",
        "rating_avg": "4.35",
        "ratings_count": 12,
        "completed_orders_count": 31,
        "success_rate": "96.88",
        "average_delivery_seconds": 540,
    }


def test_business_and_admin_dtos_have_distinct_internal_visibility() -> None:
    business = _business(reputation_tier="active", ratings_count=4, completed_orders_count=6)

    own_payload = business_payload(business)
    admin_payload = business_payload(business, admin=True)

    assert own_payload["trust_level"] == "plus"
    assert "risk_level" not in own_payload
    assert own_payload["reputation"]["tier"] == "active"
    assert admin_payload["trust_level"] == "plus"
    assert admin_payload["risk_level"] == "under_review"
    assert admin_payload["reputation"]["business_failure_orders_count"] == 0


def test_reputation_migration_is_reversible_and_has_no_text_review_fields() -> None:
    up = (ROOT / "database" / "migrations" / "0033_business_reputation_foundation.up.sql").read_text(encoding="utf-8")
    down = (ROOT / "database" / "migrations" / "0033_business_reputation_foundation.down.sql").read_text(encoding="utf-8")
    rating_table = up.split("create table if not exists ratings", 1)[1].split(");", 1)[0]

    assert "add column if not exists reputation_tier" in up
    assert "constraint ratings_stars_check" in rating_table
    assert "unique" in rating_table and "order_id" in rating_table
    assert not re.search(r"\b(comment|review_title|review_body)\b", rating_table)
    assert "drop table if exists ratings" in down
    assert "drop column if exists reputation_tier" in down
    assert "drop column if exists trust_level" not in down
    assert "drop column if exists risk_level" not in down


def test_frontend_does_not_calculate_success_rate_or_receive_marketplace_risk() -> None:
    frontend_files = [
        *sorted((ROOT / "apps" / "web" / "src").rglob("*.ts")),
        *sorted((ROOT / "apps" / "web" / "src").rglob("*.tsx")),
    ]
    frontend = "\n".join(path.read_text(encoding="utf-8") for path in frontend_files)
    marketplace_types = (ROOT / "apps" / "web" / "src" / "types" / "ads.ts").read_text(encoding="utf-8")

    for forbidden in ("calculateSuccessRate", "computeSuccessRate", "calculateReputationTier", "computeReputationTier"):
        assert forbidden not in frontend
    assert "risk_level" not in marketplace_types
    assert "trust_level" not in marketplace_types
    assert "business_failure_orders_count" not in frontend
