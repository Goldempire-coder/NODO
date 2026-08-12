from __future__ import annotations

from typing import Any

from app.modules.admin.presenters import iso
from app.shared.keyset_pagination import decode_keyset_cursor, encode_keyset_cursor


class PostgresAdminOrdersMixin:
    def list_orders(self, *, status: str | None, business_id: str | None, remitter_user_id: str | None, cursor: str | None, limit: int) -> tuple[list[dict[str, Any]], str | None]:
        sql = """
            select id, public_order_code, status, business_id, remitter_user_id, amount_usd,
                   amount_bs_calculated, payment_method_snapshot, delivery_method_snapshot,
                   paid_reported_at, payment_confirmed_at, delivered_at, completed_at, created_at
            from orders where true
        """
        params: list[Any] = []
        for column, value in (("status", status), ("business_id", business_id), ("remitter_user_id", remitter_user_id)):
            if value:
                sql += f" and {column} = %s"
                params.append(value)
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
        return [self._pg_order_summary(row) for row in page], next_cursor

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                select id, public_order_code, status, business_id, remitter_user_id, amount_usd,
                       amount_bs_calculated, payment_method_snapshot, delivery_method_snapshot,
                       paid_reported_at, payment_confirmed_at, delivered_at, completed_at, created_at
                from orders where id = %s
                """,
                (order_id,),
            ).fetchone()
            if not row:
                return None
            report = conn.execute(
                """
                select id, status, payment_type, payment_amount, proof_file_id, created_at
                from payment_reports where order_id = %s order by created_at desc limit 1
                """,
                (order_id,),
            ).fetchone()
            events = conn.execute(
                """
                select event_type, from_status, to_status, reason, created_at
                from order_state_events where order_id = %s order by created_at asc
                """,
                (order_id,),
            ).fetchall()
        return {
            "order": self._pg_order_summary(row),
            "payment_report": {
                "id": str(report["id"]),
                "status": report["status"],
                "payment_type": report["payment_type"],
                "payment_amount": str(report["payment_amount"]),
                "proof_file_id": str(report["proof_file_id"]) if report["proof_file_id"] else None,
                "created_at": report["created_at"].isoformat(),
            }
            if report
            else None,
            "timeline": [
                {
                    "event_type": event["event_type"],
                    "from_status": event["from_status"],
                    "to_status": event["to_status"],
                    "reason": event["reason"],
                    "created_at": event["created_at"].isoformat(),
                }
                for event in events
            ],
        }

    def _pg_order_summary(self, row) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        return {
            "id": str(row["id"]),
            "public_order_code": row["public_order_code"],
            "status": row["status"],
            "business_id": str(row["business_id"]),
            "remitter_user_id": str(row["remitter_user_id"]),
            "amount_usd": str(row["amount_usd"]),
            "amount_bs_calculated": str(row["amount_bs_calculated"]),
            "payment_method_snapshot": row["payment_method_snapshot"],
            "delivery_method_snapshot": row["delivery_method_snapshot"],
            "paid_reported_at": iso(row["paid_reported_at"]),
            "payment_confirmed_at": iso(row["payment_confirmed_at"]),
            "delivered_at": iso(row["delivered_at"]),
            "completed_at": iso(row["completed_at"]),
            "created_at": row["created_at"].isoformat(),
            "capabilities": {"admin_can_view": True},
        }
