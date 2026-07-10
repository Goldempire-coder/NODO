from __future__ import annotations

from app.core.errors import ApiError
from app.modules.ads.models import CreditLedgerRecord
from app.modules.credits.models import CreditPurchaseRecord
from app.modules.credits.postgres_referral_bonus import grant_referral_bonus_if_eligible_pg
from app.modules.credits.row_mappers import ledger_from_row, purchase_from_row


def approve_purchase_pg(connect, *, purchase: CreditPurchaseRecord, actor_user_id: str | None, event_id: str | None = None, payment_intent_id: str | None = None, admin_note: str | None = None) -> tuple[CreditPurchaseRecord, CreditLedgerRecord | None]:  # type: ignore[no-untyped-def]
    with connect() as conn:
        current_purchase = _purchase_for_update_or_raise(conn, purchase.id)
        existing = _existing_purchase_ledger(conn, purchase.id)
        if existing:
            return _approved_purchase_replay_or_raise(conn, current_purchase, existing)
        allowed_statuses = {"pending_manual_review"} if admin_note else {"pending_payment", "paid"}
        if current_purchase.status not in allowed_statuses:
            conn.rollback()
            raise ApiError("PURCHASE_STATUS_INVALID", status_code=409)
        wallet = _credit_wallet_for_update(conn, current_purchase.business_id)
        available_after = _credit_wallet_for_purchase(conn, current_purchase, wallet)
        updated_purchase = _mark_purchase_approved(
            conn,
            current_purchase,
            event_id=event_id,
            payment_intent_id=payment_intent_id,
            actor_user_id=actor_user_id,
            admin_note=admin_note,
        )
        ledger_row = _insert_purchase_ledger(conn, current_purchase, wallet, available_after, actor_user_id)
        grant_referral_bonus_if_eligible_pg(
            conn,
            referred_business_id=current_purchase.business_id,
            purchase_id=current_purchase.id,
            actor_user_id=actor_user_id,
        )
        conn.commit()
    return purchase_from_row(updated_purchase), ledger_from_row(ledger_row)


def _purchase_for_update_or_raise(conn, purchase_id: str) -> CreditPurchaseRecord:  # type: ignore[no-untyped-def]
    current = conn.execute("select * from credit_purchases where id = %s for update", (purchase_id,)).fetchone()
    if current is None:
        conn.rollback()
        raise ApiError("PURCHASE_NOT_FOUND", status_code=404)
    return purchase_from_row(current)


def _existing_purchase_ledger(conn, purchase_id: str):  # type: ignore[no-untyped-def]
    return conn.execute(
        "select * from credits_ledger where type = 'purchase' and related_credit_purchase_id = %s limit 1",
        (purchase_id,),
    ).fetchone()


def _approved_purchase_replay_or_raise(conn, current_purchase: CreditPurchaseRecord, existing):  # type: ignore[no-untyped-def]
    if current_purchase.status == "approved":
        return current_purchase, ledger_from_row(existing)
    conn.rollback()
    raise ApiError("CREDIT_ALREADY_GRANTED", status_code=409)


def _credit_wallet_for_update(conn, business_id: str):  # type: ignore[no-untyped-def]
    row = conn.execute("select * from credit_wallets where business_id = %s for update", (business_id,)).fetchone()
    if row is not None:
        return row
    return conn.execute(
        """
        insert into credit_wallets (business_id, available_credits, blocked_credits, consumed_credits, created_at, updated_at)
        values (%s, 0, 0, 0, now(), now()) returning *
        """,
        (business_id,),
    ).fetchone()


def _credit_wallet_for_purchase(conn, current_purchase: CreditPurchaseRecord, wallet) -> int:  # type: ignore[no-untyped-def]
    available_after = wallet["available_credits"] + current_purchase.credits_amount
    conn.execute(
        """
        update credit_wallets
        set available_credits = %s,
            lifetime_purchased_credits = lifetime_purchased_credits + %s,
            updated_at = now()
        where business_id = %s
        """,
        (available_after, current_purchase.credits_amount, current_purchase.business_id),
    )
    return available_after


def _mark_purchase_approved(
    conn,
    current_purchase: CreditPurchaseRecord,
    *,
    event_id: str | None,
    payment_intent_id: str | None,
    actor_user_id: str | None,
    admin_note: str | None,
):  # type: ignore[no-untyped-def]
    return conn.execute(
        """
        update credit_purchases
        set status = 'approved', paid_at = coalesce(paid_at, now()), approved_at = now(),
            stripe_event_id = coalesce(%s, stripe_event_id),
            stripe_payment_intent_id = coalesce(%s, stripe_payment_intent_id),
            approved_by_admin_id = coalesce(%s, approved_by_admin_id),
            admin_note = coalesce(%s, admin_note),
            updated_at = now()
        where id = %s returning *
        """,
        (event_id, payment_intent_id, actor_user_id if admin_note else None, admin_note, current_purchase.id),
    ).fetchone()


def _insert_purchase_ledger(conn, current_purchase: CreditPurchaseRecord, wallet, available_after: int, actor_user_id: str | None):  # type: ignore[no-untyped-def]
    return conn.execute(
        """
        insert into credits_ledger (
            business_id, type, amount, available_before, available_after,
            blocked_before, blocked_after, consumed_before, consumed_after,
            related_credit_purchase_id, reason, source, reference_type, reference_id,
            created_by, created_at
        )
        values (%s, 'purchase', %s, %s, %s, %s, %s, %s, %s, %s,
            'credit_purchase_approved', 'credit_purchases', 'credit_purchase', %s, %s, now())
        returning *
        """,
        (
            current_purchase.business_id,
            current_purchase.credits_amount,
            wallet["available_credits"],
            available_after,
            wallet["blocked_credits"],
            wallet["blocked_credits"],
            wallet["consumed_credits"],
            wallet["consumed_credits"],
            current_purchase.id,
            current_purchase.id,
            actor_user_id,
        ),
    ).fetchone()


def reject_purchase_pg(connect, *, purchase: CreditPurchaseRecord, admin_user_id: str, reason: str) -> CreditPurchaseRecord:  # type: ignore[no-untyped-def]
    with connect() as conn:
        row = conn.execute(
            """
            update credit_purchases
            set status = 'rejected', rejected_by_admin_id = %s, admin_note = %s,
                rejected_at = now(), updated_at = now()
            where id = %s and status = 'pending_manual_review'
            returning *
            """,
            (admin_user_id, reason, purchase.id),
        ).fetchone()
        if row is None:
            conn.rollback()
            raise ApiError("MANUAL_PAYMENT_ALREADY_REVIEWED", status_code=409)
        conn.commit()
    return purchase_from_row(row)
