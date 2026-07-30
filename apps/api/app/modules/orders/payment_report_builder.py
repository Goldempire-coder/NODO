from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.errors import ApiError
from app.modules.businesses.models import FileAssetRecord
from app.modules.orders.integrity import PAYMENT_PROOF_CONTENT_SHA256_PATTERN
from app.modules.orders.models import OrderRecord, new_id
from app.modules.orders.schemas import PaymentReportRequest
from app.modules.orders.serializers import mask_tail, mask_tx_hash
from app.modules.users.models import UserRecord


def require_uuid(value: str | None, error_code: str) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(value))
    except (TypeError, ValueError) as exc:
        raise ApiError(error_code, status_code=400 if error_code != "ORDER_NOT_FOUND" else 404) from exc


@dataclass(frozen=True)
class PaymentReportPlan:
    report_id: str
    proof_file_id: str | None
    proof_content_sha256: str | None
    create_report_fields: dict[str, Any]


def build_payment_report_plan(
    *,
    user: UserRecord,
    order: OrderRecord,
    payload: PaymentReportRequest,
    payload_hash: str,
    idempotency_key: str,
    proof_lookup: Callable[[str], FileAssetRecord | None],
) -> PaymentReportPlan:
    require_matching_payment_method(payload=payload, order=order)
    proof_file_id, report_id, proof_content_sha256 = resolve_payment_report_identity(
        user=user,
        order_id=order.id,
        payload=payload,
        proof_lookup=proof_lookup,
    )

    return PaymentReportPlan(
        report_id=report_id,
        proof_file_id=proof_file_id,
        proof_content_sha256=proof_content_sha256,
        create_report_fields=build_create_payment_report_fields(
            user=user,
            order=order,
            payload=payload,
            payload_hash=payload_hash,
            idempotency_key=idempotency_key,
            report_id=report_id,
            proof_file_id=proof_file_id,
            proof_content_sha256=proof_content_sha256,
        ),
    )


def require_matching_payment_method(*, payload: PaymentReportRequest, order: OrderRecord) -> None:
    if payload.payment_type != order.payment_method_snapshot:
        raise ApiError("INVALID_PAYMENT_METHOD", status_code=400)


def resolve_payment_report_identity(
    *,
    user: UserRecord,
    order_id: str,
    payload: PaymentReportRequest,
    proof_lookup: Callable[[str], FileAssetRecord | None],
) -> tuple[str | None, str, str | None]:
    proof_file_id = require_uuid(payload.proof_file_id, "INVALID_PAYMENT_EVIDENCE")
    pending_payment_report_id = require_uuid(payload.pending_payment_report_id, "INVALID_PAYMENT_EVIDENCE")
    report_id = pending_payment_report_id or new_id()
    if payload.payment_type == "zelle":
        report_id, proof_content_sha256 = require_zelle_evidence(
            user=user,
            order_id=order_id,
            proof_file_id=proof_file_id,
            pending_payment_report_id=pending_payment_report_id,
            proof_lookup=proof_lookup,
        )
        return proof_file_id, report_id, proof_content_sha256
    if proof_file_id:
        report_id, proof_content_sha256 = resolve_optional_payment_evidence(
            user=user,
            order_id=order_id,
            proof_file_id=proof_file_id,
            pending_payment_report_id=pending_payment_report_id,
            proof_lookup=proof_lookup,
        )
        return proof_file_id, report_id, proof_content_sha256
    return proof_file_id, report_id, None


def require_zelle_evidence(
    *,
    user: UserRecord,
    order_id: str,
    proof_file_id: str | None,
    pending_payment_report_id: str | None,
    proof_lookup: Callable[[str], FileAssetRecord | None],
) -> tuple[str, str]:
    if not proof_file_id or not pending_payment_report_id:
        raise ApiError("PAYMENT_EVIDENCE_REQUIRED", status_code=400)
    proof = proof_lookup(proof_file_id)
    if proof is None or proof.owner_user_id != user.id or proof.resource_id != pending_payment_report_id:
        raise ApiError("INVALID_PAYMENT_EVIDENCE", status_code=400)
    require_payment_evidence_order(proof=proof, order_id=order_id)
    return pending_payment_report_id, require_payment_evidence_content_hash(proof)


def resolve_optional_payment_evidence(
    *,
    user: UserRecord,
    order_id: str,
    proof_file_id: str,
    pending_payment_report_id: str | None,
    proof_lookup: Callable[[str], FileAssetRecord | None],
) -> tuple[str, str]:
    proof = proof_lookup(proof_file_id)
    if proof is None or proof.owner_user_id != user.id:
        raise ApiError("INVALID_PAYMENT_EVIDENCE", status_code=400)
    if pending_payment_report_id and proof.resource_id != pending_payment_report_id:
        raise ApiError("INVALID_PAYMENT_EVIDENCE", status_code=400)
    require_payment_evidence_order(proof=proof, order_id=order_id)
    return pending_payment_report_id or proof.resource_id, require_payment_evidence_content_hash(proof)


def require_payment_evidence_order(*, proof: FileAssetRecord, order_id: str) -> None:
    proof_order_id = (proof.metadata_json or {}).get("order_id")
    if proof_order_id != order_id:
        raise ApiError("INVALID_PAYMENT_EVIDENCE", status_code=400)


def require_payment_evidence_content_hash(proof: FileAssetRecord) -> str:
    content_sha256 = (proof.metadata_json or {}).get("content_sha256")
    if not isinstance(content_sha256, str) or not PAYMENT_PROOF_CONTENT_SHA256_PATTERN.fullmatch(content_sha256):
        raise ApiError("INVALID_PAYMENT_EVIDENCE", status_code=400)
    return content_sha256


def build_create_payment_report_fields(
    *,
    user: UserRecord,
    order: OrderRecord,
    payload: PaymentReportRequest,
    payload_hash: str,
    idempotency_key: str,
    report_id: str,
    proof_file_id: str | None,
    proof_content_sha256: str | None,
) -> dict[str, Any]:
    return {
        "report_id": report_id,
        "order_id": order.id,
        "reported_by_user_id": user.id,
        "idempotency_key": idempotency_key,
        "payment_type": payload.payment_type,
        "payment_reference": payload.payment_reference,
        "payment_sender_name": payload.payment_sender_name,
        "payment_sender_account_masked": payload.payment_sender_account_masked,
        "tx_hash": payload.tx_hash,
        "network": payload.network,
        "payment_amount": payload.payment_amount,
        "proof_file_id": proof_file_id,
        "proof_content_sha256": proof_content_sha256,
        "report_payload_hash": payload_hash,
    }


def payment_report_plan_state_metadata(
    plan: PaymentReportPlan,
    *,
    idempotency_key: str,
) -> dict[str, Any]:
    return {
        "payment_report_id": plan.report_id,
        "payment_type": plan.create_report_fields["payment_type"],
        "idempotency_key": idempotency_key,
    }


def payment_report_plan_audit_metadata(plan: PaymentReportPlan) -> dict[str, Any]:
    fields = plan.create_report_fields
    return {
        "payment_report_id": plan.report_id,
        "payment_type": fields["payment_type"],
        "payment_reference_masked": mask_tail(fields.get("payment_reference")),
        "tx_hash_masked": mask_tx_hash(fields.get("tx_hash")),
        "proof_file_id": plan.proof_file_id,
    }
