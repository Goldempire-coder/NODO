from __future__ import annotations

from app.modules.businesses.models import BusinessRecord
from app.modules.businesses.row_mappers import business_from_row


class PostgresBusinessFounderMixin:
    def list_expired_founder_businesses(self, *, limit: int) -> list[BusinessRecord]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(
                """
                select * from businesses
                where founder_status = 'active'
                  and founder_expires_at is not null
                  and founder_expires_at <= now()
                order by founder_expires_at asc
                limit %s
                """,
                (limit,),
            ).fetchall()
        return [business_from_row(row) for row in rows]

    def expire_founder_access(self, business: BusinessRecord) -> BusinessRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                "update businesses set founder_status = 'expired', updated_at = now() where id = %s returning *",
                (business.id,),
            ).fetchone()
            conn.commit()
        return business_from_row(row)
