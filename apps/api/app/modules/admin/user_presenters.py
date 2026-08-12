from __future__ import annotations

from typing import Any


def mask_phone(value: str | None) -> str | None:
    if not value:
        return None
    compact = value.strip()
    return f"{compact[:3]}*******{compact[-3:]}" if len(compact) > 6 else "***"


def mask_telegram_id(value: int | str | None) -> str | None:
    if value is None:
        return None
    text = str(value)
    return f"{text[:2]}***{text[-3:]}" if len(text) > 5 else "***"


def admin_user_payload(row: dict[str, Any], *, full_sensitive: bool) -> dict[str, Any]:
    telegram_id = row.get("telegram_id")
    phone = row.get("phone")
    return {
        "id": str(row["id"]),
        "username": row.get("username"),
        "first_name": row.get("first_name"),
        "last_name": row.get("last_name"),
        "phone": None,
        "phone_masked": mask_phone(phone),
        "telegram_id": int(telegram_id) if full_sensitive and telegram_id is not None else None,
        "telegram_id_masked": mask_telegram_id(telegram_id),
        "role": row.get("role"),
        "status": row.get("status"),
        "trust_level": row.get("trust_level"),
        "terms_accepted_at": row["terms_accepted_at"].isoformat() if row.get("terms_accepted_at") else None,
        "terms_version": row.get("terms_version"),
        "last_seen_at": row["last_seen_at"].isoformat() if row.get("last_seen_at") else None,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


def admin_business_link_payload(row: dict[str, Any], *, full_sensitive: bool) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "business_id": str(row["business_id"]),
        "user_id": str(row["user_id"]),
        "telegram_id": int(row["telegram_id_snapshot"]) if full_sensitive and row.get("telegram_id_snapshot") is not None else None,
        "telegram_id_masked": mask_telegram_id(row.get("telegram_id_snapshot")),
        "role_in_business": row["role_in_business"],
        "status": row["status"],
        "reason": row.get("reason"),
        "linked_by_admin_id": str(row["linked_by_admin_id"]) if row.get("linked_by_admin_id") else None,
        "linked_at": row["linked_at"].isoformat() if row.get("linked_at") else None,
        "suspended_at": row["suspended_at"].isoformat() if row.get("suspended_at") else None,
        "blocked_at": row["blocked_at"].isoformat() if row.get("blocked_at") else None,
        "revoked_at": row["revoked_at"].isoformat() if row.get("revoked_at") else None,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
        "user": {
            "id": str(row["user_id"]) if row.get("user_id") else None,
            "username": row.get("username"),
            "first_name": row.get("first_name"),
            "phone_masked": mask_phone(row.get("phone")),
            "telegram_id_masked": mask_telegram_id(row.get("user_telegram_id")),
            "role": row.get("user_role"),
            "status": row.get("user_status"),
        },
        "business": {
            "id": str(row["business_id"]) if row.get("business_id") else None,
            "business_name": row.get("business_name"),
            "verification_status": row.get("verification_status"),
            "risk_level": row.get("risk_level"),
        },
    }
