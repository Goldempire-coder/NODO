from __future__ import annotations

from app.core.errors import ApiError
from app.modules.users.models import UserRecord

CURRENT_TERMS_VERSION = "2026-07-06"


def user_has_current_terms(user: UserRecord) -> bool:
    return bool(user.terms_accepted_at and user.terms_version == CURRENT_TERMS_VERSION)


def require_current_terms(user: UserRecord) -> None:
    if user_has_current_terms(user):
        return
    raise ApiError(
        "TERMS_ACCEPTANCE_REQUIRED",
        "Debes aceptar los terminos vigentes de NODO para continuar.",
        status_code=403,
    )
