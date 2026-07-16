from __future__ import annotations

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
            row = conn.execute("select * from businesses where id = %s", (business_id,)).fetchone()
        return business_from_row(row) if row else None

    def get_businesses_by_ids(self, business_ids: set[str]) -> dict[str, BusinessRecord]:
        if not business_ids:
            return {}
        with self._connect() as conn:
            rows = conn.execute("select * from businesses where id = any(%s::uuid[])", (list(business_ids),)).fetchall()
        businesses = [business_from_row(row) for row in rows]
        return {business.id: business for business in businesses}

    def get_active_business_for_owner(self, owner_user_id: str) -> BusinessRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "select * from businesses where owner_user_id = %s order by created_at desc limit 1",
                (owner_user_id,),
            ).fetchone()
        return business_from_row(row) if row else None

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


