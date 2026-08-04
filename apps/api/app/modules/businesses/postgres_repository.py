from __future__ import annotations

from datetime import datetime, timedelta

from app.modules.businesses.models import BusinessRecord
from app.modules.businesses.postgres_access_links import PostgresBusinessAccessLinksMixin
from app.modules.businesses.postgres_admin_review import PostgresBusinessAdminReviewMixin
from app.modules.businesses.postgres_founder import PostgresBusinessFounderMixin
from app.modules.businesses.postgres_marketplace import PostgresBusinessMarketplaceMixin
from app.modules.businesses.postgres_payment_methods import PostgresBusinessPaymentMethodsMixin
from app.modules.businesses.postgres_surface_access import PostgresBusinessSurfaceAccessMixin
from app.modules.businesses.postgres_verification_assets import PostgresBusinessVerificationAssetsMixin
from app.modules.businesses.row_mappers import business_from_row
from app.shared.db.connection import pooled_connect


class PostgresBusinessRepository(
    PostgresBusinessAccessLinksMixin,
    PostgresBusinessAdminReviewMixin,
    PostgresBusinessFounderMixin,
    PostgresBusinessMarketplaceMixin,
    PostgresBusinessPaymentMethodsMixin,
    PostgresBusinessSurfaceAccessMixin,
    PostgresBusinessVerificationAssetsMixin,
):
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    @staticmethod
    def _with_public_reputation_snapshot(where_clause: str) -> str:
        return f"""
            select
                businesses.*,
                snapshots.rating_avg as public_reputation_rating_avg,
                snapshots.ratings_count as public_reputation_ratings_count,
                snapshots.reputation_tier as public_reputation_tier,
                snapshots.published_at as public_reputation_published_at,
                snapshots.source_calculated_at as public_reputation_source_calculated_at
            from businesses
            left join business_public_reputation_snapshots snapshots
              on snapshots.business_id = businesses.id
            {where_clause}
        """

    def create_business(self, *, owner_user_id: str, business_name: str, rif: str | None, address: str | None, phone: str | None, country: str) -> BusinessRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                insert into businesses (owner_user_id, business_name, rif, address, phone, country, created_at, updated_at)
                values (%s, %s, %s, %s, %s, %s, now(), now())
                returning *
                """,
                (owner_user_id, business_name, rif, address, phone, country),
            ).fetchone()
            conn.commit()
        return business_from_row(row)

    def update_business(self, business: BusinessRecord, fields: dict[str, str | None]) -> BusinessRecord:
        updates = {key: value for key, value in fields.items() if value is not None}
        if not updates:
            return business
        assignments = ", ".join(f"{key} = %s" for key in updates)
        values = [*updates.values(), business.id]
        with self._connect() as conn:
            row = conn.execute(f"update businesses set {assignments}, updated_at = now() where id = %s returning *", values).fetchone()
            conn.commit()
        return business_from_row(row)

    def update_business_accepting_orders(self, business_id: str, accepting_orders: bool) -> BusinessRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "update businesses set is_accepting_orders = %s, updated_at = now() where id = %s returning *",
                (accepting_orders, business_id),
            ).fetchone()
            conn.commit()
        return business_from_row(row) if row else None

    def get_business(self, business_id: str) -> BusinessRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                self._with_public_reputation_snapshot("where businesses.id = %s"),
                (business_id,),
            ).fetchone()
        return business_from_row(row) if row else None

    def get_businesses_by_ids(self, business_ids: set[str]) -> dict[str, BusinessRecord]:
        if not business_ids:
            return {}
        with self._connect() as conn:
            rows = conn.execute(
                self._with_public_reputation_snapshot("where businesses.id = any(%s::uuid[])"),
                (list(business_ids),),
            ).fetchall()
        businesses = [business_from_row(row) for row in rows]
        return {business.id: business for business in businesses}

    def get_active_business_for_owner(self, owner_user_id: str) -> BusinessRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                self._with_public_reputation_snapshot(
                    "where businesses.owner_user_id = %s order by businesses.created_at desc limit 1"
                ),
                (owner_user_id,),
            ).fetchone()
        return business_from_row(row) if row else None

    def publish_due_public_reputation_snapshots(
        self,
        *,
        current_time: datetime,
        limit: int,
        minimum_ratings: int = 5,
        publication_interval: timedelta = timedelta(hours=24),
        dry_run: bool = False,
    ) -> list[str]:
        cutoff = current_time - publication_interval
        select_sql = """
            select businesses.id
            from businesses
            left join business_public_reputation_snapshots snapshots
              on snapshots.business_id = businesses.id
            where businesses.ratings_count >= %s
              and businesses.rating_avg is not null
              and businesses.reputation_calculated_at is not null
              and businesses.reputation_calculated_at <= %s
              and (
                  snapshots.business_id is null
                  or (
                      snapshots.published_at <= %s
                      and businesses.reputation_calculated_at > snapshots.source_calculated_at
                  )
              )
            order by snapshots.published_at asc nulls first, businesses.id asc
            limit %s
            for update of businesses skip locked
        """
        with self._connect() as conn:
            rows = conn.execute(select_sql, (minimum_ratings, cutoff, cutoff, limit)).fetchall()
            business_ids = [str(row["id"]) for row in rows]
            if business_ids and not dry_run:
                conn.execute(
                    """
                    insert into business_public_reputation_snapshots (
                        business_id,
                        rating_avg,
                        ratings_count,
                        reputation_tier,
                        source_calculated_at,
                        published_at,
                        created_at,
                        updated_at
                    )
                    select
                        id,
                        rating_avg,
                        ratings_count,
                        reputation_tier,
                        reputation_calculated_at,
                        %s,
                        %s,
                        %s
                    from businesses
                    where id = any(%s::uuid[])
                    on conflict (business_id) do update set
                        rating_avg = excluded.rating_avg,
                        ratings_count = excluded.ratings_count,
                        reputation_tier = excluded.reputation_tier,
                        source_calculated_at = excluded.source_calculated_at,
                        published_at = excluded.published_at,
                        updated_at = excluded.updated_at
                    """,
                    (current_time, current_time, current_time, business_ids),
                )
                conn.commit()
            else:
                conn.rollback()
        return business_ids

    def list_pending_businesses(self, *, cursor: str | None, limit: int) -> tuple[list[BusinessRecord], str | None]:
        sql = "select * from businesses where verification_status = 'pending'"
        params: list[object] = []
        if cursor:
            sql += " and created_at < %s"
            params.append(cursor)
        sql += " order by created_at desc limit %s"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        items = [business_from_row(row) for row in rows]
        next_cursor = items[-1].created_at.isoformat() if len(items) == limit else None
        return items, next_cursor


