from __future__ import annotations

from typing import Any


class PostgresAdminDashboardMixin:
    def dashboard(self) -> dict[str, Any]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            clients_total = conn.execute("select count(*) as c from users where role = 'remitter'").fetchone()["c"]
            clients_with_phone = conn.execute("select count(*) as c from users where role = 'remitter' and phone is not null and phone <> ''").fetchone()["c"]
            recent_contacts = conn.execute(
                """
                select id, first_name, username, phone, updated_at
                from users
                where role = 'remitter' and phone is not null and phone <> ''
                order by updated_at desc
                limit 5
                """
            ).fetchall()
            pending_businesses = conn.execute("select count(*) as c from businesses where verification_status = 'pending'").fetchone()["c"]
            pending_credit_purchases = conn.execute("select count(*) as c from credit_purchases where status = 'pending_manual_review'").fetchone()["c"]
            open_disputes = conn.execute("select count(*) as c from disputes where status in ('open', 'in_review')").fetchone()["c"]
            active_orders = conn.execute("select count(*) as c from orders where status not in ('completed', 'cancelled')").fetchone()["c"]
            disputed_orders = conn.execute("select count(*) as c from orders where status = 'disputed'").fetchone()["c"]
            delivered_orders = conn.execute("select count(*) as c from orders where status = 'delivered'").fetchone()["c"]
            under_review = conn.execute("select count(*) as c from businesses where risk_level = 'under_review'").fetchone()["c"]
        return {
            "queues": {"pending_businesses": pending_businesses, "pending_credit_purchases": pending_credit_purchases, "open_disputes": open_disputes},
            "orders": {"active_count": active_orders, "disputed_count": disputed_orders, "delivered_waiting_close_count": delivered_orders},
            "credits": {"manual_review_count": pending_credit_purchases},
            "risk": {"businesses_under_review": under_review},
            "users": {
                "clients_total": clients_total,
                "client_profiles_with_phone": clients_with_phone,
                "recent_client_contacts": [
                    {
                        "id": str(row["id"]),
                        "first_name": row["first_name"],
                        "username": row["username"],
                        "phone": row["phone"],
                        "updated_at": row["updated_at"].isoformat(),
                    }
                    for row in recent_contacts
                ],
            },
        }

    def metrics(self) -> dict[str, Any]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            business_total = conn.execute("select count(*) as c from businesses").fetchone()["c"]
            approved = conn.execute("select count(*) as c from businesses where verification_status = 'approved'").fetchone()["c"]
            orders = {row["status"]: row["c"] for row in conn.execute("select status, count(*) as c from orders group by status").fetchall()}
            disputes = {row["status"]: row["c"] for row in conn.execute("select status, count(*) as c from disputes group by status").fetchall()}
            ledger = {row["type"]: row["c"] for row in conn.execute("select type, count(*) as c from credits_ledger group by type").fetchall()}
        return {
            "source": "read_model",
            "generated_at": None,
            "businesses": {"total": business_total, "approved": approved},
            "orders": orders,
            "disputes": disputes,
            "credits": {"consumed_ledger_entries": ledger.get("consume", 0), "released_ledger_entries": ledger.get("release", 0)},
        }
