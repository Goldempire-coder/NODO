from __future__ import annotations

import re
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.ads.models import AdRecord
from app.modules.ads.marketplace import AdMarketplaceMixin
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


def _ranking_ad(*, ad_id: str, business: BusinessRecord, seconds_after: int) -> AdRecord:
    created_at = business.created_at + timedelta(seconds=seconds_after)
    return AdRecord(
        id=ad_id,
        business_id=business.id,
        payment_method_id=f"payment-{ad_id}",
        payment_method="zelle",
        delivery_method="pago_movil_ve",
        rate_bs_per_usd=Decimal("40.00"),
        amount_min_usd=Decimal("20.00"),
        amount_max_usd=Decimal("100.00"),
        required_credits=1,
        status="active",
        credit_hold_ledger_id=None,
        credit_consumed_ledger_id=None,
        created_at=created_at,
        updated_at=created_at,
        activated_at=created_at,
        expires_at=None,
        last_rate_updated_at=None,
    )


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
    assert "rating_avg" not in public_business
    assert "completed_orders_count" not in public_business
    assert "business_failure_orders_count" not in public_business
    assert "lost_disputes_count" not in public_business
    assert public_business["availability"] == {
        "status": "online",
        "label": "Online",
    }
    assert public_business["reputation"] == {
        "publication_status": "withheld_pending_snapshot",
        "label": "Reputación no publicada",
    }
    assert "rating_avg" not in public_business["reputation"]
    assert "ratings_count" not in public_business["reputation"]


def test_business_and_admin_dtos_have_distinct_internal_visibility() -> None:
    business = _business(
        reputation_tier="active",
        rating_avg=Decimal("4.25"),
        ratings_count=4,
        completed_orders_count=6,
    )

    own_payload = business_payload(business)
    support_payload = business_payload(business, admin=False)
    admin_payload = business_payload(business, admin=True)

    assert own_payload["trust_level"] == "plus"
    assert "risk_level" not in own_payload
    assert own_payload["reputation"] == {
        "publication_status": "withheld_pending_snapshot",
        "label": "Reputación no publicada",
    }
    assert "rating_avg" not in own_payload["reputation"]
    assert "ratings_count" not in own_payload["reputation"]
    assert support_payload["reputation"] == own_payload["reputation"]
    assert "rating_avg" not in support_payload["reputation"]
    assert "ratings_count" not in support_payload["reputation"]
    assert admin_payload["trust_level"] == "plus"
    assert admin_payload["risk_level"] == "under_review"
    assert admin_payload["reputation"]["tier"] == "active"
    assert admin_payload["reputation"]["rating_avg"] == "4.25"
    assert admin_payload["reputation"]["ratings_count"] == 4
    assert admin_payload["reputation"]["business_failure_orders_count"] == 0


def test_public_reputation_stays_stable_when_internal_rating_aggregates_change() -> None:
    business = _business(
        reputation_tier="new",
        rating_avg=None,
        ratings_count=0,
        completed_orders_count=4,
        success_rate=Decimal("100.00"),
    )
    ad = AdRecord(
        id="ad-reputation-stability",
        business_id=business.id,
        payment_method_id="payment-method-stability",
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
    business_before = business_payload(business)["reputation"]
    marketplace_before = ad_payload(ad, business=business)["business"]["reputation"]

    business.reputation_tier = "active"
    business.rating_avg = Decimal("5.00")
    business.ratings_count = 3
    business.completed_orders_count = 5

    business_after = business_payload(business)["reputation"]
    marketplace_after = ad_payload(ad, business=business)["business"]["reputation"]

    assert business_before == business_after
    assert marketplace_before == marketplace_after
    assert business_after == {
        "publication_status": "withheld_pending_snapshot",
        "label": "Reputación no publicada",
    }


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
    business_types = (ROOT / "apps" / "web" / "src" / "types" / "business.ts").read_text(encoding="utf-8")
    marketplace_screen = (ROOT / "apps" / "web" / "src" / "screens" / "client" / "ClientMarketplaceScreens.tsx").read_text(encoding="utf-8")
    marketplace_model = (ROOT / "apps" / "web" / "src" / "hooks" / "workspace" / "useClientMarketplaceModel.ts").read_text(encoding="utf-8")
    workspace_state = (ROOT / "apps" / "web" / "src" / "hooks" / "workspace" / "useClientWorkspaceState.ts").read_text(encoding="utf-8")

    for forbidden in ("calculateSuccessRate", "computeSuccessRate", "calculateReputationTier", "computeReputationTier"):
        assert forbidden not in frontend
    assert "risk_level" not in marketplace_types
    assert "trust_level" not in marketplace_types
    assert "business_failure_orders_count" not in frontend
    assert "rating_avg" not in marketplace_types
    assert "ratings_count: number" not in marketplace_types
    assert "rating_avg" not in business_types
    assert "ratings_count: number" not in business_types
    assert "ratings_count_band" not in marketplace_types
    assert "ratings_count_band" not in business_types
    assert "withheld_pending_snapshot" in marketplace_types
    assert "withheld_pending_snapshot" in business_types
    assert "rating_avg" not in marketplace_screen
    assert "Mejor confianza" not in marketplace_screen
    assert "Más rápido" not in marketplace_screen
    assert 'sort: "rate"' in workspace_state
    assert 'prefetchActiveMarketplace(sort: "trust" | "rate" | "speed" = "rate")' in marketplace_model


def test_marketplace_ranking_does_not_use_live_rating_aggregates() -> None:
    marketplace_service = (ROOT / "apps" / "api" / "app" / "modules" / "ads" / "marketplace.py").read_text(
        encoding="utf-8"
    )
    postgres_repository = (ROOT / "apps" / "api" / "app" / "modules" / "ads" / "postgres_repository.py").read_text(
        encoding="utf-8"
    ).lower()
    memory_repository = (ROOT / "apps" / "api" / "app" / "modules" / "ads" / "memory_repository.py").read_text(
        encoding="utf-8"
    )
    rank_source = marketplace_service.split("def _rank(", 1)[1].split("def _ad_within_current_business_limits", 1)[0]

    for forbidden in (
        "rating_avg",
        "ratings_count",
        "reputation_tier",
        "trust_level",
        "completed_orders_count",
        "success_rate",
        "average_delivery_seconds",
    ):
        assert forbidden not in rank_source
        assert f"order by businesses.{forbidden}" not in postgres_repository
    assert "key=lambda ad: (ad.rate_bs_per_usd, ad.created_at)" in memory_repository
    assert "order by rate_bs_per_usd desc, created_at desc limit" in postgres_repository
    assert postgres_repository.count("order by ads.rate_bs_per_usd desc, ads.created_at desc limit") >= 2


def test_marketplace_legacy_sorts_ignore_live_reputation_and_match_rate_order() -> None:
    older_business = _business(
        id="business-older",
        trust_level="pro",
        rating_avg=Decimal("5.00"),
        ratings_count=100,
        reputation_tier="elite",
        completed_orders_count=100,
        success_rate=Decimal("100.00"),
        average_delivery_seconds=60,
    )
    newer_business = _business(
        id="business-newer",
        trust_level="new",
        rating_avg=None,
        ratings_count=0,
        reputation_tier="new",
        completed_orders_count=0,
        success_rate=None,
        average_delivery_seconds=None,
    )
    older_ad = _ranking_ad(ad_id="ad-older", business=older_business, seconds_after=0)
    newer_ad = _ranking_ad(ad_id="ad-newer", business=newer_business, seconds_after=1)
    marketplace = AdMarketplaceMixin()

    def ranked_ids(sort: str | None) -> list[str]:
        return [
            ad.id
            for ad in marketplace._rank(
                [older_ad, newer_ad],
                sort=sort,
            )
        ]

    expected = ["ad-newer", "ad-older"]
    assert ranked_ids("rate") == expected
    assert ranked_ids("trust") == expected
    assert ranked_ids("speed") == expected
    assert ranked_ids(None) == expected

    older_business.trust_level = "new"
    older_business.rating_avg = None
    older_business.ratings_count = 0
    older_business.reputation_tier = "new"
    older_business.completed_orders_count = 0
    older_business.success_rate = None
    older_business.average_delivery_seconds = None
    newer_business.trust_level = "pro"
    newer_business.rating_avg = Decimal("5.00")
    newer_business.ratings_count = 100
    newer_business.reputation_tier = "elite"
    newer_business.completed_orders_count = 100
    newer_business.success_rate = Decimal("100.00")
    newer_business.average_delivery_seconds = 60

    assert ranked_ids("trust") == expected
    assert ranked_ids("speed") == expected


def test_marketplace_cache_namespace_is_versioned_for_private_reputation_projection() -> None:
    cache_source = (ROOT / "apps" / "api" / "app" / "modules" / "ads" / "marketplace_cache.py").read_text(
        encoding="utf-8"
    )

    assert 'MARKETPLACE_CACHE_PREFIX = "marketplace:ads:v2:"' in cache_source
