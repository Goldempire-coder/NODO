from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.modules.orders.models import PaymentReportRecord
from app.modules.orders.postgres_payment_evidence_files import PostgresPaymentEvidenceFilesMixin
from app.modules.orders.row_mappers import payment_report_from_row


class PostgresPaymentReportsMixin(PostgresPaymentEvidenceFilesMixin):
    def get_submitted_payment_report_for_order(self, order_id: str) -> PaymentReportRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                "select * from payment_reports where order_id = %s and status = 'submitted' order by created_at desc limit 1",
                (order_id,),
            ).fetchone()
        return payment_report_from_row(row) if row else None

    def get_latest_payment_report_for_order(self, order_id: str) -> PaymentReportRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                "select * from payment_reports where order_id = %s order by created_at desc limit 1",
                (order_id,),
            ).fetchone()
        return payment_report_from_row(row) if row else None

    def get_payment_report_by_idempotency_key(self, *, reported_by_user_id: str, idempotency_key: str) -> PaymentReportRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                "select * from payment_reports where reported_by_user_id = %s and idempotency_key = %s limit 1",
                (reported_by_user_id, idempotency_key),
            ).fetchone()
        return payment_report_from_row(row) if row else None

    def update_payment_report(self, report: PaymentReportRecord, **fields: Any) -> PaymentReportRecord:
        assignments: list[str] = []
        params: list[Any] = []
        for key, value in fields.items():
            assignments.append(f"{key} = %s")
            params.append(value)
        assignments.append("updated_at = now()")
        params.append(report.id)
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(f"update payment_reports set {', '.join(assignments)} where id = %s returning *", params).fetchone()
            conn.commit()
        return payment_report_from_row(row)

    def create_payment_report(
        self,
        *,
        report_id: str,
        order_id: str,
        reported_by_user_id: str,
        idempotency_key: str,
        payment_type: str,
        payment_amount: Decimal,
        report_payload_hash: str,
        payment_reference: str | None = None,
        payment_sender_name: str | None = None,
        payment_sender_account_masked: str | None = None,
        tx_hash: str | None = None,
        network: str | None = None,
        proof_file_id: str | None = None,
        proof_content_sha256: str | None = None,
    ) -> PaymentReportRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = self._insert_payment_report(
                conn,
                report_id=report_id,
                order_id=order_id,
                reported_by_user_id=reported_by_user_id,
                idempotency_key=idempotency_key,
                payment_type=payment_type,
                payment_reference=payment_reference,
                payment_sender_name=payment_sender_name,
                payment_sender_account_masked=payment_sender_account_masked,
                tx_hash=tx_hash,
                network=network,
                payment_amount=payment_amount,
                proof_file_id=proof_file_id,
                proof_content_sha256=proof_content_sha256,
                report_payload_hash=report_payload_hash,
            )
            conn.commit()
        return payment_report_from_row(row)

    def _insert_payment_report(
        self,
        conn,
        *,
        report_id: str,
        order_id: str,
        reported_by_user_id: str,
        idempotency_key: str,
        payment_type: str,
        payment_reference: str | None,
        payment_sender_name: str | None,
        payment_sender_account_masked: str | None,
        tx_hash: str | None,
        network: str | None,
        payment_amount: Decimal,
        proof_file_id: str | None,
        proof_content_sha256: str | None,
        report_payload_hash: str,
    ):  # type: ignore[no-untyped-def]
        return conn.execute(
            """
            insert into payment_reports (
                id, order_id, reported_by_user_id, status, idempotency_key,
                payment_type, payment_reference, payment_sender_name,
                payment_sender_account_masked, tx_hash, network, payment_amount,
                proof_file_id, proof_content_sha256, report_payload_hash, created_at, updated_at
            )
            values (%s, %s, %s, 'submitted', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
            returning *
            """,
            (
                report_id,
                order_id,
                reported_by_user_id,
                idempotency_key,
                payment_type,
                payment_reference,
                payment_sender_name,
                payment_sender_account_masked,
                tx_hash,
                network,
                payment_amount,
                proof_file_id,
                proof_content_sha256,
                report_payload_hash,
            ),
        ).fetchone()
