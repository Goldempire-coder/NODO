from __future__ import annotations

from app.core.errors import ApiError
from app.modules.ads.models import AdRecord, CreditLedgerRecord
from app.modules.ads.row_mappers import credit_ledger_from_row


class PostgresAdCreditHoldsMixin:
    def release_hold(
        self,
        *,
        ad: AdRecord,
        created_by: str | None,
        reason: str = "ad_expired_without_order_or_payment",
        related_order_id: str | None = None,
        source: str = "ads",
    ) -> CreditLedgerRecord | None:
        if ad.credit_hold_ledger_id is None:
            return None
        with self._connect() as conn:  # type: ignore[attr-defined]
            if self._release_hold_already_exists(conn, ad_id=ad.id):
                return None
            wallet = self._lock_wallet_for_release(conn, ad=ad)
            if wallet is None:
                return None
            available_after = wallet["available_credits"] + ad.required_credits
            blocked_after = wallet["blocked_credits"] - ad.required_credits
            conn.execute(
                "update credit_wallets set available_credits = %s, blocked_credits = %s, updated_at = now() where business_id = %s",
                (available_after, blocked_after, ad.business_id),
            )
            row = self._insert_release_ledger(
                conn,
                ad=ad,
                wallet=wallet,
                available_after=available_after,
                blocked_after=blocked_after,
                created_by=created_by,
                reason=reason,
                related_order_id=related_order_id,
                source=source,
            )
            conn.commit()
        return credit_ledger_from_row(row)

    def consume_hold_for_order(
        self,
        *,
        ad: AdRecord,
        order_id: str,
        created_by: str,
        reason: str = "business_confirmed_payment_received",
        source: str = "orders",
    ) -> CreditLedgerRecord:
        if ad.credit_hold_ledger_id is None:
            raise ApiError("CREDIT_HOLD_NOT_FOUND", status_code=409)
        with self._connect() as conn:  # type: ignore[attr-defined]
            if self._consume_hold_already_exists(conn, order_id=order_id):
                raise ApiError("CREDIT_ALREADY_CONSUMED", status_code=409)
            wallet = self._lock_wallet_for_consume(conn, ad=ad)
            if wallet is None:
                conn.rollback()
                raise ApiError("CREDIT_HOLD_NOT_FOUND", status_code=409)
            blocked_after = wallet["blocked_credits"] - ad.required_credits
            consumed_after = wallet["consumed_credits"] + ad.required_credits
            conn.execute(
                """
                update credit_wallets
                set blocked_credits = %s, consumed_credits = %s, updated_at = now()
                where business_id = %s
                """,
                (blocked_after, consumed_after, ad.business_id),
            )
            row = self._insert_consume_ledger(
                conn,
                ad=ad,
                order_id=order_id,
                wallet=wallet,
                blocked_after=blocked_after,
                consumed_after=consumed_after,
                created_by=created_by,
                reason=reason,
                source=source,
            )
            conn.execute(
                "update ads set status = 'archived', credit_consumed_ledger_id = %s, updated_at = now() where id = %s",
                (row["id"], ad.id),
            )
            conn.commit()
        return credit_ledger_from_row(row)

    def expire_hold(
        self,
        *,
        ad: AdRecord,
        created_by: str | None,
        reason: str = "ad_expired_without_purchase",
        related_order_id: str | None = None,
        source: str = "ads",
    ) -> CreditLedgerRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            existing = self._expire_hold_already_exists(conn, ad_id=ad.id)
            if existing is not None:
                conn.execute(
                    """
                    update ads
                    set status = 'archived', credit_consumed_ledger_id = coalesce(credit_consumed_ledger_id, %s), updated_at = now()
                    where id = %s
                    """,
                    (existing["id"], ad.id),
                )
                conn.commit()
                return None
            if ad.credit_hold_ledger_id is None:
                conn.execute("update ads set status = 'archived', updated_at = now() where id = %s", (ad.id,))
                conn.commit()
                return None
            wallet = self._lock_wallet_for_consume(conn, ad=ad)
            if wallet is None:
                conn.execute("update ads set status = 'archived', updated_at = now() where id = %s", (ad.id,))
                conn.commit()
                return None
            blocked_after = wallet["blocked_credits"] - ad.required_credits
            consumed_after = wallet["consumed_credits"] + ad.required_credits
            conn.execute(
                """
                update credit_wallets
                set blocked_credits = %s, consumed_credits = %s, updated_at = now()
                where business_id = %s
                """,
                (blocked_after, consumed_after, ad.business_id),
            )
            row = self._insert_expire_ledger(
                conn,
                ad=ad,
                wallet=wallet,
                blocked_after=blocked_after,
                consumed_after=consumed_after,
                created_by=created_by,
                reason=reason,
                related_order_id=related_order_id,
                source=source,
            )
            conn.execute(
                "update ads set status = 'archived', credit_consumed_ledger_id = %s, updated_at = now() where id = %s",
                (row["id"], ad.id),
            )
            conn.commit()
        return credit_ledger_from_row(row)

    def _release_hold_already_exists(self, conn, *, ad_id: str) -> bool:  # type: ignore[no-untyped-def]
        row = conn.execute("select 1 from credits_ledger where type = 'release' and related_ad_id = %s limit 1", (ad_id,)).fetchone()
        return row is not None

    def _lock_wallet_for_release(self, conn, *, ad: AdRecord):  # type: ignore[no-untyped-def]
        wallet = conn.execute("select * from credit_wallets where business_id = %s for update", (ad.business_id,)).fetchone()
        if wallet is None or wallet["blocked_credits"] < ad.required_credits:
            return None
        return wallet

    def _insert_release_ledger(
        self,
        conn,
        *,
        ad: AdRecord,
        wallet,
        available_after: int,
        blocked_after: int,
        created_by: str | None,
        reason: str,
        related_order_id: str | None,
        source: str,
    ):  # type: ignore[no-untyped-def]
        return conn.execute(
            """
            insert into credits_ledger (
                business_id, type, amount, available_before, available_after,
                blocked_before, blocked_after, consumed_before, consumed_after,
                related_ad_id, reason, source, reference_type, reference_id, created_by, created_at
            )
            values (%s, 'release', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            returning *
            """,
            (
                ad.business_id,
                ad.required_credits,
                wallet["available_credits"],
                available_after,
                wallet["blocked_credits"],
                blocked_after,
                wallet["consumed_credits"],
                wallet["consumed_credits"],
                ad.id,
                reason,
                source,
                "order" if related_order_id else "ad",
                related_order_id or ad.id,
                created_by,
            ),
        ).fetchone()

    def _expire_hold_already_exists(self, conn, *, ad_id: str):  # type: ignore[no-untyped-def]
        return conn.execute("select * from credits_ledger where type = 'expire' and related_ad_id = %s limit 1", (ad_id,)).fetchone()

    def _consume_hold_already_exists(self, conn, *, order_id: str) -> bool:  # type: ignore[no-untyped-def]
        row = conn.execute(
            "select * from credits_ledger where type = 'consume' and related_order_id = %s limit 1",
            (order_id,),
        ).fetchone()
        return row is not None

    def _lock_wallet_for_consume(self, conn, *, ad: AdRecord):  # type: ignore[no-untyped-def]
        wallet = conn.execute("select * from credit_wallets where business_id = %s for update", (ad.business_id,)).fetchone()
        if wallet is None or wallet["blocked_credits"] < ad.required_credits:
            return None
        return wallet

    def _insert_consume_ledger(
        self,
        conn,
        *,
        ad: AdRecord,
        order_id: str,
        wallet,
        blocked_after: int,
        consumed_after: int,
        created_by: str,
        reason: str,
        source: str,
    ):  # type: ignore[no-untyped-def]
        return conn.execute(
            """
            insert into credits_ledger (
                business_id, type, amount, available_before, available_after,
                blocked_before, blocked_after, consumed_before, consumed_after,
                related_ad_id, related_order_id, reason, source, reference_type,
                reference_id, created_by, created_at
            )
            values (%s, 'consume', %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, 'order', %s, %s, now())
            returning *
            """,
            (
                ad.business_id,
                ad.required_credits,
                wallet["available_credits"],
                wallet["available_credits"],
                wallet["blocked_credits"],
                blocked_after,
                wallet["consumed_credits"],
                consumed_after,
                ad.id,
                order_id,
                reason,
                source,
                order_id,
                created_by,
            ),
        ).fetchone()

    def _insert_expire_ledger(
        self,
        conn,
        *,
        ad: AdRecord,
        wallet,
        blocked_after: int,
        consumed_after: int,
        created_by: str | None,
        reason: str,
        related_order_id: str | None,
        source: str,
    ):  # type: ignore[no-untyped-def]
        reference_type = "order" if related_order_id else "ad"
        reference_id = related_order_id or ad.id
        return conn.execute(
            """
            insert into credits_ledger (
                business_id, type, amount, available_before, available_after,
                blocked_before, blocked_after, consumed_before, consumed_after,
                related_ad_id, related_order_id, reason, source, reference_type,
                reference_id, created_by, created_at
            )
            values (%s, 'expire', %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, now())
            returning *
            """,
            (
                ad.business_id,
                ad.required_credits,
                wallet["available_credits"],
                wallet["available_credits"],
                wallet["blocked_credits"],
                blocked_after,
                wallet["consumed_credits"],
                consumed_after,
                ad.id,
                related_order_id,
                reason,
                source,
                reference_type,
                reference_id,
                created_by,
            ),
        ).fetchone()
