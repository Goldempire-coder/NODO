from __future__ import annotations

from app.core.errors import ApiError
from app.modules.users.models import UserRecord


def require_admin_read(user: UserRecord) -> None:
    if user.status != "active" or user.role not in {"admin", "super_admin", "support"}:
        raise ApiError("FORBIDDEN", status_code=403)


def require_admin_mutation(user: UserRecord) -> None:
    if user.status != "active" or user.role not in {"admin", "super_admin"}:
        raise ApiError("FORBIDDEN", status_code=403)
