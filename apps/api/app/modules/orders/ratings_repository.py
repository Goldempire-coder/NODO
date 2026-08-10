from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta
from threading import RLock
from typing import Any

from app.core.errors import ApiError
from app.modules.businesses.reputation import calculate_reputation_tier, calculate_success_rate
from app.modules.businesses.row_mappers import business_from_row
from app.modules.orders.models import RatingRecord, new_id, utc_now
from app.modules.orders.row_mappers import rating_from_row
from app.shared.db.connection import pooled_connect


RATING_COMPLETION_REASONS = frozenset(
    {"manual_confirmed", "auto_completed_after_24h", "admin_resolved"}
)


def _completion_allows_rating(
    *,
    status: str,
    completion_reason: str | None,
    has_open_dispute: bool,
    has_resolved_dispute: bool,
) -> bool:
    if status != "completed" or completion_reason not in RATING_COMPLETION_REASONS or has_open_dispute:
        return False
    return completion_reason != "admin_resolved" or has_resolved_dispute


def _rating_average(stars: list[int]) -> Decimal | None:
    if not stars:
        return None
    return (sum(Decimal(value) for value in stars) / Decimal(len(stars))).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _reputation_values(
    *,
    completed_orders_count: int,
    business_failure_orders_count: int,
    ratings_count: int,
    rating_avg: Decimal | None,
) -> tuple[Decimal | None, str]:
    success_rate = calculate_success_rate(
        completed_orders_count=completed_orders_count,
        business_failure_orders_count=business_failure_orders_count,
    )
    tier = calculate_reputation_tier(
        completed_orders_count=completed_orders_count,
        ratings_count=ratings_count,
        rating_avg=rating_avg,
        success_rate=success_rate,
    )
    return success_rate, tier


class InMemoryOrderRatingRepository:
    def __init__(self, *, order_repository, business_repository, dispute_repository) -> None:  # type: ignore[no-untyped-def]
        self._orders = order_repository
        self._businesses = business_repository
        self._disputes = dispute_repository
        self._lock: RLock = order_repository._lock
        self.ratings: dict[str, RatingRecord] = {}

    def get_for_order(self, order_id: str) -> RatingRecord | None:
        with self._lock:
            return self.ratings.get(order_id)

    def rating_state(self, *, order_id: str, rater_user_id: str) -> dict[str, Any]:
        with self._lock:
            rating = self.ratings.get(order_id)
            if rating is not None:
                return {"can_rate": False, "already_rated": True, "stars": rating.stars}
            order = self._orders.get_by_id(order_id)
            disputes = [item for item in self._disputes.disputes.values() if item.order_id == order_id]
            business = self._businesses.get_business(order.business_id) if order else None
            can_rate = bool(
                order
                and order.remitter_user_id == rater_user_id
                and _completion_allows_rating(
                    status=order.status,
                    completion_reason=order.completion_reason,
                    has_open_dispute=any(item.status in {"open", "in_review"} for item in disputes),
                    has_resolved_dispute=any(item.status == "resolved" for item in disputes),
                )
                and business is not None
                and business.owner_user_id != rater_user_id
            )
            return {"can_rate": can_rate, "already_rated": False, "stars": None}

    def create_for_completed_order(self, *, order_id: str, rater_user_id: str, stars: int):  # type: ignore[no-untyped-def]
        with self._lock:
            order = self._orders.get_by_id(order_id)
            if order is None or order.remitter_user_id != rater_user_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            disputes = [item for item in self._disputes.disputes.values() if item.order_id == order_id]
            if not _completion_allows_rating(
                status=order.status,
                completion_reason=order.completion_reason,
                has_open_dispute=any(item.status in {"open", "in_review"} for item in disputes),
                has_resolved_dispute=any(item.status == "resolved" for item in disputes),
            ):
                raise ApiError("RATING_NOT_ALLOWED", status_code=409)
            business = self._businesses.get_business(order.business_id)
            if business is None or business.owner_user_id == rater_user_id:
                raise ApiError("RATING_NOT_ALLOWED", status_code=409)
            if order.id in self.ratings:
                raise ApiError("RATING_ALREADY_EXISTS", status_code=409)

            rating = RatingRecord(
                id=new_id(),
                order_id=order.id,
                business_id=order.business_id,
                rater_user_id=rater_user_id,
                stars=stars,
            )
            business_ratings = [item for item in self.ratings.values() if item.business_id == business.id]
            rating_avg = _rating_average([item.stars for item in business_ratings] + [stars])
            completed_orders = [
                item for item in self._orders.orders.values() if item.business_id == business.id and item.status == "completed"
            ]
            delivery_seconds = [
                int((item.delivered_at - item.payment_confirmed_at).total_seconds())
                for item in completed_orders
                if item.payment_confirmed_at is not None
                and item.delivered_at is not None
                and item.delivered_at >= item.payment_confirmed_at
            ]
            disputes = [
                item
                for item in self._disputes.disputes.values()
                if (related_order := self._orders.get_by_id(item.order_id)) is not None
                and related_order.business_id == business.id
            ]
            lost_order_ids = {
                item.order_id
                for item in disputes
                if item.status == "resolved" and item.resolution_type == "remitter_favored"
            }
            success_rate, reputation_tier = _reputation_values(
                completed_orders_count=len(completed_orders),
                business_failure_orders_count=len(lost_order_ids),
                ratings_count=len(business_ratings) + 1,
                rating_avg=rating_avg,
            )

            calculated_at = utc_now()
            pause_candidate = calculated_at + timedelta(minutes=15)

            self.ratings[order.id] = rating
            self._businesses.extend_ad_publication_pause(
                business.id,
                pause_candidate,
            )
            business.rating_avg = rating_avg
            business.ratings_count = len(business_ratings) + 1
            business.completed_orders_count = len(completed_orders)
            business.business_failure_orders_count = len(lost_order_ids)
            business.lost_disputes_count = len(lost_order_ids)
            business.disputes_count = len(disputes)
            business.success_rate = success_rate
            business.average_delivery_seconds = int(sum(delivery_seconds) / len(delivery_seconds)) if delivery_seconds else None
            business.reputation_tier = reputation_tier
            business.reputation_calculated_at = calculated_at
            business.updated_at = business.reputation_calculated_at
            return rating, business


class PostgresOrderRatingRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def get_for_order(self, order_id: str) -> RatingRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from ratings where order_id = %s", (order_id,)).fetchone()
        return rating_from_row(row) if row else None

    def rating_state(self, *, order_id: str, rater_user_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            rating_row = conn.execute("select * from ratings where order_id = %s", (order_id,)).fetchone()
            if rating_row:
                rating = rating_from_row(rating_row)
                return {"can_rate": False, "already_rated": True, "stars": rating.stars}
            row = conn.execute(
                """
                select o.status, o.completion_reason, o.remitter_user_id, b.owner_user_id,
                       exists (
                           select 1 from disputes d
                           where d.order_id = o.id and d.status in ('open', 'in_review')
                       ) as has_open_dispute,
                       exists (
                           select 1 from disputes d
                           where d.order_id = o.id and d.status = 'resolved'
                       ) as has_resolved_dispute
                from orders o
                join businesses b on b.id = o.business_id
                where o.id = %s
                """,
                (order_id,),
            ).fetchone()
        can_rate = bool(
            row
            and str(row["remitter_user_id"]) == rater_user_id
            and str(row["owner_user_id"]) != rater_user_id
            and _completion_allows_rating(
                status=row["status"],
                completion_reason=row["completion_reason"],
                has_open_dispute=bool(row["has_open_dispute"]),
                has_resolved_dispute=bool(row["has_resolved_dispute"]),
            )
        )
        return {"can_rate": can_rate, "already_rated": False, "stars": None}

    def create_for_completed_order(self, *, order_id: str, rater_user_id: str, stars: int):  # type: ignore[no-untyped-def]
        with self._connect() as conn:
            order = conn.execute(
                "select * from orders where id = %s for update",
                (order_id,),
            ).fetchone()
            if order is None or str(order["remitter_user_id"]) != rater_user_id:
                raise ApiError("ORDER_NOT_FOUND", status_code=404)
            has_open_dispute = conn.execute(
                "select 1 from disputes where order_id = %s and status in ('open', 'in_review') limit 1",
                (order_id,),
            ).fetchone()
            has_resolved_dispute = conn.execute(
                "select 1 from disputes where order_id = %s and status = 'resolved' limit 1",
                (order_id,),
            ).fetchone()
            if not _completion_allows_rating(
                status=order["status"],
                completion_reason=order["completion_reason"],
                has_open_dispute=bool(has_open_dispute),
                has_resolved_dispute=bool(has_resolved_dispute),
            ):
                raise ApiError("RATING_NOT_ALLOWED", status_code=409)
            business = conn.execute(
                "select * from businesses where id = %s for update",
                (order["business_id"],),
            ).fetchone()
            if business is None or str(business["owner_user_id"]) == rater_user_id:
                raise ApiError("RATING_NOT_ALLOWED", status_code=409)
            if conn.execute("select 1 from ratings where order_id = %s", (order_id,)).fetchone():
                raise ApiError("RATING_ALREADY_EXISTS", status_code=409)

            rating_row = conn.execute(
                """
                insert into ratings (order_id, business_id, rater_user_id, stars, created_at)
                values (%s, %s, %s, %s, now())
                returning *
                """,
                (order_id, order["business_id"], rater_user_id, stars),
            ).fetchone()
            rating_aggregates = conn.execute(
                "select count(*) as ratings_count, round(avg(stars), 2) as rating_avg from ratings where business_id = %s",
                (order["business_id"],),
            ).fetchone()
            order_aggregates = conn.execute(
                """
                select
                    count(*) filter (where status = 'completed') as completed_orders_count,
                    avg(extract(epoch from (delivered_at - payment_confirmed_at))) filter (
                        where status = 'completed'
                          and payment_confirmed_at is not null
                          and delivered_at is not null
                          and delivered_at >= payment_confirmed_at
                    ) as average_delivery_seconds
                from orders
                where business_id = %s
                """,
                (order["business_id"],),
            ).fetchone()
            dispute_aggregates = conn.execute(
                """
                select
                    count(*) as disputes_count,
                    count(distinct d.order_id) filter (
                        where d.status = 'resolved' and d.resolution_type = 'remitter_favored'
                    ) as lost_disputes_count
                from disputes d
                join orders o on o.id = d.order_id
                where o.business_id = %s
                """,
                (order["business_id"],),
            ).fetchone()

            ratings_count = int(rating_aggregates["ratings_count"] or 0)
            rating_avg = Decimal(str(rating_aggregates["rating_avg"])) if rating_aggregates["rating_avg"] is not None else None
            completed_orders_count = int(order_aggregates["completed_orders_count"] or 0)
            lost_disputes_count = int(dispute_aggregates["lost_disputes_count"] or 0)
            success_rate, reputation_tier = _reputation_values(
                completed_orders_count=completed_orders_count,
                business_failure_orders_count=lost_disputes_count,
                ratings_count=ratings_count,
                rating_avg=rating_avg,
            )
            updated_business_row = conn.execute(
                """
                update businesses
                set rating_avg = %s,
                    ratings_count = %s,
                    completed_orders_count = %s,
                    business_failure_orders_count = %s,
                    lost_disputes_count = %s,
                    disputes_count = %s,
                    success_rate = %s,
                    average_delivery_seconds = %s,
                    reputation_tier = %s,
                    ad_publication_paused_until = greatest(
                        coalesce(ad_publication_paused_until, '-infinity'::timestamptz),
                        now() + interval '15 minutes'
                    ),
                    reputation_calculated_at = now(),
                    updated_at = now()
                where id = %s
                returning *
                """,
                (
                    rating_avg,
                    ratings_count,
                    completed_orders_count,
                    lost_disputes_count,
                    lost_disputes_count,
                    int(dispute_aggregates["disputes_count"] or 0),
                    success_rate,
                    int(order_aggregates["average_delivery_seconds"]) if order_aggregates["average_delivery_seconds"] is not None else None,
                    reputation_tier,
                    order["business_id"],
                ),
            ).fetchone()
            conn.commit()
        return rating_from_row(rating_row), business_from_row(updated_business_row)
