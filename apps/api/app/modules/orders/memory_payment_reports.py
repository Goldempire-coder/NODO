from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.errors import ApiError
from app.modules.businesses.models import FileAssetRecord
from app.modules.orders.models import PaymentReportRecord, utc_now


class InMemoryOrderPaymentReportsMixin:
    def get_submitted_payment_report_for_order(self, order_id: str) -> PaymentReportRecord | None:
        for report in self.payment_reports.values():  # type: ignore[attr-defined]
            if report.order_id == order_id and report.status == "submitted":
                return report
        return None

    def get_latest_payment_report_for_order(self, order_id: str) -> PaymentReportRecord | None:
        reports = [report for report in self.payment_reports.values() if report.order_id == order_id]  # type: ignore[attr-defined]
        if not reports:
            return None
        return sorted(reports, key=lambda report: report.created_at, reverse=True)[0]

    def get_payment_report_by_idempotency_key(self, *, reported_by_user_id: str, idempotency_key: str) -> PaymentReportRecord | None:
        for report in self.payment_reports.values():  # type: ignore[attr-defined]
            if report.reported_by_user_id == reported_by_user_id and report.idempotency_key == idempotency_key:
                return report
        return None

    def update_payment_report(self, report: PaymentReportRecord, **fields: Any) -> PaymentReportRecord:
        with self._lock:  # type: ignore[attr-defined]
            for key, value in fields.items():
                setattr(report, key, value)
            report.updated_at = utc_now()
            return report

    def list_payment_evidence_for_report(self, payment_report_id: str) -> list[FileAssetRecord]:
        return [
            file
            for file in self.files.values()  # type: ignore[attr-defined]
            if file.resource_type == "payment_report"
            and file.resource_id == payment_report_id
            and file.file_type == "payment_evidence"
            and file.deleted_at is None
        ]

    def create_payment_evidence_file(
        self,
        *,
        file_id: str,
        owner_user_id: str,
        payment_report_id: str,
        storage_path: str,
        mime_type: str,
        size_bytes: int,
        content_sha256: str,
        order_id: str,
    ) -> FileAssetRecord:
        with self._lock:  # type: ignore[attr-defined]
            file = FileAssetRecord(
                id=file_id,
                owner_user_id=owner_user_id,
                resource_type="payment_report",
                resource_id=payment_report_id,
                file_type="payment_evidence",
                storage_path=storage_path,
                mime_type=mime_type,
                size_bytes=size_bytes,
                metadata_json={
                    "content_sha256": content_sha256,
                    "order_id": order_id,
                },
            )
            self.files[file.id] = file  # type: ignore[attr-defined]
            return file

    def get_payment_evidence_file(self, file_id: str) -> FileAssetRecord | None:
        file = self.files.get(file_id)  # type: ignore[attr-defined]
        if file and file.resource_type == "payment_report" and file.file_type == "payment_evidence" and file.deleted_at is None:
            return file
        return None

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
        with self._lock:  # type: ignore[attr-defined]
            if self.get_submitted_payment_report_for_order(order_id) is not None:
                raise ApiError("PAYMENT_REPORT_ALREADY_SUBMITTED", status_code=409)
            if report_id in self.payment_reports or (  # type: ignore[attr-defined]
                proof_file_id is not None
                and any(
                    report.proof_file_id == proof_file_id
                    for report in self.payment_reports.values()  # type: ignore[attr-defined]
                )
            ):
                raise ApiError(
                    "PAYMENT_REPORT_PROOF_ALREADY_USED",
                    status_code=409,
                )
            if proof_content_sha256 is not None and any(
                report.proof_content_sha256 == proof_content_sha256
                for report in self.payment_reports.values()  # type: ignore[attr-defined]
            ):
                raise ApiError(
                    "PAYMENT_REPORT_PROOF_ALREADY_USED",
                    status_code=409,
                )
            now = utc_now()
            report = PaymentReportRecord(
                id=report_id,
                order_id=order_id,
                reported_by_user_id=reported_by_user_id,
                status="submitted",
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
                created_at=now,
                updated_at=now,
            )
            self.payment_reports[report.id] = report  # type: ignore[attr-defined]
            return report
