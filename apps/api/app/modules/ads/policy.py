from __future__ import annotations

from app.core.errors import ApiError
from app.modules.ads.publication_access import (
    business_can_receive_new_orders,
    require_ad_publication_access,
)
from app.modules.businesses.models import BusinessRecord
from app.modules.users.models import UserRecord


def require_marketplace_user(user: UserRecord) -> None:
    if user.role != "remitter" or user.status != "active":
        raise ApiError("FORBIDDEN", status_code=403)


def require_business_owner(user: UserRecord, business: BusinessRecord) -> None:
    if user.role != "business_owner" or business.owner_user_id != user.id:
        raise ApiError("FORBIDDEN", status_code=403)


def require_publishable_business(business: BusinessRecord) -> None:
    require_ad_publication_access(business)


def business_is_marketplace_visible(business: BusinessRecord) -> bool:
    return business_can_receive_new_orders(business)
