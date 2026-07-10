from __future__ import annotations

import hmac

from app.core.errors import ApiError
from app.modules.users.models import UserRecord
from app.routes.telegram_bot import telegram_webhook_secret


def require_bot_secret(*, provided_secret: str | None, bot_token: str | None) -> None:
    if not bot_token:
        raise ApiError("TELEGRAM_BOT_NOT_CONFIGURED", status_code=503)
    if not provided_secret or not hmac.compare_digest(provided_secret, telegram_webhook_secret(bot_token)):
        raise ApiError("FORBIDDEN", status_code=403)


def require_admin_read(user: UserRecord) -> None:
    if user.status != "active" or user.role not in {"admin", "super_admin", "support"}:
        raise ApiError("FORBIDDEN", status_code=403)


def require_admin_mutation(user: UserRecord) -> None:
    if user.status != "active" or user.role not in {"admin", "super_admin"}:
        raise ApiError("FORBIDDEN", status_code=403)
