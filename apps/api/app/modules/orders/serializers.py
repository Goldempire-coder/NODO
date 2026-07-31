from __future__ import annotations

from typing import Any

from app.modules.businesses.presenters import decimal_text


def mask_tail(value: str | None, keep: int = 4) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if len(normalized) <= keep:
        return "*" * len(normalized)
    return f"***{normalized[-keep:]}"


def mask_tx_hash(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if len(normalized) <= 12:
        return mask_tail(normalized)
    return f"{normalized[:6]}...{normalized[-4:]}"


def order_capabilities(order, *, receiver_details_shared: bool = False) -> dict[str, bool]:  # type: ignore[no-untyped-def]
    return {
        "can_confirm_payment": order.status == "payment_reported",
        "can_reject_payment_report": order.status == "payment_reported",
        "can_mark_delivered": order.status == "payment_confirmed" and receiver_details_shared,
        "can_decline_before_payment": order.status == "waiting_payment",
        "receiver_details_shared": receiver_details_shared,
    }


def business_order_payload(order, *, list_view: bool = False, receiver_details_shared: bool = False) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    receiver = order.receiver_data_json or {}
    data = {
        "id": order.id,
        "public_order_code": order.public_order_code,
        "status": order.status,
        "cancel_reason": order.cancel_reason,
        "amount_usd": decimal_text(order.amount_usd),
        "amount_bs_calculated": decimal_text(order.amount_bs_calculated),
        "payment_method_snapshot": order.payment_method_snapshot,
        "delivery_method_snapshot": order.delivery_method_snapshot,
        "paid_reported_at": order.paid_reported_at.isoformat() if order.paid_reported_at else None,
        "payment_confirmed_at": order.payment_confirmed_at.isoformat() if order.payment_confirmed_at else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "business_response_warning_at": order.business_response_warning_at.isoformat() if order.business_response_warning_at else None,
        "business_response_deadline_at": order.business_response_deadline_at.isoformat() if order.business_response_deadline_at else None,
        "delivery_warning_at": order.delivery_warning_at.isoformat() if order.delivery_warning_at else None,
        "delivery_deadline_at": order.delivery_deadline_at.isoformat() if order.delivery_deadline_at else None,
        "auto_complete_at": order.auto_complete_at.isoformat() if order.auto_complete_at else None,
        "created_at": order.created_at.isoformat(),
        "capabilities": order_capabilities(order, receiver_details_shared=receiver_details_shared),
        "receiver_data_masked": {
            "bank": receiver.get("bank"),
            "phone": mask_tail(receiver.get("phone")),
            "document": mask_tail(receiver.get("document")),
            "holder": mask_tail(receiver.get("holder"), keep=2),
        },
    }
    return data


def business_receiver_payload(order) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    receiver = order.receiver_data_json or {}
    return {
        "bank": receiver.get("bank"),
        "phone_masked": mask_tail(receiver.get("phone")),
        "document_masked": mask_tail(receiver.get("document")),
        "holder": mask_tail(receiver.get("holder"), keep=2),
    }


def business_payment_report_payload(report) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    return {
        "id": report.id,
        "order_id": report.order_id,
        "status": report.status,
        "payment_type": report.payment_type,
        "payment_reference_masked": mask_tail(report.payment_reference),
        "tx_hash_masked": mask_tx_hash(report.tx_hash),
        "payment_amount": decimal_text(report.payment_amount),
        "proof_file_id": report.proof_file_id,
        "created_at": report.created_at.isoformat(),
    }


def public_order_payload(order, *, list_view: bool = False) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    receiver = order.receiver_data_json or {}
    payment = order.payment_instructions_snapshot or {}
    data = {
        "id": order.id,
        "public_order_code": order.public_order_code,
        "status": order.status,
        "amount_usd": decimal_text(order.amount_usd),
        "rate_snapshot": decimal_text(order.rate_snapshot),
        "amount_bs_calculated": decimal_text(order.amount_bs_calculated),
        "business_name": order.business_name_snapshot,
        "payment_method_snapshot": order.payment_method_snapshot,
        "delivery_method_snapshot": order.delivery_method_snapshot,
        "payment_instructions_masked": {
            "method_type": payment.get("method_type"),
            "network": payment.get("network"),
            "account_masked": payment.get("account_masked"),
        },
        "receiver_data_masked": {
            "bank": receiver.get("bank"),
            "phone": mask_tail(receiver.get("phone")),
            "document": mask_tail(receiver.get("document")),
            "holder": mask_tail(receiver.get("holder"), keep=2),
        },
        "payment_report_deadline_at": order.payment_report_deadline_at.isoformat(),
        "extension_used": order.extension_used,
        "expires_at": order.expires_at.isoformat(),
        "created_at": order.created_at.isoformat(),
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,
        "completion_reason": order.completion_reason,
        "can_view_payment_instructions": False,
    }
    if not list_view:
        data["limits_snapshot"] = {
            "min_amount_usd": decimal_text(order.min_amount_snapshot),
            "max_amount_usd": decimal_text(order.max_amount_snapshot),
        }
        data["cancel_reason"] = order.cancel_reason
    return data


def payment_report_payload(report) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    return {
        "id": report.id,
        "order_id": report.order_id,
        "status": report.status,
        "payment_type": report.payment_type,
        "payment_reference_masked": mask_tail(report.payment_reference),
        "tx_hash_masked": mask_tx_hash(report.tx_hash),
        "payment_amount": decimal_text(report.payment_amount),
        "proof_file_id": report.proof_file_id,
        "created_at": report.created_at.isoformat(),
    }


def payment_report_order_payload(order) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    return {
        "id": order.id,
        "public_order_code": order.public_order_code,
        "status": order.status,
        "paid_reported_at": order.paid_reported_at.isoformat() if order.paid_reported_at else None,
    }
