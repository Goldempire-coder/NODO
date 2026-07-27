from __future__ import annotations

from typing import Any

from app.modules.ads.models import AdRecord
from app.modules.ads.state_machine import is_expired
from app.modules.businesses.models import BusinessPaymentMethodRecord, BusinessRecord
from app.modules.businesses.presenters import decimal_text
from app.modules.businesses.reputation import public_reputation_payload


def ad_payload(
    ad: AdRecord,
    *,
    business: BusinessRecord | None = None,
    payment_method: BusinessPaymentMethodRecord | None = None,
    can_cover_requested_amount: bool | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": ad.id,
        "business_id": ad.business_id,
        "payment_method_id": ad.payment_method_id,
        "payment_method": ad.payment_method,
        "delivery_method": ad.delivery_method,
        "rate_bs_per_usd": decimal_text(ad.rate_bs_per_usd),
        "amount_min_usd": decimal_text(ad.amount_min_usd),
        "amount_max_usd": decimal_text(ad.amount_max_usd),
        "required_credits": ad.required_credits,
        "status": ad.status,
        "effective_status": "expired" if is_expired(ad) else ad.status,
        "created_at": ad.created_at.isoformat(),
        "updated_at": ad.updated_at.isoformat(),
        "activated_at": ad.activated_at.isoformat() if ad.activated_at else None,
        "expires_at": ad.expires_at.isoformat() if ad.expires_at else None,
    }
    if business is not None:
        payload["business"] = {
            "id": business.id,
            "business_name": business.business_name,
            "verification_status": business.verification_status,
            "availability": {
                "status": "online" if business.is_accepting_orders else "offline",
                "label": "Online" if business.is_accepting_orders else "Offline",
                **(
                    {"can_cover_requested_amount": can_cover_requested_amount}
                    if can_cover_requested_amount is not None
                    else {}
                ),
            },
            "rating_avg": decimal_text(business.rating_avg) if business.rating_avg is not None else None,
            "completed_orders_count": business.completed_orders_count,
            "reputation": public_reputation_payload(business),
        }
    if payment_method is not None:
        payload["payment_method_details"] = {
            "id": payment_method.id,
            "method_type": payment_method.method_type,
            "network": payment_method.network,
            "account_masked": payment_method.account_masked,
            "holder_name": payment_method.holder_name,
            "verified_status": payment_method.verified_status,
            "active": payment_method.active,
        }
    return payload
