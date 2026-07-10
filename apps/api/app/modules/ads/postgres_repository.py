from __future__ import annotations

import time
from decimal import Decimal

from app.modules.ads.models import AdRecord
from app.modules.ads.postgres_credit_holds import PostgresAdCreditHoldsMixin
from app.modules.ads.postgres_publish import PostgresAdPublishMixin
from app.modules.ads.postgres_wallets import PostgresAdWalletsMixin
from app.modules.ads.row_mappers import ad_from_row
from app.modules.businesses.models import BusinessRecord
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

    def update_ad(self, ad: AdRecord, *, rate_bs_per_usd: Decimal | None, amount_min_usd: Decimal | None, amount_max_usd: Decimal | None) -> AdRecord:
        updates: dict[str, object] = {}
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
            row = conn.execute(f"update ads set {', '.join(assignments)}, updated_at = now() where id = %s returning *", params).fetchone()
            conn.commit()
        return ad_from_row(row)

    def set_status(self, ad: AdRecord, status: str) -> AdRecord:
        with self._connect() as conn:
            row = conn.execute("update ads set status = %s, updated_at = now() where id = %s returning *", (status, ad.id)).fetchone()
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
            select * from ads
            where business_id = any(%s)
              and status = 'active'
              and expires_at > now()
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
            sql += " and created_at < %s"
            params.append(cursor)
        sql += " order by rate_bs_per_usd desc, created_at desc limit %s"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        items = [ad_from_row(row) for row in rows]
        return items, items[-1].created_at.isoformat() if len(items) == limit else None

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
            where ads.status = 'active'
              and ads.expires_at > now()
              and businesses.verification_status = 'approved'
              and businesses.risk_level not in ('restricted', 'high_risk')
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
            sql += " and ads.created_at < %s"
            params.append(cursor)
        sql += " order by ads.rate_bs_per_usd desc, ads.created_at desc limit %s"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        items = [ad_from_row(row) for row in rows]
        return items, items[-1].created_at.isoformat() if len(items) == limit else None

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
                businesses.max_order_amount_usd as business_max_order_amount_usd,
                businesses.daily_limit_usd as business_daily_limit_usd,
                businesses.active_order_limit as business_active_order_limit,
                businesses.rating_avg as business_rating_avg,
                businesses.completed_orders_count as business_completed_orders_count,
                businesses.disputes_count as business_disputes_count,
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
            where ads.status = 'active'
              and ads.expires_at > now()
              and businesses.verification_status = 'approved'
              and businesses.risk_level not in ('restricted', 'high_risk')
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
            sql += " and ads.created_at < %s"
            params.append(cursor)
        sql += " order by ads.rate_bs_per_usd desc, ads.created_at desc limit %s"
        params.append(limit)
        with self._connect() as conn:
            started = time.perf_counter()
            rows = conn.execute(sql, params).fetchall()
            profile_mark(current_profile(), "db:query:list_marketplace_ads_with_businesses", started)
        started = time.perf_counter()
        items = [(ad_from_row(row), _business_from_marketplace_row(row)) for row in rows]
        profile_mark(current_profile(), "db:row_map:list_marketplace_ads_with_businesses", started)
        ads = [ad for ad, _business in items]
        return items, ads[-1].created_at.isoformat() if len(ads) == limit else None

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
        max_order_amount_usd=Decimal(str(row["business_max_order_amount_usd"])),
        daily_limit_usd=Decimal(str(row["business_daily_limit_usd"])),
        active_order_limit=row["business_active_order_limit"],
        rating_avg=Decimal(str(row["business_rating_avg"])) if row["business_rating_avg"] is not None else None,
        completed_orders_count=row["business_completed_orders_count"],
        disputes_count=row["business_disputes_count"],
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
