from __future__ import annotations

import time
from typing import Any

from app.core.errors import ApiError
from app.modules.orders.row_mappers import profile_mark


class PostgresPaymentCreditConsumptionMixin:
    def _ensure_no_existing_credit_consumption(self, conn: Any, *, order_id: str, profile: list[dict[str, Any]] | None) -> None:
        stage_started = time.perf_counter()
        existing_consume = conn.execute(
            "select 1 from credits_ledger where type = 'consume' and related_order_id = %s limit 1",
            (order_id,),
        ).fetchone()
        profile_mark(profile, "repo_atomic:check_existing_consume", stage_started)
        if existing_consume:
            conn.rollback()
            raise ApiError("CREDIT_ALREADY_CONSUMED", status_code=409)

    def _lock_wallet_with_credit_hold(self, conn: Any, *, business_id: str, ad_row: Any, profile: list[dict[str, Any]] | None) -> Any:
        stage_started = time.perf_counter()
        wallet_row = conn.execute("select * from credit_wallets where business_id = %s for update", (business_id,)).fetchone()
        profile_mark(profile, "repo_atomic:lock_wallet", stage_started)
        if wallet_row is None or wallet_row["blocked_credits"] < ad_row["required_credits"]:
            conn.rollback()
            raise ApiError("CREDIT_HOLD_NOT_FOUND", status_code=409)
        return wallet_row

    def _consume_credit_hold(
        self,
        conn: Any,
        *,
        order_id: str,
        business_id: str,
        actor_user_id: str,
        ad_row: Any,
        wallet_row: Any,
        profile: list[dict[str, Any]] | None,
    ) -> Any:
        blocked_after, consumed_after = self._consumed_hold_balances(wallet_row=wallet_row, ad_row=ad_row)
        self._update_wallet_for_consumed_hold(
            conn,
            business_id=business_id,
            blocked_after=blocked_after,
            consumed_after=consumed_after,
            profile=profile,
        )
        return self._insert_consumed_hold_ledger(
            conn,
            order_id=order_id,
            business_id=business_id,
            actor_user_id=actor_user_id,
            ad_row=ad_row,
            wallet_row=wallet_row,
            blocked_after=blocked_after,
            consumed_after=consumed_after,
            profile=profile,
        )

    def _consumed_hold_balances(self, *, wallet_row: Any, ad_row: Any) -> tuple[int, int]:
        return wallet_row["blocked_credits"] - ad_row["required_credits"], wallet_row["consumed_credits"] + ad_row["required_credits"]

    def _update_wallet_for_consumed_hold(self, conn: Any, *, business_id: str, blocked_after: int, consumed_after: int, profile: list[dict[str, Any]] | None) -> None:
        stage_started = time.perf_counter()
        conn.execute(
            "update credit_wallets set blocked_credits = %s, consumed_credits = %s, updated_at = now() where business_id = %s",
            (blocked_after, consumed_after, business_id),
        )
        profile_mark(profile, "repo_atomic:update_wallet", stage_started)

    def _insert_consumed_hold_ledger(
        self,
        conn: Any,
        *,
        order_id: str,
        business_id: str,
        actor_user_id: str,
        ad_row: Any,
        wallet_row: Any,
        blocked_after: int,
        consumed_after: int,
        profile: list[dict[str, Any]] | None,
    ) -> Any:
        stage_started = time.perf_counter()
        ledger_row = conn.execute(
            """
            insert into credits_ledger (
                business_id, type, amount, available_before, available_after,
                blocked_before, blocked_after, consumed_before, consumed_after,
                related_ad_id, related_order_id, reason, source, reference_type,
                reference_id, created_by, created_at
            )
            values (%s, 'consume', %s, %s, %s, %s, %s, %s, %s, %s, %s,
                'business_confirmed_payment_received', 'orders', 'order', %s, %s, now())
            returning *
            """,
            (
                business_id,
                ad_row["required_credits"],
                wallet_row["available_credits"],
                wallet_row["available_credits"],
                wallet_row["blocked_credits"],
                blocked_after,
                wallet_row["consumed_credits"],
                consumed_after,
                ad_row["id"],
                order_id,
                order_id,
                actor_user_id,
            ),
        ).fetchone()
        profile_mark(profile, "repo_atomic:insert_consume_ledger", stage_started)
        return ledger_row

    def _archive_consumed_ad(self, conn: Any, *, ad_row: Any, ledger_row: Any, profile: list[dict[str, Any]] | None) -> None:
        stage_started = time.perf_counter()
        conn.execute(
            "update ads set status = 'archived', credit_consumed_ledger_id = %s, updated_at = now() where id = %s",
            (ledger_row["id"], ad_row["id"]),
        )
        profile_mark(profile, "repo_atomic:archive_ad", stage_started)
