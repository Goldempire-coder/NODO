from __future__ import annotations

from typing import Any

from app.modules.orders.models import OrderRecord
from app.modules.orders.row_mappers import order_from_row


class PostgresOrderQueriesMixin:
    def list_for_remitter(self, *, remitter_user_id: str, status: str | None, cursor: str | None, limit: int) -> tuple[list[OrderRecord], str | None]:
        sql = "select * from orders where remitter_user_id = %s"
        params: list[Any] = [remitter_user_id]
        return self._query_order_page(sql=sql, params=params, status=status, cursor=cursor, limit=limit)

    def list_for_business(self, *, business_id: str, status: str | None, cursor: str | None, limit: int) -> tuple[list[OrderRecord], str | None]:
        sql = "select * from orders where business_id = %s"
        params: list[Any] = [business_id]
        return self._query_order_page(sql=sql, params=params, status=status, cursor=cursor, limit=limit)

    def list_for_business_statuses(self, *, business_id: str, statuses: set[str], cursor: str | None, limit: int) -> tuple[list[OrderRecord], str | None]:
        sql = "select * from orders where business_id = %s and status = any(%s)"
        params: list[Any] = [business_id, list(statuses)]
        return self._query_order_page(sql=sql, params=params, status=None, cursor=cursor, limit=limit)

    def list_for_remitter_statuses(self, *, remitter_user_id: str, statuses: set[str], cursor: str | None, limit: int) -> tuple[list[OrderRecord], str | None]:
        sql = "select * from orders where remitter_user_id = %s and status = any(%s)"
        params: list[Any] = [remitter_user_id, list(statuses)]
        return self._query_order_page(sql=sql, params=params, status=None, cursor=cursor, limit=limit)

    def list_attention_for_business(
        self,
        *,
        business_id: str,
        statuses: set[str],
        limit: int,
        cancel_reasons: set[str] | None = None,
    ) -> tuple[list[OrderRecord], bool]:
        if cancel_reasons:
            return self._query_attention_orders(
                sql="""
                    select * from orders
                    where business_id = %s
                      and (
                          status = any(%s)
                          or (status = 'cancelled' and cancel_reason = any(%s))
                      )
                    order by updated_at desc, id desc
                    limit %s
                """,
                params=[business_id, sorted(statuses), sorted(cancel_reasons)],
                limit=limit,
            )
        return self._query_attention_orders(
            sql="""
                select * from orders
                where business_id = %s and status = any(%s)
                order by updated_at desc, id desc
                limit %s
            """,
            params=[business_id, sorted(statuses)],
            limit=limit,
        )

    def list_attention_for_remitter(self, *, remitter_user_id: str, statuses: set[str], limit: int) -> tuple[list[OrderRecord], bool]:
        return self._query_attention_orders(
            sql="""
                select * from orders
                where remitter_user_id = %s and status = any(%s)
                order by updated_at desc, id desc
                limit %s
            """,
            params=[remitter_user_id, sorted(statuses)],
            limit=limit,
        )

    def list_job_candidate_orders(self, *, limit: int) -> list[OrderRecord]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(
                """
                select * from orders
                where status in ('waiting_payment', 'payment_reported', 'payment_confirmed', 'delivered')
                order by created_at asc
                limit %s
                """,
                (limit,),
            ).fetchall()
        return [order_from_row(row) for row in rows]

    def get_by_id_for_business(self, *, order_id: str, business_id: str) -> OrderRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                "select * from orders where id = %s and business_id = %s",
                (order_id, business_id),
            ).fetchone()
        return order_from_row(row) if row else None

    def _query_order_page(self, *, sql: str, params: list[Any], status: str | None, cursor: str | None, limit: int) -> tuple[list[OrderRecord], str | None]:
        if status:
            sql += " and status = %s"
            params.append(status)
        if cursor:
            sql += " and created_at < %s"
            params.append(cursor)
        sql += " order by created_at desc limit %s"
        params.append(limit)
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(sql, params).fetchall()
        items = [order_from_row(row) for row in rows]
        return items, items[-1].created_at.isoformat() if len(items) == limit else None

    def _query_attention_orders(self, *, sql: str, params: list[Any], limit: int) -> tuple[list[OrderRecord], bool]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(sql, [*params, limit + 1]).fetchall()
        items = [order_from_row(row) for row in rows]
        return items[:limit], len(items) > limit
