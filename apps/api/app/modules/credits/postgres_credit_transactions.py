from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.modules.ads.models import CreditLedgerRecord
from app.modules.credits.credit_transactions import (
    CreditTransactionRecord,
    CreditTransactionSummary,
)
from app.modules.credits.row_mappers import ledger_from_row, purchase_from_row
from app.shared.keyset_pagination import decode_keyset_cursor, encode_keyset_cursor

_FINANCIAL_STATUS_SQL = """
case
  when exists (
    select 1 from credits_ledger ledger_status
    where ledger_status.related_credit_purchase_id = cp.id
      and ledger_status.type = 'purchase'
  ) and cp.status in ('approved', 'credited') then 'confirmed'
  when cp.owner_dismissed_at is not null
    and not exists (
      select 1 from credits_ledger ledger_status
      where ledger_status.related_credit_purchase_id = cp.id
        and ledger_status.type = 'purchase'
    ) then 'dismissed'
  when cp.status in ('pending_manual_review', 'under_review', 'verified') then 'review'
  when cp.status in ('approved', 'credited') then 'review'
  when cp.status in ('rejected', 'failed', 'expired', 'verification_failed') then 'failed'
  when cp.status in ('created', 'pending_payment', 'pending_onchain_confirmation', 'detected', 'paid') then 'pending'
  else 'review'
end
"""


def list_credit_transactions_pg(
    connect,
    *,
    financial_status: str | None,
    payment_method: str | None,
    business_id: str | None,
    package_code: str | None,
    created_from: datetime | None,
    created_to: datetime | None,
    cursor: str | None,
    limit: int,
) -> tuple[list[CreditTransactionRecord], str | None, CreditTransactionSummary]:  # type: ignore[no-untyped-def]
    base_where, base_params = _base_filters(
        payment_method=payment_method,
        business_id=business_id,
        package_code=package_code,
        created_from=created_from,
        created_to=created_to,
    )
    filtered_where = ""
    filtered_params: list[object] = []
    if financial_status:
        filtered_where += " and financial_status = %s"
        filtered_params.append(financial_status)
    page_where = filtered_where
    page_params = [*base_params, *filtered_params]
    if cursor:
        position = decode_keyset_cursor(cursor)
        page_where += " and (created_at, id) < (%s, %s::uuid)"
        page_params.extend((position.timestamp, position.item_id))
    page_params.append(limit + 1)
    page_sql = f"""
        with base as (
            select cp.*, b.business_name, {_FINANCIAL_STATUS_SQL} as financial_status
            from credit_purchases cp
            left join businesses b on b.id = cp.business_id
            where {base_where}
        )
        select * from base
        where 1 = 1 {page_where}
        order by created_at desc, id desc
        limit %s
    """
    summary_sql = f"""
        with base as (
            select cp.*, {_FINANCIAL_STATUS_SQL} as financial_status
            from credit_purchases cp
            where {base_where}
        ),
        filtered as (
            select * from base where 1 = 1 {filtered_where}
        )
        select
            count(*) as total_count,
            count(*) filter (where financial_status = 'confirmed') as confirmed_count,
            count(*) filter (where financial_status = 'pending') as pending_count,
            count(*) filter (where financial_status = 'review') as review_count,
            count(*) filter (where financial_status = 'failed') as failed_count,
            count(*) filter (where financial_status = 'dismissed') as dismissed_count,
            coalesce(sum(price_usd) filter (where financial_status = 'confirmed'), 0) as confirmed_amount_usd,
            coalesce(sum(credits_amount) filter (where financial_status = 'confirmed'), 0) as confirmed_credits
        from filtered
    """
    with connect() as conn:
        page_rows = conn.execute(page_sql, page_params).fetchall()
        summary_row = conn.execute(summary_sql, [*base_params, *filtered_params]).fetchone()
        page = page_rows[:limit]
        ledgers = _purchase_ledgers(conn, [str(row["id"]) for row in page])
    records = [
        CreditTransactionRecord(
            purchase=purchase_from_row(row),
            business_name=row["business_name"],
            ledger=ledgers.get(str(row["id"])),
        )
        for row in page
    ]
    next_cursor = (
        encode_keyset_cursor(records[-1].purchase.created_at, records[-1].purchase.id)
        if len(page_rows) > limit and records
        else None
    )
    return records, next_cursor, _summary_from_row(summary_row)


def _base_filters(
    *,
    payment_method: str | None,
    business_id: str | None,
    package_code: str | None,
    created_from: datetime | None,
    created_to: datetime | None,
) -> tuple[str, list[object]]:
    clauses = ["1 = 1"]
    params: list[object] = []
    if payment_method:
        clauses.append("cp.payment_method = %s")
        params.append(payment_method)
    if business_id:
        clauses.append("cp.business_id = %s")
        params.append(business_id)
    if package_code:
        clauses.append("cp.package_code = %s")
        params.append(package_code)
    if created_from:
        clauses.append("cp.created_at >= %s")
        params.append(created_from)
    if created_to:
        clauses.append("cp.created_at <= %s")
        params.append(created_to)
    return " and ".join(clauses), params


def _purchase_ledgers(conn, purchase_ids: list[str]) -> dict[str, CreditLedgerRecord]:  # type: ignore[no-untyped-def]
    if not purchase_ids:
        return {}
    placeholders = ", ".join(["%s::uuid"] * len(purchase_ids))
    rows = conn.execute(
        f"""
        select distinct on (related_credit_purchase_id) *
        from credits_ledger
        where type = 'purchase'
          and related_credit_purchase_id in ({placeholders})
        order by related_credit_purchase_id, created_at desc, id desc
        """,
        purchase_ids,
    ).fetchall()
    return {str(row["related_credit_purchase_id"]): ledger_from_row(row) for row in rows}


def _summary_from_row(row) -> CreditTransactionSummary:  # type: ignore[no-untyped-def]
    return CreditTransactionSummary(
        total_count=row["total_count"] or 0,
        confirmed_count=row["confirmed_count"] or 0,
        pending_count=row["pending_count"] or 0,
        review_count=row["review_count"] or 0,
        failed_count=row["failed_count"] or 0,
        dismissed_count=row["dismissed_count"] or 0,
        confirmed_amount_usd=Decimal(str(row["confirmed_amount_usd"] or "0")),
        confirmed_credits=row["confirmed_credits"] or 0,
    )
