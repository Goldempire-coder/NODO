from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.modules.businesses.models import (
    BusinessAccessLinkRecord,
    BusinessPaymentMethodRecord,
    BusinessRecord,
    FileAssetRecord,
)


def mask_rif(value: str | None) -> str | None:
    if not value:
        return None
    compact = value.replace(" ", "")
    return f"{compact[:2]}***{compact[-3:]}" if len(compact) > 5 else "***"


def mask_phone(value: str | None) -> str | None:
    if not value:
        return None
    return f"{value[:3]}*******{value[-3:]}" if len(value) > 6 else "***"


def mask_account(value: str) -> str:
    return f"***{value[-4:]}" if len(value) > 4 else "***"


def decimal_text(value: Decimal) -> str:
    return f"{value:.2f}"


def payment_method_display(method: BusinessPaymentMethodRecord, *, business: BusinessRecord) -> dict[str, str | bool | dict[str, str] | None]:
    receive_display = "USDT TRC20" if method.method_type == "usdt_trc20" else "Zelle"
    delivery_display = "Pago Móvil"
    delivery_currency = "Bs."
    return {
        "id": method.id,
        "label": f"Recibo {receive_display} → Entrego {delivery_display} {delivery_currency}",
        "receive_method": method.method_type,
        "delivery_method": "pago_movil_ve",
        "receive_display": receive_display,
        "delivery_display": delivery_display,
        "delivery_currency": delivery_currency,
        "status": method.verified_status,
        "is_available": method.active and method.verified_status == "approved",
        "limits": {
            "min_amount_usd": "20.00",
            "max_amount_usd": decimal_text(business.max_order_amount_usd),
        },
        "masked_account": method.account_masked,
    }


def business_payload(business: BusinessRecord, *, admin: bool = False) -> dict[str, Any]:
    return {
        "id": business.id,
        "owner_user_id": business.owner_user_id,
        "business_name": business.business_name,
        "rif": business.rif if admin else mask_rif(business.rif),
        "address": business.address if admin else business.address,
        "phone": business.phone if admin else mask_phone(business.phone),
        "country": business.country,
        "verification_status": business.verification_status,
        "trust_level": business.trust_level,
        "risk_level": business.risk_level,
        "max_order_amount_usd": decimal_text(business.max_order_amount_usd),
        "daily_limit_usd": decimal_text(business.daily_limit_usd),
        "active_order_limit": business.active_order_limit,
        "approved_at": business.approved_at.isoformat() if business.approved_at else None,
        "created_at": business.created_at.isoformat(),
        "updated_at": business.updated_at.isoformat(),
    }


def file_payload(file: FileAssetRecord) -> dict[str, Any]:
    return {
        "id": file.id,
        "file_type": file.file_type,
        "mime_type": file.mime_type,
        "size_bytes": file.size_bytes,
        "created_at": file.created_at.isoformat(),
    }


def access_link_payload(link: BusinessAccessLinkRecord) -> dict[str, Any]:
    return {
        "id": link.id,
        "business_id": link.business_id,
        "user_id": link.user_id,
        "telegram_id_snapshot": link.telegram_id_snapshot,
        "role_in_business": link.role_in_business,
        "status": link.status,
        "linked_by_admin_id": link.linked_by_admin_id,
        "linked_at": link.linked_at.isoformat(),
        "suspended_at": link.suspended_at.isoformat() if link.suspended_at else None,
        "blocked_at": link.blocked_at.isoformat() if link.blocked_at else None,
        "revoked_at": link.revoked_at.isoformat() if link.revoked_at else None,
        "reason": link.reason,
        "created_at": link.created_at.isoformat(),
        "updated_at": link.updated_at.isoformat(),
    }
