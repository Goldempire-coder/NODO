from __future__ import annotations

from app.modules.businesses.models import BusinessAccessLinkRecord, BusinessRecord
from app.modules.businesses.row_mappers import access_link_from_row, business_from_row


class PostgresBusinessSurfaceAccessMixin:
    def get_business_with_latest_access_link_for_owner(self, owner_user_id: str) -> tuple[BusinessRecord | None, BusinessAccessLinkRecord | None]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                with latest_business as (
                    select *
                    from businesses
                    where owner_user_id = %s
                    order by created_at desc
                    limit 1
                ),
                latest_link as (
                    select l.*
                    from business_access_links l
                    join latest_business b on b.id = l.business_id
                    where l.user_id = %s
                    order by l.updated_at desc
                    limit 1
                )
                select
                    row_to_json(b) as business_json,
                    row_to_json(l) as link_json
                from latest_business b
                left join latest_link l on true
                """,
                (owner_user_id, owner_user_id),
            ).fetchone()
        if row is None or row["business_json"] is None:
            return None, None
        return business_from_row(row["business_json"]), access_link_from_row(row["link_json"]) if row["link_json"] else None
