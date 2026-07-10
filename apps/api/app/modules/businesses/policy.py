from __future__ import annotations

from app.core.errors import ApiError
from app.modules.businesses.models import BusinessRecord
from app.modules.users.models import UserRecord


ADMIN_MUTATION_ROLES = {"admin", "super_admin"}
ADMIN_VIEW_ROLES = {"admin", "super_admin", "support"}
OWNER_ELIGIBLE_ROLES = {"remitter", "business_owner"}


def require_owner_or_eligible(user: UserRecord) -> None:
    if user.role not in OWNER_ELIGIBLE_ROLES:
        raise ApiError("FORBIDDEN", status_code=403)


def require_business_owner(user: UserRecord, business: BusinessRecord) -> None:
    if business.owner_user_id != user.id:
        raise ApiError("FORBIDDEN", status_code=403)


def require_admin_view(user: UserRecord) -> None:
    if user.role not in ADMIN_VIEW_ROLES:
        raise ApiError("FORBIDDEN", status_code=403)


def require_admin_mutation(user: UserRecord) -> None:
    if user.role not in ADMIN_MUTATION_ROLES:
        raise ApiError("FORBIDDEN", status_code=403)
