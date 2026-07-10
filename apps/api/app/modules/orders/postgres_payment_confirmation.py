from __future__ import annotations

import time
from typing import Any

from app.core.errors import ApiError
from app.modules.ads.models import CreditLedgerRecord
from app.modules.orders.models import OrderRecord, PaymentReportRecord
from app.modules.orders.postgres_payment_credit_consumption import PostgresPaymentCreditConsumptionMixin
from app.modules.orders.row_mappers import credit_ledger_from_row, order_from_row, payment_report_from_row, profile_mark


class PostgresPaymentConfirmationMixin(PostgresPaymentCreditConsumptionMixin):
    def confirm_business_payment_with_credit_consumption(
        self,
        *,
        order_id: str,
        business_id: str,
        actor_user_id: str,
        profile: list[dict[str, Any]] | None = None,
    ) -> tuple[OrderRecord, PaymentReportRecord, CreditLedgerRecord]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            order_row = self._lock_confirmable_order(conn, order_id=order_id, business_id=business_id, profile=profile)
            report_row = self._lock_submitted_payment_report(conn, order_id=order_id, profile=profile)
            ad_row = self._lock_order_ad(conn, order_row=order_row, business_id=business_id, profile=profile)
            self._ensure_no_existing_credit_consumption(conn, order_id=order_id, profile=profile)
            wallet_row = self._lock_wallet_with_credit_hold(conn, business_id=business_id, ad_row=ad_row, profile=profile)
            ledger_row = self._consume_credit_hold(
                conn,
                order_id=order_id,
                business_id=business_id,
                actor_user_id=actor_user_id,
                ad_row=ad_row,
                wallet_row=wallet_row,
                profile=profile,
            )
            self._archive_consumed_ad(conn, ad_row=ad_row, ledger_row=ledger_row, profile=profile)
            report_row = self._accept_payment_report(conn, report_row=report_row, profile=profile)
            order_row = self._mark_order_payment_confirmed(conn, order_id=order_id, profile=profile)
            stage_started = time.perf_counter()
            conn.commit()
            profile_mark(profile, "repo_atomic:commit", stage_started)
        return order_from_row(order_row), payment_report_from_row(report_row), credit_ledger_from_row(ledger_row)

    def _lock_confirmable_order(self, conn: Any, *, order_id: str, business_id: str, profile: list[dict[str, Any]] | None) -> Any:
        stage_started = time.perf_counter()
        order_row = conn.execute(
            "select * from orders where id = %s and business_id = %s for update",
            (order_id, business_id),
        ).fetchone()
        profile_mark(profile, "repo_atomic:lock_order", stage_started)
        if order_row is None:
            conn.rollback()
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        if order_row["status"] != "payment_reported":
            conn.rollback()
            raise ApiError("PAYMENT_CONFIRMATION_NOT_ALLOWED", status_code=409)
        return order_row

    def _lock_submitted_payment_report(self, conn: Any, *, order_id: str, profile: list[dict[str, Any]] | None) -> Any:
        stage_started = time.perf_counter()
        report_row = conn.execute(
            "select * from payment_reports where order_id = %s and status = 'submitted' order by created_at desc limit 1 for update",
            (order_id,),
        ).fetchone()
        profile_mark(profile, "repo_atomic:lock_payment_report", stage_started)
        if report_row is None:
            conn.rollback()
            raise ApiError("PAYMENT_REPORT_NOT_FOUND", status_code=404)
        return report_row

    def _lock_order_ad(self, conn: Any, *, order_row: Any, business_id: str, profile: list[dict[str, Any]] | None) -> Any:
        stage_started = time.perf_counter()
        ad_row = conn.execute("select * from ads where id = %s and business_id = %s for update", (order_row["ad_id"], business_id)).fetchone()
        profile_mark(profile, "repo_atomic:lock_ad", stage_started)
        if ad_row is None:
            conn.rollback()
            raise ApiError("AD_NOT_FOUND", status_code=404)
        if ad_row["credit_hold_ledger_id"] is None:
            conn.rollback()
            raise ApiError("CREDIT_HOLD_NOT_FOUND", status_code=409)
        return ad_row

    def _accept_payment_report(self, conn: Any, *, report_row: Any, profile: list[dict[str, Any]] | None) -> Any:
        stage_started = time.perf_counter()
        updated_report = conn.execute(
            "update payment_reports set status = 'accepted', updated_at = now() where id = %s returning *",
            (report_row["id"],),
        ).fetchone()
        profile_mark(profile, "repo_atomic:accept_payment_report", stage_started)
        return updated_report

    def _mark_order_payment_confirmed(self, conn: Any, *, order_id: str, profile: list[dict[str, Any]] | None) -> Any:
        stage_started = time.perf_counter()
        order_row = conn.execute(
            """
            update orders
            set status = 'payment_confirmed',
                payment_confirmed_at = now(),
                delivery_warning_at = now() + interval '30 minutes',
                delivery_deadline_at = now() + interval '2 hours',
                updated_at = now()
            where id = %s
            returning *
            """,
            (order_id,),
        ).fetchone()
        profile_mark(profile, "repo_atomic:update_order_confirmed", stage_started)
        return order_row
