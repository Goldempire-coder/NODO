from __future__ import annotations

from typing import Any

from app.modules.ads.models import AdRecord
from app.modules.businesses.models import BusinessRecord
from app.modules.users.models import UserRecord


def ad_creation_audit_events(
    *,
    user: UserRecord,
    business: BusinessRecord,
    ad: AdRecord,
    founder_access_used: bool,
    request_id: str,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = [
        {
            "event_type": "ad_created",
            "actor_user_id": user.id,
            "actor_role": user.role,
            "resource_type": "ad",
            "resource_id": ad.id,
            "request_id": request_id,
        },
        {
            "event_type": "ad_published",
            "actor_user_id": user.id,
            "actor_role": user.role,
            "resource_type": "ad",
            "resource_id": ad.id,
            "request_id": request_id,
        },
    ]
    if ad.credit_hold_ledger_id:
        events.append(
            {
                "event_type": "credits_held",
                "actor_user_id": user.id,
                "actor_role": user.role,
                "resource_type": "ad",
                "resource_id": ad.id,
                "request_id": request_id,
                "metadata_json": {"ledger_id": ad.credit_hold_ledger_id, "amount": ad.required_credits},
            }
        )
    elif founder_access_used:
        events.append(
            {
                "event_type": "founder_free_use",
                "actor_user_id": user.id,
                "actor_role": user.role,
                "resource_type": "ad",
                "resource_id": ad.id,
                "request_id": request_id,
                "metadata_json": {"business_id": business.id, "required_credits": ad.required_credits},
            }
        )
    return events
