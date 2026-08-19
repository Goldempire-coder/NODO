from __future__ import annotations

from typing import Any

from app.shared.keyset_pagination import decode_keyset_cursor, encode_keyset_cursor


def _like_contains(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class PostgresAdminBusinessesMixin:
    def list_businesses(
        self,
        *,
        verification_status: str | None,
        risk_level: str | None,
        business_id: str | None,
        business_name: str | None,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], str | None]:
        sql = "select id, business_name, verification_status, risk_level, trust_level, created_at from businesses where true"
        params: list[Any] = []
        if verification_status:
            sql += " and verification_status = %s"
            params.append(verification_status)
        if risk_level:
            sql += " and risk_level = %s"
            params.append(risk_level)
        if business_id:
            sql += " and id = %s"
            params.append(business_id)
        if business_name:
            sql += " and business_name ilike %s escape E'\\\\'"
            params.append(_like_contains(business_name))
        if cursor:
            position = decode_keyset_cursor(cursor)
            sql += " and (created_at, id) < (%s, %s::uuid)"
            params.extend((position.timestamp, position.item_id))
        sql += " order by created_at desc, id desc limit %s"
        params.append(limit + 1)
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(sql, params).fetchall()
        page = rows[:limit]
        next_cursor = encode_keyset_cursor(page[-1]["created_at"], str(page[-1]["id"])) if len(rows) > limit else None
        return [dict(row) | {"id": str(row["id"]), "created_at": row["created_at"].isoformat()} for row in page], next_cursor

    def get_business(self, business_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                select id, owner_user_id, business_name, country, verification_status, risk_level,
                       trust_level, min_order_amount_usd, max_order_amount_usd, daily_limit_usd,
                       active_order_limit, completed_orders_count,
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
        data["min_order_amount_usd"] = str(row["min_order_amount_usd"])
        data["max_order_amount_usd"] = str(row["max_order_amount_usd"])
        data["daily_limit_usd"] = str(row["daily_limit_usd"])
        data["created_at"] = row["created_at"].isoformat()
        data["updated_at"] = row["updated_at"].isoformat()
        return data
