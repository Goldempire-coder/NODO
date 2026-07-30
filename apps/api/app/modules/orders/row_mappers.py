from __future__ import annotations

import json
import time
from decimal import Decimal
from typing import Any

from psycopg.types.json import Jsonb

from app.modules.ads.models import CreditLedgerRecord
from app.modules.businesses.models import FileAssetRecord
from app.modules.orders.models import OrderRecord, OrderStateEventRecord, PaymentReportRecord, RatingRecord


def decimal_from_row_value(value: object) -> Decimal:
    return Decimal(str(value))


def jsonb(value: dict | None) -> Jsonb | None:
    if value is None:
        return None
    return Jsonb(value, dumps=lambda payload: json.dumps(payload, default=str))


def optional_row_value(row, key: str, default=None):  # type: ignore[no-untyped-def]
    try:
        return row[key]
    except (KeyError, IndexError):
        return default


def profile_mark(profile: list[dict[str, Any]] | None, stage: str, started: float) -> None:
    if profile is None:
        return
    profile.append({"stage": stage, "elapsed_ms": round((time.perf_counter() - started) * 1000, 4)})


def credit_ledger_from_row(row: Any) -> CreditLedgerRecord:
    return CreditLedgerRecord(
        id=str(row["id"]),
        business_id=str(row["business_id"]),
        type=row["type"],
        amount=row["amount"],
        available_before=row["available_before"],
        available_after=row["available_after"],
        blocked_before=row["blocked_before"],
        blocked_after=row["blocked_after"],
        consumed_before=row["consumed_before"],
        consumed_after=row["consumed_after"],
        reason=row["reason"],
        source=row["source"],
        reference_type=row["reference_type"],
        reference_id=str(row["reference_id"]),
        related_ad_id=str(row["related_ad_id"]) if row["related_ad_id"] else None,
        related_order_id=str(row["related_order_id"]) if row["related_order_id"] else None,
        created_by=str(row["created_by"]) if row["created_by"] else None,
        created_at=row["created_at"],
    )


def order_from_row(row) -> OrderRecord:  # type: ignore[no-untyped-def]
    return OrderRecord(
        id=str(row["id"]),
        public_order_code=row["public_order_code"],
        ad_id=str(row["ad_id"]),
        business_id=str(row["business_id"]),
        remitter_user_id=str(row["remitter_user_id"]),
        status=row["status"],
        idempotency_key=row["idempotency_key"],
        completion_reason=row["completion_reason"],
        cancel_reason=row["cancel_reason"],
        dispute_reason=row["dispute_reason"],
        amount_usd=decimal_from_row_value(row["amount_usd"]),
        rate_snapshot=decimal_from_row_value(row["rate_snapshot"]),
        amount_bs_calculated=decimal_from_row_value(row["amount_bs_calculated"]),
        business_name_snapshot=row["business_name_snapshot"],
        payment_method_snapshot=row["payment_method_snapshot"],
        delivery_method_snapshot=row["delivery_method_snapshot"],
        min_amount_snapshot=decimal_from_row_value(row["min_amount_snapshot"]),
        max_amount_snapshot=decimal_from_row_value(row["max_amount_snapshot"]),
        payment_instructions_snapshot=row["payment_instructions_snapshot"],
        receiver_data_json=row["receiver_data_json"],
        payment_data_revealed_at=row["payment_data_revealed_at"],
        payment_data_revealed_by=str(row["payment_data_revealed_by"]) if row["payment_data_revealed_by"] else None,
        payment_report_deadline_at=row["payment_report_deadline_at"],
        payment_report_extension_used_at=row["payment_report_extension_used_at"],
        extension_used=row["extension_used"],
        expires_at=row["expires_at"],
        business_response_warning_at=row["business_response_warning_at"],
        business_response_deadline_at=row["business_response_deadline_at"],
        delivery_warning_at=row["delivery_warning_at"],
        delivery_deadline_at=row["delivery_deadline_at"],
        auto_complete_warning_12h_at=row["auto_complete_warning_12h_at"],
        auto_complete_warning_23h_at=row["auto_complete_warning_23h_at"],
        auto_complete_at=row["auto_complete_at"],
        paid_reported_at=row["paid_reported_at"],
        payment_confirmed_at=row["payment_confirmed_at"],
        delivered_at=row["delivered_at"],
        completed_at=row["completed_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def payment_report_from_row(row) -> PaymentReportRecord:  # type: ignore[no-untyped-def]
    return PaymentReportRecord(
        id=str(row["id"]),
        order_id=str(row["order_id"]),
        reported_by_user_id=str(row["reported_by_user_id"]),
        status=row["status"],
        idempotency_key=row["idempotency_key"],
        payment_type=row["payment_type"],
        payment_reference=row["payment_reference"],
        payment_sender_name=row["payment_sender_name"],
        payment_sender_account_masked=row["payment_sender_account_masked"],
        tx_hash=row["tx_hash"],
        network=row["network"],
        payment_amount=decimal_from_row_value(row["payment_amount"]),
        proof_file_id=str(row["proof_file_id"]) if row["proof_file_id"] else None,
        proof_content_sha256=optional_row_value(row, "proof_content_sha256"),
        report_payload_hash=row["report_payload_hash"],
        admin_notes=row["admin_notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def rating_from_row(row) -> RatingRecord:  # type: ignore[no-untyped-def]
    return RatingRecord(
        id=str(row["id"]),
        order_id=str(row["order_id"]),
        business_id=str(row["business_id"]),
        rater_user_id=str(row["rater_user_id"]),
        stars=int(row["stars"]),
        created_at=row["created_at"],
    )


def state_event_from_row(row) -> OrderStateEventRecord:  # type: ignore[no-untyped-def]
    return OrderStateEventRecord(
        id=str(row["id"]),
        order_id=str(row["order_id"]),
        from_status=row["from_status"],
        to_status=row["to_status"],
        event_type=row["event_type"],
        actor_user_id=str(row["actor_user_id"]) if row["actor_user_id"] else None,
        actor_role=row["actor_role"],
        reason=row["reason"],
        request_id=row["request_id"],
        metadata_json=row["metadata_json"],
        created_at=row["created_at"],
    )


def file_from_row(row) -> FileAssetRecord:  # type: ignore[no-untyped-def]
    return FileAssetRecord(
        id=str(row["id"]),
        owner_user_id=str(row["owner_user_id"]),
        resource_type=row["resource_type"],
        resource_id=str(row["resource_id"]),
        file_type=row["file_type"],
        storage_path=row["storage_path"],
        mime_type=row["mime_type"],
        size_bytes=row["size_bytes"],
        metadata_json=optional_row_value(row, "metadata_json"),
        created_at=row["created_at"],
        deleted_at=row["deleted_at"],
    )
