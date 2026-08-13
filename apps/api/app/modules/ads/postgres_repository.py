from __future__ import annotations

import time
from decimal import Decimal

from app.core.errors import ApiError
from app.modules.ads.active_guard import require_active_ad_candidate
from app.modules.ads.marketplace_pagination import decode_marketplace_cursor, encode_marketplace_cursor
from app.modules.ads.models import AdRecord
from app.modules.ads.publication_access import require_ad_publication_access
from app.modules.ads.postgres_credit_holds import PostgresAdCreditHoldsMixin
from app.modules.ads.postgres_publish import PostgresAdPublishMixin
from app.modules.ads.postgres_wallets import PostgresAdWalletsMixin
from app.modules.ads.row_mappers import ad_from_row
from app.modules.businesses.models import BusinessRecord
from app.modules.businesses.row_mappers import business_from_row
from app.shared.db.connection import pooled_connect
from app.shared.profiling import current_profile, profile_mark


class PostgresAdRepository(PostgresAdWalletsMixin, PostgresAdCreditHoldsMixin, PostgresAdPublishMixin):
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def get_ad(self, ad_id: str) -> AdRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from ads where id = %s", (ad_id,)).fetchone()
        return ad_from_row(row) if row else None

    def _lock_declared_capacity_for_active_ad(self, conn, *, business_id: str) -> Decimal:  # type: ignore[no-untyped-def]
        conn.execute(
            """
            insert into business_capacity (
                business_id, declared_available_capacity_usd, created_at, updated_at
            )
            values (%s, 0.00, now(), now())
            on conflict (business_id) do nothing
            """,
            (business_id,),
        )
        row = conn.execute(
            """
            select declared_available_capacity_usd
            from business_capacity
            where business_id = %s
            for update
            """,
            (business_id,),
        ).fetchone()
        return Decimal(str(row["declared_available_capacity_usd"]))

    def _require_active_candidate_in_transaction(
        self,
        conn,
        *,
        business_id: str,
        payment_method: str,
        amount_max_usd: Decimal,
        exclude_ad_id: str | None = None,
        enforce_publication_access: bool = False,
    ) -> None:  # type: ignore[no-untyped-def]
        declared = self._lock_declared_capacity_for_active_ad(
            conn,
            business_id=business_id,
        )
        if enforce_publication_access:
            self._require_business_publication_access_in_transaction(
                conn,
                business_id=business_id,
            )
        sql = """
            select
                count(*) filter (where status = 'active') as active_count,
                count(*) filter (
                    where payment_method = %s and status in ('active', 'in_order')
                ) as active_method_count,
                coalesce(sum(amount_max_usd) filter (
                    where status in ('active', 'in_order')
                ), 0.00) as committed_max_total
            from ads
            where business_id = %s
        """
        params: list[object] = [payment_method, business_id]
        if exclude_ad_id is not None:
            sql += " and id <> %s"
            params.append(exclude_ad_id)
        row = conn.execute(sql, params).fetchone()
        require_active_ad_candidate(
            active_count=int(row["active_count"]),
            active_method_count=int(row["active_method_count"]),
            committed_max_total_usd=Decimal(str(row["committed_max_total"])),
            candidate_max_usd=amount_max_usd,
            declared_available_capacity_usd=declared,
        )

    def _require_business_publication_access_in_transaction(
        self,
        conn,
        *,
        business_id: str,
    ) -> None:  # type: ignore[no-untyped-def]
        row = conn.execute(
            "select businesses.*, now() as database_now from businesses where id = %s for update",
            (business_id,),
        ).fetchone()
        if row is None:
            raise ApiError("BUSINESS_NOT_FOUND", status_code=404)
        hold = conn.execute(
            """
            select exists(
                select 1 from business_publication_holds
                where business_id = %s and status = 'active'
            ) as active
            """,
            (business_id,),
        ).fetchone()
        require_ad_publication_access(
            business_from_row(row),
            current_time=row["database_now"],
            has_active_operational_hold=bool(hold["active"]),
        )

    def has_overlapping_ad(
        self,
        *,
        business_id: str,
        payment_method: str,
        delivery_method: str,
        amount_min_usd: Decimal,
        amount_max_usd: Decimal,
        exclude_ad_id: str | None = None,
    ) -> bool:
        sql = """
            select 1 from ads
            where business_id = %s
              and payment_method = %s
              and delivery_method = %s
              and status in ('active', 'paused')
              and amount_min_usd <= %s
              and amount_max_usd >= %s
        """
        params: list[object] = [business_id, payment_method, delivery_method, amount_max_usd, amount_min_usd]
        if exclude_ad_id:
            sql += " and id <> %s"
            params.append(exclude_ad_id)
        sql += " limit 1"
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return row is not None

    def business_open_exposure_usd(self, *, business_id: str, exclude_ad_id: str | None = None) -> Decimal:
        sql = """
            select coalesce(sum(amount_max_usd), 0) as open_exposure
            from ads
            where business_id = %s
              and status in ('active', 'in_order')
        """
        params: list[object] = [business_id]
        if exclude_ad_id:
            sql += " and id <> %s"
            params.append(exclude_ad_id)
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return Decimal(str(row["open_exposure"])) if row else Decimal("0.00")

    def update_ad(
        self,
        ad: AdRecord,
        *,
        payment_method_id: str | None,
        rate_bs_per_usd: Decimal | None,
        amount_min_usd: Decimal | None,
        amount_max_usd: Decimal | None,
    ) -> AdRecord:
        updates: dict[str, object] = {}
        if payment_method_id is not None:
            updates["payment_method_id"] = payment_method_id
        if rate_bs_per_usd is not None:
            updates["rate_bs_per_usd"] = rate_bs_per_usd
            updates["last_rate_updated_at"] = "now()"
        if amount_min_usd is not None:
            updates["amount_min_usd"] = amount_min_usd
        if amount_max_usd is not None:
            updates["amount_max_usd"] = amount_max_usd
        if not updates:
            return ad
        assignments: list[str] = []
        params: list[object] = []
        for key, value in updates.items():
            if value == "now()":
                assignments.append(f"{key} = now()")
            else:
                assignments.append(f"{key} = %s")
                params.append(value)
        params.append(ad.id)
        with self._connect() as conn:
            self._lock_declared_capacity_for_active_ad(conn, business_id=ad.business_id)
            current_row = conn.execute(
                "select * from ads where id = %s for update",
                (ad.id,),
            ).fetchone()
            current = ad_from_row(current_row)
            if current.status == "active":
                self._require_active_candidate_in_transaction(
                    conn,
                    business_id=current.business_id,
                    payment_method=current.payment_method,
                    amount_max_usd=(
                        amount_max_usd
                        if amount_max_usd is not None
                        else current.amount_max_usd
                    ),
                    exclude_ad_id=current.id,
                )
            row = conn.execute(f"update ads set {', '.join(assignments)}, updated_at = now() where id = %s returning *", params).fetchone()
            conn.commit()
        return ad_from_row(row)

    def set_status(
        self,
        ad: AdRecord,
        status: str,
        *,
        enforce_publication_access: bool = False,
    ) -> AdRecord:
        with self._connect() as conn:
            if status == "active":
                self._lock_declared_capacity_for_active_ad(
                    conn,
                    business_id=ad.business_id,
                )
                current_row = conn.execute(
                    "select * from ads where id = %s for update",
                    (ad.id,),
                ).fetchone()
                current = ad_from_row(current_row)
                self._require_active_candidate_in_transaction(
                    conn,
                    business_id=current.business_id,
                    payment_method=current.payment_method,
                    amount_max_usd=current.amount_max_usd,
                    exclude_ad_id=current.id,
                    enforce_publication_access=enforce_publication_access,
                )
            row = conn.execute(
                "update ads set status = %s, updated_at = now() where id = %s returning *",
                (status, ad.id),
            ).fetchone()
            conn.commit()
        return ad_from_row(row)

    def list_marketplace_ads(
        self,
        *,
        amount_usd: Decimal | None,
        payment_method: str | None,
        delivery_method: str | None,
        eligible_business_ids: set[str],
        cursor: str | None,
        limit: int,
    ) -> tuple[list[AdRecord], str | None]:
        if not eligible_business_ids:
            return [], None
        sql = """
            select ads.* from ads
            join business_payment_methods on business_payment_methods.id = ads.payment_method_id
            where ads.business_id = any(%s)
              and ads.status = 'active'
              and ads.expires_at > now()
              and not exists (
                  select 1 from business_publication_holds publication_hold
                  where publication_hold.business_id = ads.business_id
                    and publication_hold.status = 'active'
              )
              and business_payment_methods.business_id = ads.business_id
              and business_payment_methods.verified_status = 'approved'
              and business_payment_methods.active = true
        """
        params: list[object] = [list(eligible_business_ids)]
        if payment_method is not None:
            sql += " and payment_method = %s"
            params.append(payment_method)
        if delivery_method is not None:
            sql += " and delivery_method = %s"
            params.append(delivery_method)
        if amount_usd is not None:
            sql += " and amount_min_usd <= %s and amount_max_usd >= %s"
            params.extend([amount_usd, amount_usd])
        if cursor:
            position = decode_marketplace_cursor(cursor)
            sql += " and (ads.rate_bs_per_usd, ads.created_at, ads.id) < (%s, %s, %s::uuid)"
            params.extend([position.rate, position.created_at, position.ad_id])
        sql += " order by ads.rate_bs_per_usd desc, ads.created_at desc, ads.id desc limit %s"
        params.append(limit + 1)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        items = [ad_from_row(row) for row in rows[:limit]]
        return items, encode_marketplace_cursor(items[-1]) if len(rows) > limit else None

    def list_marketplace_ads_for_marketplace(
        self,
        *,
        amount_usd: Decimal | None,
        payment_method: str | None,
        delivery_method: str | None,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[AdRecord], str | None]:
        sql = """
            select ads.*
            from ads
            join businesses on businesses.id = ads.business_id
            join business_payment_methods on business_payment_methods.id = ads.payment_method_id
            left join business_capacity capacity on capacity.business_id = businesses.id
            left join lateral (
                select
                    coalesce(sum(amount_usd) filter (where status = 'reserved'), 0.00) as reserved,
                    coalesce(sum(amount_usd) filter (
                        where status = 'consumed'
                          and consumed_at >=
                              date_trunc('day', now() at time zone 'UTC') at time zone 'UTC'
                          and consumed_at <
                              (
                                  date_trunc('day', now() at time zone 'UTC')
                                  + interval '1 day'
                              ) at time zone 'UTC'
                    ), 0.00) as daily_consumed
                from business_capacity_reservations
                where business_id = businesses.id
            ) capacity_totals on true
            where ads.status = 'active'
              and ads.expires_at > now()
              and businesses.verification_status = 'approved'
              and businesses.risk_level not in ('restricted', 'high_risk')
              and businesses.is_accepting_orders = true
              and (
                  businesses.ad_publication_paused_until is null
                  or businesses.ad_publication_paused_until <= now()
              )
              and not exists (
                  select 1 from business_publication_holds publication_hold
                  where publication_hold.business_id = businesses.id
                    and publication_hold.status = 'active'
              )
              and business_payment_methods.business_id = ads.business_id
              and business_payment_methods.verified_status = 'approved'
              and business_payment_methods.active = true
              and (
                  coalesce(capacity.declared_available_capacity_usd, 0.00)
                  - coalesce(capacity_totals.reserved, 0.00)
              ) >= businesses.min_order_amount_usd
              and (
                  businesses.daily_limit_usd
                  - coalesce(capacity_totals.reserved, 0.00)
                  - coalesce(capacity_totals.daily_consumed, 0.00)
              ) >= businesses.min_order_amount_usd
        """
        params: list[object] = []
        if payment_method is not None:
            sql += " and ads.payment_method = %s"
            params.append(payment_method)
        if delivery_method is not None:
            sql += " and ads.delivery_method = %s"
            params.append(delivery_method)
        if amount_usd is not None:
            sql += " and ads.amount_min_usd <= %s and ads.amount_max_usd >= %s"
            params.extend([amount_usd, amount_usd])
        if cursor:
            position = decode_marketplace_cursor(cursor)
            sql += " and (ads.rate_bs_per_usd, ads.created_at, ads.id) < (%s, %s, %s::uuid)"
            params.extend([position.rate, position.created_at, position.ad_id])
        sql += " order by ads.rate_bs_per_usd desc, ads.created_at desc, ads.id desc limit %s"
        params.append(limit + 1)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        items = [ad_from_row(row) for row in rows[:limit]]
        return items, encode_marketplace_cursor(items[-1]) if len(rows) > limit else None

    def list_marketplace_ads_with_businesses(
        self,
        *,
        amount_usd: Decimal | None,
        payment_method: str | None,
        delivery_method: str | None,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[tuple[AdRecord, BusinessRecord]], str | None]:
        sql = """
            select
                ads.*,
                businesses.id as business_join_id,
                businesses.owner_user_id as business_owner_user_id,
                businesses.business_name as business_business_name,
                businesses.rif as business_rif,
                businesses.address as business_address,
                businesses.phone as business_phone,
                businesses.country as business_country,
                businesses.verification_status as business_verification_status,
                businesses.trust_level as business_trust_level,
                businesses.risk_level as business_risk_level,
                businesses.min_order_amount_usd as business_min_order_amount_usd,
                businesses.max_order_amount_usd as business_max_order_amount_usd,
                businesses.daily_limit_usd as business_daily_limit_usd,
                businesses.active_order_limit as business_active_order_limit,
                businesses.is_accepting_orders as business_is_accepting_orders,
                businesses.ad_publication_paused_until as business_ad_publication_paused_until,
                businesses.rating_avg as business_rating_avg,
                businesses.ratings_count as business_ratings_count,
                businesses.completed_orders_count as business_completed_orders_count,
                businesses.business_failure_orders_count as business_business_failure_orders_count,
                businesses.lost_disputes_count as business_lost_disputes_count,
                businesses.disputes_count as business_disputes_count,
                businesses.success_rate as business_success_rate,
                businesses.average_delivery_seconds as business_average_delivery_seconds,
                businesses.reputation_tier as business_reputation_tier,
                businesses.reputation_calculated_at as business_reputation_calculated_at,
                reputation_snapshot.rating_avg as business_public_reputation_rating_avg,
                reputation_snapshot.ratings_count as business_public_reputation_ratings_count,
                reputation_snapshot.reputation_tier as business_public_reputation_tier,
                reputation_snapshot.published_at as business_public_reputation_published_at,
                reputation_snapshot.source_calculated_at as business_public_reputation_source_calculated_at,
                businesses.evasion_reports_count as business_evasion_reports_count,
                businesses.referral_code as business_referral_code,
                businesses.referral_credits_earned as business_referral_credits_earned,
                businesses.founder_status as business_founder_status,
                businesses.founder_started_at as business_founder_started_at,
                businesses.founder_expires_at as business_founder_expires_at,
                businesses.created_at as business_created_at,
                businesses.updated_at as business_updated_at,
                businesses.approved_at as business_approved_at
            from ads
            join businesses on businesses.id = ads.business_id
            join business_payment_methods on business_payment_methods.id = ads.payment_method_id
            left join business_public_reputation_snapshots reputation_snapshot
              on reputation_snapshot.business_id = businesses.id
            left join business_capacity capacity on capacity.business_id = businesses.id
            left join lateral (
                select
                    coalesce(sum(amount_usd) filter (where status = 'reserved'), 0.00) as reserved,
                    coalesce(sum(amount_usd) filter (
                        where status = 'consumed'
                          and consumed_at >=
                              date_trunc('day', now() at time zone 'UTC') at time zone 'UTC'
                          and consumed_at <
                              (
                                  date_trunc('day', now() at time zone 'UTC')
                                  + interval '1 day'
                              ) at time zone 'UTC'
                    ), 0.00) as daily_consumed
                from business_capacity_reservations
                where business_id = businesses.id
            ) capacity_totals on true
            where ads.status = 'active'
              and ads.expires_at > now()
              and businesses.verification_status = 'approved'
              and businesses.risk_level not in ('restricted', 'high_risk')
              and businesses.is_accepting_orders = true
              and (
                  businesses.ad_publication_paused_until is null
                  or businesses.ad_publication_paused_until <= now()
              )
              and not exists (
                  select 1 from business_publication_holds publication_hold
                  where publication_hold.business_id = businesses.id
                    and publication_hold.status = 'active'
              )
              and business_payment_methods.business_id = ads.business_id
              and business_payment_methods.verified_status = 'approved'
              and business_payment_methods.active = true
              and (
                  coalesce(capacity.declared_available_capacity_usd, 0.00)
                  - coalesce(capacity_totals.reserved, 0.00)
              ) >= businesses.min_order_amount_usd
              and (
                  businesses.daily_limit_usd
                  - coalesce(capacity_totals.reserved, 0.00)
                  - coalesce(capacity_totals.daily_consumed, 0.00)
              ) >= businesses.min_order_amount_usd
        """
        params: list[object] = []
        if payment_method is not None:
            sql += " and ads.payment_method = %s"
            params.append(payment_method)
        if delivery_method is not None:
            sql += " and ads.delivery_method = %s"
            params.append(delivery_method)
        if amount_usd is not None:
            sql += """
                and ads.amount_min_usd <= %s
                and ads.amount_max_usd >= %s
                and (
                    coalesce(capacity.declared_available_capacity_usd, 0.00)
                    - coalesce(capacity_totals.reserved, 0.00)
                ) >= %s
                and (
                    businesses.daily_limit_usd
                    - coalesce(capacity_totals.reserved, 0.00)
                    - coalesce(capacity_totals.daily_consumed, 0.00)
                ) >= %s
            """
            params.extend([amount_usd, amount_usd, amount_usd, amount_usd])
        if cursor:
            position = decode_marketplace_cursor(cursor)
            sql += " and (ads.rate_bs_per_usd, ads.created_at, ads.id) < (%s, %s, %s::uuid)"
            params.extend([position.rate, position.created_at, position.ad_id])
        sql += " order by ads.rate_bs_per_usd desc, ads.created_at desc, ads.id desc limit %s"
        params.append(limit + 1)
        with self._connect() as conn:
            started = time.perf_counter()
            rows = conn.execute(sql, params).fetchall()
            profile_mark(current_profile(), "db:query:list_marketplace_ads_with_businesses", started)
        started = time.perf_counter()
        items = [(ad_from_row(row), _business_from_marketplace_row(row)) for row in rows[:limit]]
        profile_mark(current_profile(), "db:row_map:list_marketplace_ads_with_businesses", started)
        ads = [ad for ad, _business in items]
        return items, encode_marketplace_cursor(ads[-1]) if len(rows) > limit else None

    def list_business_ads(self, *, business_id: str, archived: bool, cursor: str | None, limit: int) -> tuple[list[AdRecord], str | None]:
        statuses = ("archived", "expired") if archived else ("active", "paused", "in_order", "suspended")
        sql = "select * from ads where business_id = %s and status = any(%s)"
        params: list[object] = [business_id, list(statuses)]
        if cursor:
            sql += " and created_at < %s"
            params.append(cursor)
        sql += " order by created_at desc limit %s"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        items = [ad_from_row(row) for row in rows]
        return items, items[-1].created_at.isoformat() if len(items) == limit else None

    def list_expirable_ads(self, *, limit: int) -> list[AdRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select * from ads
                where status in ('active', 'paused')
                  and expires_at is not null
                  and expires_at <= now()
                order by expires_at asc
                limit %s
                """,
                (limit,),
            ).fetchall()
        return [ad_from_row(row) for row in rows]


def _business_from_marketplace_row(row) -> BusinessRecord:  # type: ignore[no-untyped-def]
    return BusinessRecord(
        id=str(row["business_join_id"]),
        owner_user_id=str(row["business_owner_user_id"]),
        business_name=row["business_business_name"],
        rif=row["business_rif"],
        address=row["business_address"],
        phone=row["business_phone"],
        country=row["business_country"],
        verification_status=row["business_verification_status"],
        trust_level=row["business_trust_level"],
        risk_level=row["business_risk_level"],
        min_order_amount_usd=Decimal(str(row["business_min_order_amount_usd"])),
        max_order_amount_usd=Decimal(str(row["business_max_order_amount_usd"])),
        daily_limit_usd=Decimal(str(row["business_daily_limit_usd"])),
        active_order_limit=row["business_active_order_limit"],
        is_accepting_orders=bool(row["business_is_accepting_orders"]),
        ad_publication_paused_until=row["business_ad_publication_paused_until"],
        rating_avg=Decimal(str(row["business_rating_avg"])) if row["business_rating_avg"] is not None else None,
        ratings_count=row["business_ratings_count"],
        completed_orders_count=row["business_completed_orders_count"],
        business_failure_orders_count=row["business_business_failure_orders_count"],
        lost_disputes_count=row["business_lost_disputes_count"],
        disputes_count=row["business_disputes_count"],
        success_rate=Decimal(str(row["business_success_rate"])) if row["business_success_rate"] is not None else None,
        average_delivery_seconds=row["business_average_delivery_seconds"],
        reputation_tier=row["business_reputation_tier"],
        reputation_calculated_at=row["business_reputation_calculated_at"],
        public_reputation_rating_avg=(
            Decimal(str(row["business_public_reputation_rating_avg"]))
            if row["business_public_reputation_rating_avg"] is not None
            else None
        ),
        public_reputation_ratings_count=row["business_public_reputation_ratings_count"],
        public_reputation_tier=row["business_public_reputation_tier"],
        public_reputation_published_at=row["business_public_reputation_published_at"],
        public_reputation_source_calculated_at=row["business_public_reputation_source_calculated_at"],
        evasion_reports_count=row["business_evasion_reports_count"],
        referral_code=row["business_referral_code"],
        referral_credits_earned=row["business_referral_credits_earned"],
        founder_status=row["business_founder_status"],
        founder_started_at=row["business_founder_started_at"],
        founder_expires_at=row["business_founder_expires_at"],
        created_at=row["business_created_at"],
        updated_at=row["business_updated_at"],
        approved_at=row["business_approved_at"],
    )
