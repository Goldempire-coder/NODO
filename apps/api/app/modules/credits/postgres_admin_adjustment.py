from __future__ import annotations

from app.core.errors import ApiError
from app.modules.ads.models import CreditLedgerRecord
from app.modules.credits.row_mappers import ledger_from_row


def adjust_wallet_pg(connect, *, business_id: str, amount: int, direction: str, reason: str, notes: str | None, created_by: str) -> CreditLedgerRecord:  # type: ignore[no-untyped-def]
    with connect() as conn:
        wallet = conn.execute("select * from credit_wallets where business_id = %s for update", (business_id,)).fetchone()
        if wallet is None:
            wallet = conn.execute(
                "insert into credit_wallets (business_id, created_at, updated_at) values (%s, now(), now()) returning *",
                (business_id,),
            ).fetchone()
        signed = amount if direction == "add" else -amount
        if wallet["available_credits"] + signed < 0:
            conn.rollback()
            raise ApiError("CREDIT_BALANCE_INSUFFICIENT", status_code=409)
        available_after = wallet["available_credits"] + signed
        conn.execute(
            """
            update credit_wallets
            set available_credits = %s,
                lifetime_adjusted_credits = lifetime_adjusted_credits + %s,
                updated_at = now()
            where business_id = %s
            """,
            (available_after, amount if signed > 0 else 0, business_id),
        )
        row = conn.execute(
            """
            insert into credits_ledger (
                business_id, type, amount, available_before, available_after,
                blocked_before, blocked_after, consumed_before, consumed_after,
                reason, source, reference_type, reference_id, notes, created_by, created_at
            )
            values (%s, 'admin_adjustment', %s, %s, %s, %s, %s, %s, %s,
                %s, 'admin', 'business', %s, %s, %s, now())
            returning *
            """,
            (
                business_id,
                amount,
                wallet["available_credits"],
                available_after,
                wallet["blocked_credits"],
                wallet["blocked_credits"],
                wallet["consumed_credits"],
                wallet["consumed_credits"],
                reason,
                business_id,
                notes,
                created_by,
            ),
        ).fetchone()
        conn.commit()
    return ledger_from_row(row)
