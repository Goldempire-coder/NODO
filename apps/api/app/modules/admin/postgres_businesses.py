from __future__ import annotations

from typing import Any


class PostgresAdminBusinessesMixin:
    def list_businesses(self, *, verification_status: str | None, risk_level: str | None, cursor: str | None, limit: int) -> tuple[list[dict[str, Any]], str | None]:
        sql = "select id, business_name, verification_status, risk_level, trust_level, created_at from businesses where true"
        params: list[Any] = []
        if verification_status:
            sql += " and verification_status = %s"
            params.append(verification_status)
        if risk_level:
            sql += " and risk_level = %s"
            params.append(risk_level)
        if cursor:
            sql += " and created_at < %s"
            params.append(cursor)
        sql += " order by created_at desc limit %s"
        params.append(limit)
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) | {"id": str(row["id"]), "created_at": row["created_at"].isoformat()} for row in rows], rows[-1]["created_at"].isoformat() if len(rows) == limit else None

    def get_business(self, business_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                select id, owner_user_id, business_name, country, verification_status, risk_level,
                       trust_level, max_order_amount_usd, active_order_limit, completed_orders_count,
                       disputes_count, updated_at, created_at
                from businesses where id = %s
                """,
                (business_id,),
            ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["id"] = str(row["id"])
        data["owner_user_id"] = str(row["owner_user_id"])
        data["max_order_amount_usd"] = str(row["max_order_amount_usd"])
        data["created_at"] = row["created_at"].isoformat()
        data["updated_at"] = row["updated_at"].isoformat()
        return data
