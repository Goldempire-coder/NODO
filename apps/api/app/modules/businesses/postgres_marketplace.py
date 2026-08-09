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
                  and (
                      ad_publication_paused_until is null
                      or ad_publication_paused_until <= now()
                  )
                  and not exists (
                      select 1 from business_publication_holds publication_hold
                      where publication_hold.business_id = businesses.id
                        and publication_hold.status = 'active'
                  )
                """
            ).fetchall()
        return {str(row["id"]) for row in rows}

    def list_marketplace_ineligible_business_ids(self, business_ids: set[str]) -> set[str]:
        if not business_ids:
            return set()
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(
                """
                select id from businesses
                where id = any(%s::uuid[])
                  and verification_status = 'approved'
                  and risk_level not in ('restricted', 'high_risk')
                  and is_accepting_orders = true
                  and (
                      ad_publication_paused_until is null
                      or ad_publication_paused_until <= now()
                  )
                  and not exists (
                      select 1 from business_publication_holds publication_hold
                      where publication_hold.business_id = businesses.id
                        and publication_hold.status = 'active'
                  )
                """,
                (list(business_ids),),
            ).fetchall()
        eligible = {str(row["id"]) for row in rows}
        return business_ids - eligible
