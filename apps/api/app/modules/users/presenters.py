from __future__ import annotations

from app.modules.users.models import UserRecord


def public_user_payload(user: UserRecord) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "role": user.role,
        "status": user.status,
        "trust_level": user.trust_level,
        "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
        "terms_accepted_at": user.terms_accepted_at.isoformat() if user.terms_accepted_at else None,
        "terms_version": user.terms_version,
    }
