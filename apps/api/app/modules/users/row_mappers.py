from __future__ import annotations

from app.modules.users.models import AdminCredentialRecord, SessionRecord, UserRecord


def user_from_row(row) -> UserRecord:  # type: ignore[no-untyped-def]
    admin_alert_telegram_id = row["admin_alert_telegram_id"] if "admin_alert_telegram_id" in row.keys() else None
    return UserRecord(
        id=str(row["id"]),
        telegram_id=int(row["telegram_id"]) if row["telegram_id"] is not None else None,
        username=row["username"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        admin_alert_telegram_id=int(admin_alert_telegram_id) if admin_alert_telegram_id is not None else None,
        phone=row["phone"],
        role=row["role"],
        status=row["status"],
        trust_level=row["trust_level"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        last_seen_at=row["last_seen_at"],
        terms_accepted_at=row["terms_accepted_at"],
        terms_version=row["terms_version"],
    )


def admin_credential_from_row(row) -> AdminCredentialRecord:  # type: ignore[no-untyped-def]
    return AdminCredentialRecord(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        username=row["username"],
        username_normalized=row["username_normalized"],
        password_hash=row["password_hash"],
        status=row["status"],
        failed_attempts=int(row["failed_attempts"]),
        locked_until=row["locked_until"],
        last_login_at=row["last_login_at"],
        password_changed_at=row["password_changed_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def session_from_row(row) -> SessionRecord:  # type: ignore[no-untyped-def]
    return SessionRecord(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        refresh_token_hash=row["refresh_token_hash"],
        status=row["status"],
        access_token_jti=row["access_token_jti"],
        expires_at=row["expires_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        revoked_at=row["revoked_at"],
        last_used_at=row["last_used_at"],
        ip_hash=row["ip_hash"],
        user_agent=row["user_agent"],
    )
