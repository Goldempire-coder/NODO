from __future__ import annotations

from app.modules.credits.models import CreditPurchaseRecord
from app.modules.credits.row_mappers import purchase_from_row
from app.shared.keyset_pagination import decode_keyset_cursor, encode_keyset_cursor


def get_purchase_pg(connect, purchase_id: str) -> CreditPurchaseRecord | None:  # type: ignore[no-untyped-def]
    with connect() as conn:
        row = conn.execute("select * from credit_purchases where id = %s", (purchase_id,)).fetchone()
    return purchase_from_row(row) if row else None


def find_purchase_by_checkout_session_pg(connect, session_id: str) -> CreditPurchaseRecord | None:  # type: ignore[no-untyped-def]
    with connect() as conn:
        row = conn.execute("select * from credit_purchases where stripe_checkout_session_id = %s", (session_id,)).fetchone()
    return purchase_from_row(row) if row else None


def stripe_event_processed_pg(connect, event_id: str) -> bool:  # type: ignore[no-untyped-def]
    with connect() as conn:
        row = conn.execute("select 1 from credit_purchases where stripe_event_id = %s limit 1", (event_id,)).fetchone()
    return row is not None


def list_purchases_pg(connect, *, status: str | None, business_id: str | None, cursor: str | None, limit: int) -> tuple[list[CreditPurchaseRecord], str | None]:  # type: ignore[no-untyped-def]
    sql = "select * from credit_purchases where 1 = 1"
    params: list[object] = []
    if status:
        sql += " and status = %s"
        params.append(status)
    if business_id:
        sql += " and business_id = %s"
        params.append(business_id)
    if cursor:
        position = decode_keyset_cursor(cursor)
        sql += " and (created_at, id) < (%s, %s::uuid)"
        params.extend((position.timestamp, position.item_id))
    sql += " order by created_at desc, id desc limit %s"
    params.append(limit + 1)
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    page = rows[:limit]
    items = [purchase_from_row(row) for row in page]
    next_cursor = encode_keyset_cursor(items[-1].created_at, items[-1].id) if len(rows) > limit else None
    return items, next_cursor
