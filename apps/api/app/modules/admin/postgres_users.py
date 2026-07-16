from __future__ import annotations

from typing import Any

from app.modules.admin.user_presenters import admin_business_link_payload, admin_user_payload
from app.modules.users.row_mappers import user_from_row


class PostgresAdminUsersMixin:
    def list_users(
        self,
        *,
        phone: str | None,
        telegram_id: int | None,
        username: str | None,
        role: str | None,
        status: str | None,
        cursor: str | None,
        limit: int,
        full_sensitive: bool,
    ) -> tuple[list[dict[str, Any]], str | None]:
        sql = "select * from users where true"
        params: list[Any] = []
        if phone:
            sql += " and phone ilike %s"
            params.append(f"%{phone}%")
        if telegram_id is not None:
            sql += " and telegram_id = %s"
            params.append(telegram_id)
        if username:
            sql += " and lower(username) like lower(%s)"
            params.append(f"%{username}%")
        if role:
            sql += " and role = %s"
            params.append(role)
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
        items = [admin_user_payload(dict(row), full_sensitive=full_sensitive) for row in rows]
        next_cursor = rows[-1]["created_at"].isoformat() if len(rows) == limit else None
        return items, next_cursor

    def get_user_admin(self, user_id: str, *, full_sensitive: bool) -> dict[str, Any] | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute("select * from users where id = %s", (user_id,)).fetchone()
            if row is None:
                return None
            order_counts = conn.execute(
                """
                select
                    count(*) as total,
                    count(*) filter (where status not in ('completed', 'cancelled')) as active,
                    count(*) filter (where status = 'completed') as completed,
                    count(*) filter (where status = 'disputed') as disputed
                from orders
                where remitter_user_id = %s
                """,
                (user_id,),
            ).fetchone()
            businesses = conn.execute(
                """
                select id, business_name, verification_status, risk_level, trust_level, created_at
                from businesses
                where owner_user_id = %s
                order by created_at desc
                """,
                (user_id,),
            ).fetchall()
        payload = admin_user_payload(dict(row), full_sensitive=full_sensitive)
        payload["order_counts"] = {
            "total": int(order_counts["total"] or 0),
            "active": int(order_counts["active"] or 0),
            "completed": int(order_counts["completed"] or 0),
            "disputed": int(order_counts["disputed"] or 0),
        }
        payload["businesses"] = [
            {
                "id": str(business["id"]),
                "business_name": business["business_name"],
                "verification_status": business["verification_status"],
                "risk_level": business["risk_level"],
                "trust_level": business["trust_level"],
                "created_at": business["created_at"].isoformat(),
            }
            for business in businesses
        ]
        return payload

    def get_user_record_for_admin(self, user_id: str):
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute("select * from users where id = %s", (user_id,)).fetchone()
        return user_from_row(row) if row else None

    def set_user_status_for_admin(self, *, user_id: str, status: str):
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                "update users set status = %s, updated_at = now() where id = %s returning *",
                (status, user_id),
            ).fetchone()
            conn.commit()
        return user_from_row(row)

    def count_active_super_admins(self) -> int:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute("select count(*) as count from users where role = 'super_admin' and status = 'active'").fetchone()
        return int(row["count"])

    def list_access_links_for_business(self, *, business_id: str, full_sensitive: bool) -> list[dict[str, Any]]:
        return self._list_access_links(where_sql="l.business_id = %s", params=[business_id], full_sensitive=full_sensitive)

    def list_access_links_for_user(self, *, user_id: str, full_sensitive: bool) -> list[dict[str, Any]]:
        return self._list_access_links(where_sql="l.user_id = %s", params=[user_id], full_sensitive=full_sensitive)

    def _list_access_links(self, *, where_sql: str, params: list[Any], full_sensitive: bool) -> list[dict[str, Any]]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(
                f"""
                select
                    l.*,
                    u.username, u.first_name, u.phone, u.telegram_id as user_telegram_id,
                    u.role as user_role, u.status as user_status,
                    b.business_name, b.verification_status, b.risk_level
                from business_access_links l
                join users u on u.id = l.user_id
                join businesses b on b.id = l.business_id
                where {where_sql}
                order by l.updated_at desc
                """,
                params,
            ).fetchall()
        return [admin_business_link_payload(dict(row), full_sensitive=full_sensitive) for row in rows]
