from __future__ import annotations

from decimal import Decimal

from app.core.errors import ApiError
from app.modules.ads.models import AdRecord
from app.modules.ads.row_mappers import ad_from_row


class PostgresAdPublishMixin:
    def publish_ad(
        self,
        *,
        business_id: str,
        payment_method_id: str,
        payment_method: str,
        delivery_method: str,
        rate_bs_per_usd: Decimal,
        amount_min_usd: Decimal,
        amount_max_usd: Decimal,
        required_credits: int,
        created_by: str,
        use_founder_access: bool,
    ) -> AdRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            self._require_active_candidate_in_transaction(  # type: ignore[attr-defined]
                conn,
                business_id=business_id,
                payment_method=payment_method,
                amount_max_usd=amount_max_usd,
                enforce_publication_access=True,
            )
            wallet_row = self._wallet_for_ad_publish(conn, business_id=business_id)
            self._ensure_publish_credit_balance(conn, wallet_row, required_credits=required_credits, use_founder_access=use_founder_access)
            ad_row = self._insert_active_ad(
                conn,
                business_id=business_id,
                payment_method_id=payment_method_id,
                payment_method=payment_method,
                delivery_method=delivery_method,
                rate_bs_per_usd=rate_bs_per_usd,
                amount_min_usd=amount_min_usd,
                amount_max_usd=amount_max_usd,
                required_credits=required_credits,
            )
            ad = ad_from_row(ad_row)
            available_after, blocked_after = self._publish_wallet_balances(wallet_row, required_credits=required_credits, use_founder_access=use_founder_access)
            if not use_founder_access:
                self._update_wallet_for_publish_hold(conn, business_id=business_id, available_after=available_after, blocked_after=blocked_after)
            ledger_row = self._insert_publish_ledger(
                conn,
                business_id=business_id,
                ad_id=ad.id,
                wallet_row=wallet_row,
                required_credits=required_credits,
                available_after=available_after,
                blocked_after=blocked_after,
                created_by=created_by,
                use_founder_access=use_founder_access,
            )
            if not use_founder_access:
                ad_row = self._attach_hold_ledger_to_ad(conn, ad_id=ad.id, ledger_id=ledger_row["id"])
            conn.commit()
        return ad_from_row(ad_row)

    def _wallet_for_ad_publish(self, conn, *, business_id: str):  # type: ignore[no-untyped-def]
        return conn.execute(
            """
            insert into credit_wallets (business_id, available_credits, blocked_credits, consumed_credits, created_at, updated_at)
            values (%s, 0, 0, 0, now(), now())
            on conflict (business_id) do update set updated_at = credit_wallets.updated_at
            returning *
            """,
            (business_id,),
        ).fetchone()

    def _ensure_publish_credit_balance(self, conn, wallet_row, *, required_credits: int, use_founder_access: bool) -> None:  # type: ignore[no-untyped-def]
        if not use_founder_access and wallet_row["available_credits"] < required_credits:
            conn.rollback()
            raise ApiError("CREDIT_BALANCE_INSUFFICIENT", status_code=409)

    def _insert_active_ad(
        self,
        conn,
        *,
        business_id: str,
        payment_method_id: str,
        payment_method: str,
        delivery_method: str,
        rate_bs_per_usd: Decimal,
        amount_min_usd: Decimal,
        amount_max_usd: Decimal,
        required_credits: int,
    ):  # type: ignore[no-untyped-def]
        return conn.execute(
            """
            insert into ads (
                business_id, payment_method_id, payment_method, delivery_method, rate_bs_per_usd,
                amount_min_usd, amount_max_usd, required_credits, status,
                activated_at, expires_at, last_rate_updated_at, created_at, updated_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, 'active', now(), now() + interval '7 days', now(), now(), now())
            returning *
            """,
            (business_id, payment_method_id, payment_method, delivery_method, rate_bs_per_usd, amount_min_usd, amount_max_usd, required_credits),
        ).fetchone()

    def _publish_wallet_balances(self, wallet_row, *, required_credits: int, use_founder_access: bool) -> tuple[int, int]:  # type: ignore[no-untyped-def]
        available_after = wallet_row["available_credits"] if use_founder_access else wallet_row["available_credits"] - required_credits
        blocked_after = wallet_row["blocked_credits"] if use_founder_access else wallet_row["blocked_credits"] + required_credits
        return available_after, blocked_after

    def _update_wallet_for_publish_hold(self, conn, *, business_id: str, available_after: int, blocked_after: int) -> None:  # type: ignore[no-untyped-def]
        conn.execute(
            """
            update credit_wallets
            set available_credits = %s, blocked_credits = %s, updated_at = now()
            where business_id = %s
            """,
            (available_after, blocked_after, business_id),
        )

    def _insert_publish_ledger(
        self,
        conn,
        *,
        business_id: str,
        ad_id: str,
        wallet_row,
        required_credits: int,
        available_after: int,
        blocked_after: int,
        created_by: str,
        use_founder_access: bool,
    ):  # type: ignore[no-untyped-def]
        ledger_type = "founder_free_use" if use_founder_access else "hold"
        return conn.execute(
            """
            insert into credits_ledger (
                business_id, type, amount, available_before, available_after,
                blocked_before, blocked_after, consumed_before, consumed_after,
                related_ad_id, reason, source, reference_type, reference_id, created_by, created_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ads', 'ad', %s, %s, now())
            returning id
            """,
            (
                business_id,
                ledger_type,
                required_credits,
                wallet_row["available_credits"],
                available_after,
                wallet_row["blocked_credits"],
                blocked_after,
                wallet_row["consumed_credits"],
                wallet_row["consumed_credits"],
                ad_id,
                "founder_access_ad_publish" if use_founder_access else "ad_publish_credit_hold",
                ad_id,
                created_by,
            ),
        ).fetchone()

    def _attach_hold_ledger_to_ad(self, conn, *, ad_id: str, ledger_id: str):  # type: ignore[no-untyped-def]
        return conn.execute("update ads set credit_hold_ledger_id = %s, updated_at = now() where id = %s returning *", (ledger_id, ad_id)).fetchone()
