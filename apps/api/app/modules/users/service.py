from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.auth.jwt import create_access_token, create_refresh_token, hash_refresh_token
from app.auth.telegram import validate_telegram_init_data
from app.core.config import Settings
from app.core.errors import ApiError
from app.modules.users.auth_helpers import REFRESH_ALLOWED_STATUSES_BY_ROLE, hash_ip, safe_debug_payload
from app.modules.users.models import SessionRecord, UserRecord, utc_now
from app.modules.users.presenters import public_user_payload
from app.modules.users.repository import InMemoryUserRepository

__all__ = ["AuthService", "public_user_payload"]


class AuthService:
    def __init__(self, *, settings: Settings, repository: InMemoryUserRepository, audit_writer, rate_limiter) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._audit = audit_writer
        self._rate_limiter = rate_limiter

    def _require_auth_secrets(self) -> tuple[str, str, str]:
        if not self._settings.bot_token or not self._settings.jwt_secret or not self._settings.jwt_refresh_secret:
            raise ApiError("UNAUTHENTICATED", status_code=401)
        return self._settings.bot_token, self._settings.jwt_secret, self._settings.jwt_refresh_secret

    def _check_rate_limit(self, key: str) -> None:
        if not self._rate_limiter.allow(
            key,
            max_attempts=self._settings.auth_rate_limit_max_attempts,
            window_seconds=self._settings.auth_rate_limit_window_seconds,
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def login_with_telegram(self, *, init_data: str, request_id: str, ip_address: str | None, user_agent: str | None) -> dict:
        bot_token, jwt_secret, jwt_refresh_secret = self._require_auth_secrets()
        self._check_rate_limit(f"auth:{ip_address or 'unknown'}")
        telegram_user = self._validate_telegram_login(init_data=init_data, bot_token=bot_token, request_id=request_id)
        user, created = self._repository.upsert_telegram_user(
            telegram_id=telegram_user.telegram_id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
        )
        self._ensure_login_user_allowed(user=user, request_id=request_id)
        access_token, refresh_token = self._create_login_session(
            user=user,
            jwt_secret=jwt_secret,
            jwt_refresh_secret=jwt_refresh_secret,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._write_login_success_audit(user=user, created=created, request_id=request_id)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self._settings.access_token_ttl_seconds,
            "user": public_user_payload(user),
        }

    def _validate_telegram_login(self, *, init_data: str, bot_token: str, request_id: str) -> Any:
        try:
            return validate_telegram_init_data(
                init_data,
                bot_token,
                self._settings.auth_init_data_max_age_seconds,
            )
        except ApiError:
            self._audit.write(
                event_type="auth_failed",
                actor_user_id=None,
                actor_role=None,
                resource_type="auth",
                resource_id=None,
                request_id=request_id,
                metadata_json={"reason": "telegram_init_data_rejected"},
            )
            raise

    def _ensure_login_user_allowed(self, *, user: UserRecord, request_id: str) -> None:
        if user.status == "blocked":
            self._audit.write(
                event_type="auth_failed",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="user",
                resource_id=user.id,
                request_id=request_id,
                metadata_json={"reason": "user_blocked"},
            )
            raise ApiError("USER_SUSPENDED", status_code=403)

    def _create_login_session(
        self,
        *,
        user: UserRecord,
        jwt_secret: str,
        jwt_refresh_secret: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> tuple[str, str]:
        access_token, access_token_jti, _ = create_access_token(
            user_id=user.id,
            role=user.role,
            status=user.status,
            secret=jwt_secret,
            ttl_seconds=self._settings.access_token_ttl_seconds,
        )
        refresh_token = create_refresh_token()
        refresh_hash = hash_refresh_token(refresh_token, jwt_refresh_secret)
        self._repository.create_session(
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            access_token_jti=access_token_jti,
            expires_at=utc_now() + timedelta(seconds=self._settings.refresh_token_ttl_seconds),
            ip_hash=hash_ip(ip_address),
            user_agent=user_agent,
        )
        return access_token, refresh_token

    def _write_login_success_audit(self, *, user: UserRecord, created: bool, request_id: str) -> None:
        if created:
            self._audit.write(
                event_type="user_created",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="user",
                resource_id=user.id,
                request_id=request_id,
            )
        self._audit.write(
            event_type="user_login",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="user",
            resource_id=user.id,
            request_id=request_id,
        )

    def refresh(self, *, refresh_token: str, request_id: str) -> dict:
        _, jwt_secret, jwt_refresh_secret = self._require_auth_secrets()
        refresh_hash = hash_refresh_token(refresh_token, jwt_refresh_secret)
        session = self._repository.get_session_by_refresh_hash(refresh_hash)
        if session is None or session.status != "active" or self._repository.session_is_expired(session):
            raise ApiError("SESSION_EXPIRED", status_code=401)
        user = self._active_user_for_session(session)

        access_token, access_token_jti, _ = create_access_token(
            user_id=user.id,
            role=user.role,
            status=user.status,
            secret=jwt_secret,
            ttl_seconds=self._settings.access_token_ttl_seconds,
        )
        next_refresh_token = create_refresh_token()
        self._repository.rotate_session(
            session,
            refresh_token_hash=hash_refresh_token(next_refresh_token, jwt_refresh_secret),
            access_token_jti=access_token_jti,
            expires_at=utc_now() + timedelta(seconds=self._settings.refresh_token_ttl_seconds),
        )
        self._audit.write(
            event_type="session_refreshed",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="session",
            resource_id=session.id,
            request_id=request_id,
        )
        return {
            "access_token": access_token,
            "refresh_token": next_refresh_token,
            "token_type": "Bearer",
            "expires_in": self._settings.access_token_ttl_seconds,
        }

    def logout(self, *, refresh_token: str, user: UserRecord, request_id: str) -> dict:
        _, _, jwt_refresh_secret = self._require_auth_secrets()
        refresh_hash = hash_refresh_token(refresh_token, jwt_refresh_secret)
        session = self._repository.get_session_by_refresh_hash(refresh_hash)
        if session is not None and session.user_id == user.id and session.status != "revoked":
            self._repository.revoke_session(session)
        self._audit.write(
            event_type="user_logout",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="user",
            resource_id=user.id,
            request_id=request_id,
        )
        return {"logged_out": True}

    def _active_user_for_session(self, session: SessionRecord) -> UserRecord:
        user = self._repository.get_user_by_id(session.user_id)
        if user is None:
            raise ApiError("SESSION_EXPIRED", status_code=401)
        allowed_statuses = REFRESH_ALLOWED_STATUSES_BY_ROLE.get(user.role, {"active"})
        if user.status not in allowed_statuses:
            raise ApiError("USER_SUSPENDED", status_code=403)
        return user

    @staticmethod
    def safe_debug_payload(payload: dict) -> str:
        return safe_debug_payload(payload)
