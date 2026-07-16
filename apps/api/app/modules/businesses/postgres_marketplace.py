from __future__ import annotations


class PostgresBusinessMarketplaceMixin:
    def list_marketplace_eligible_business_ids(self) -> set[str]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(
                """
                select id from businesses
                where verification_status = 'approved'
                  and risk_level not in ('restricted', 'high_risk')
                  and is_accepting_orders = true
                """
            ).fetchall()
        return {str(row["id"]) for row in rows}
