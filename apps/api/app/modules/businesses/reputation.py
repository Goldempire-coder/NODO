from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Literal, NotRequired, TypedDict

from app.modules.businesses.models import BusinessRecord


ReputationTier = Literal["new", "active", "reliable", "elite"]
PublicReputationStatus = Literal["withheld_pending_snapshot", "published_snapshot"]

REPUTATION_TIER_LABELS: dict[ReputationTier, str] = {
    "new": "Nuevo",
    "active": "Activo",
    "reliable": "Reputación alta",
    "elite": "Elite",
}


class PublicBusinessReputation(TypedDict):
    publication_status: PublicReputationStatus
    label: str
    rating_avg: NotRequired[str]
    ratings_count: NotRequired[int]
    published_at: NotRequired[str]


class AdminBusinessReputation(TypedDict):
    tier: ReputationTier
    label: str
    rating_avg: str | None
    ratings_count: int
    completed_orders_count: int
    success_rate: str | None
    average_delivery_seconds: int | None
    business_failure_orders_count: int
    lost_disputes_count: int
    disputes_count: int
    calculated_at: str | None


def calculate_success_rate(*, completed_orders_count: int, business_failure_orders_count: int) -> Decimal | None:
    if completed_orders_count < 0 or business_failure_orders_count < 0:
        raise ValueError("reputation counters must be non-negative")
    denominator = completed_orders_count + business_failure_orders_count
    if denominator == 0:
        return None
    value = Decimal(completed_orders_count) * Decimal("100") / Decimal(denominator)
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_reputation_tier(
    *,
    completed_orders_count: int,
    ratings_count: int,
    rating_avg: Decimal | None,
    success_rate: Decimal | None,
) -> ReputationTier:
    if completed_orders_count < 0 or ratings_count < 0:
        raise ValueError("reputation counters must be non-negative")
    if _meets_tier(
        completed_orders_count=completed_orders_count,
        ratings_count=ratings_count,
        rating_avg=rating_avg,
        success_rate=success_rate,
        minimum_completed=100,
        minimum_ratings=30,
        minimum_rating=Decimal("4.50"),
        minimum_success_rate=Decimal("97.00"),
    ):
        return "elite"
    if _meets_tier(
        completed_orders_count=completed_orders_count,
        ratings_count=ratings_count,
        rating_avg=rating_avg,
        success_rate=success_rate,
        minimum_completed=25,
        minimum_ratings=10,
        minimum_rating=Decimal("4.20"),
        minimum_success_rate=Decimal("95.00"),
    ):
        return "reliable"
    if _meets_tier(
        completed_orders_count=completed_orders_count,
        ratings_count=ratings_count,
        rating_avg=rating_avg,
        success_rate=success_rate,
        minimum_completed=5,
        minimum_ratings=3,
        minimum_rating=Decimal("4.00"),
        minimum_success_rate=Decimal("90.00"),
    ):
        return "active"
    return "new"


def _meets_tier(
    *,
    completed_orders_count: int,
    ratings_count: int,
    rating_avg: Decimal | None,
    success_rate: Decimal | None,
    minimum_completed: int,
    minimum_ratings: int,
    minimum_rating: Decimal,
    minimum_success_rate: Decimal,
) -> bool:
    return (
        completed_orders_count >= minimum_completed
        and ratings_count >= minimum_ratings
        and rating_avg is not None
        and rating_avg >= minimum_rating
        and success_rate is not None
        and success_rate >= minimum_success_rate
    )


def public_reputation_payload(business: BusinessRecord) -> PublicBusinessReputation:
    _stored_tier(business.reputation_tier)
    if (
        business.public_reputation_rating_avg is not None
        and business.public_reputation_ratings_count is not None
        and business.public_reputation_tier is not None
        and business.public_reputation_published_at is not None
    ):
        _stored_tier(business.public_reputation_tier)
        rating_avg = _decimal_text(business.public_reputation_rating_avg)
        return {
            "publication_status": "published_snapshot",
            "label": f"{rating_avg} de 5 ({business.public_reputation_ratings_count} calificaciones)",
            "rating_avg": rating_avg,
            "ratings_count": business.public_reputation_ratings_count,
            "published_at": business.public_reputation_published_at.isoformat(),
        }
    return {
        "publication_status": "withheld_pending_snapshot",
        "label": "Reputación aún no publicada",
    }


def own_reputation_payload(business: BusinessRecord) -> PublicBusinessReputation:
    return public_reputation_payload(business)


def admin_reputation_payload(business: BusinessRecord) -> AdminBusinessReputation:
    tier = _stored_tier(business.reputation_tier)
    return {
        "tier": tier,
        "label": REPUTATION_TIER_LABELS[tier],
        "rating_avg": _decimal_text(business.rating_avg),
        "ratings_count": business.ratings_count,
        "completed_orders_count": business.completed_orders_count,
        "success_rate": _decimal_text(business.success_rate),
        "average_delivery_seconds": business.average_delivery_seconds,
        "business_failure_orders_count": business.business_failure_orders_count,
        "lost_disputes_count": business.lost_disputes_count,
        "disputes_count": business.disputes_count,
        "calculated_at": business.reputation_calculated_at.isoformat() if business.reputation_calculated_at else None,
    }


def _stored_tier(value: str) -> ReputationTier:
    if value not in REPUTATION_TIER_LABELS:
        raise ValueError("invalid stored reputation tier")
    return value  # type: ignore[return-value]


def _decimal_text(value: Decimal | None) -> str | None:
    return f"{value:.2f}" if value is not None else None
