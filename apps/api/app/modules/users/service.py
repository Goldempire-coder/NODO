from __future__ import annotations

import json
import hashlib
import time
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qsl

from app.auth.jwt import create_access_token, create_refresh_token, hash_refresh_token
from app.auth.telegram import validate_telegram_init_data
from app.core.config import Settings
from app.core.errors import ApiError
from app.modules.users.admin_passwords import dummy_admin_password_hash, normalize_admin_username, verify_admin_password
from app.modules.users.auth_helpers import REFRESH_ALLOWED_STATUSES_BY_ROLE, hash_ip, safe_debug_payload
from app.modules.users.models import SessionRecord, UserRecord, utc_now
from app.modules.users.presenters import public_user_payload
from app.modules.users.repository import InMemoryUserRepository

__all__ = ["AuthService", "public_user_payload"]


ADMIN_LOGIN_ROLES = {"admin", "super_admin", "support"}
ADMIN_LOGIN_ATTEMPT_LIMIT = 5
ADMIN_LOGIN_WAIT_MINUTES = 15


class AuthService:
    def __init__(self, *, settings: Settings, repository: InMemoryUserRepository, audit_writer, rate_limiter) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._audit = audit_writer
        self._rate_limiter = rate_limiter

    def _require_session_secrets(self) -> tuple[str, str]:
        if not self._settings.jwt_secret or not self._settings.jwt_refresh_secret:
            raise ApiError("UNAUTHENTICATED", status_code=401)
        return self._settings.jwt_secret, self._settings.jwt_refresh_secret

    def _require_telegram_auth_secrets(self) -> tuple[str, str, str]:
        if not self._settings.bot_token:
            raise ApiError("UNAUTHENTICATED", status_code=401)
        jwt_secret, jwt_refresh_secret = self._require_session_secrets()
        return self._settings.bot_token, jwt_secret, jwt_refresh_secret

    def _check_rate_limit(self, key: str) -> None:
        if not self._rate_limiter.allow(
            key,
            max_attempts=self._settings.auth_rate_limit_max_attempts,
            window_seconds=self._settings.auth_rate_limit_window_seconds,
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def login_with_telegram(
        self,
        *,
        init_data: str,
        surface: str | None = None,
        request_id: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> dict:
        bot_token, jwt_secret, jwt_refresh_secret = self._require_telegram_auth_secrets()
        self._check_rate_limit(f"auth:{ip_address or 'unknown'}")
        telegram_user = self._validate_telegram_login(
            init_data=init_data,
            bot_tokens=self._telegram_auth_bot_tokens(default_bot_token=bot_token, surface=surface),
            request_id=request_id,
        )
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

    def login_with_admin_credentials(
        self,
        *,
        username: str,
        password: str,
        request_id: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> dict:
        jwt_secret, jwt_refresh_secret = self._require_session_secrets()
        self._check_rate_limit(f"auth:admin:ip:{ip_address or 'unknown'}")
        try:
            username_normalized = normalize_admin_username(username)
        except ValueError as exc:
            self._write_admin_login_failed_audit(username=username, user=None, request_id=request_id, reason="invalid_credentials")
            raise ApiError("ADMIN_LOGIN_INVALID", status_code=401) from exc
        self._check_rate_limit(f"auth:admin:user:{username_normalized}")

        credential = self._repository.get_admin_credential_by_username(username_normalized)
        if credential is None:
            verify_admin_password(password, dummy_admin_password_hash())
            self._write_admin_login_failed_audit(username=username_normalized, user=None, request_id=request_id, reason="invalid_credentials")
            raise ApiError("ADMIN_LOGIN_INVALID", status_code=401)
        if credential.locked_until is not None and credential.locked_until > utc_now():
            self._write_admin_login_failed_audit(username=username_normalized, user=None, request_id=request_id, reason="credential_locked")
            raise ApiError("RATE_LIMITED", status_code=429)
        user = self._repository.get_user_by_id(credential.user_id)
        if not verify_admin_password(password, credential.password_hash):
            self._repository.record_admin_credential_failure(
                credential,
                attempt_limit=ADMIN_LOGIN_ATTEMPT_LIMIT,
                minutes=ADMIN_LOGIN_WAIT_MINUTES,
            )
            self._write_admin_login_failed_audit(username=username_normalized, user=user, request_id=request_id, reason="invalid_credentials")
            raise ApiError("ADMIN_LOGIN_INVALID", status_code=401)
        if user is None or user.role not in ADMIN_LOGIN_ROLES or user.status != "active" or credential.status != "active":
            self._write_admin_login_failed_audit(username=username_normalized, user=user, request_id=request_id, reason="not_allowed")
            raise ApiError("ADMIN_LOGIN_INVALID", status_code=401)

        access_token, refresh_token = self._create_login_session(
            user=user,
            jwt_secret=jwt_secret,
            jwt_refresh_secret=jwt_refresh_secret,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._repository.record_admin_credential_success(credential)
        self._audit.write(
            event_type="admin_login",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="user",
            resource_id=user.id,
            request_id=request_id,
            metadata_json={"surface": "admin_web", "username_hash": self._hash_admin_username(username_normalized)},
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self._settings.access_token_ttl_seconds,
            "user": public_user_payload(user),
        }

    def _write_admin_login_failed_audit(self, *, username: str, user: UserRecord | None, request_id: str, reason: str) -> None:
        self._audit.write(
            event_type="admin_login_failed",
            actor_user_id=user.id if user else None,
            actor_role=user.role if user else None,
            resource_type="auth",
            resource_id=user.id if user else None,
            request_id=request_id,
            metadata_json={"reason": reason, "surface": "admin_web", "username_hash": self._hash_admin_username(username)},
        )

    @staticmethod
    def _hash_admin_username(username: str) -> str:
        return hashlib.sha256(username.strip().lower().encode("utf-8")).hexdigest()[:16]

    def _telegram_auth_bot_tokens(self, *, default_bot_token: str, surface: str | None) -> list[str]:
        tokens = [default_bot_token]
        if surface == "business_mini_app" and self._settings.business_intake_bot_token:
            tokens.append(self._settings.business_intake_bot_token)
        return list(dict.fromkeys(tokens))

    def _validate_telegram_login(self, *, init_data: str, bot_tokens: list[str], request_id: str) -> Any:
        last_error: ApiError | None = None
        for bot_token in bot_tokens:
            try:
                return validate_telegram_init_data(
                    init_data,
                    bot_token,
                    self._settings.auth_init_data_max_age_seconds,
                )
            except ApiError as exc:
                last_error = exc
        self._audit.write(
            event_type="auth_failed",
            actor_user_id=None,
            actor_role=None,
            resource_type="auth",
            resource_id=None,
            request_id=request_id,
            metadata_json={
                "reason": "telegram_init_data_rejected",
                "last_error_code": last_error.code if last_error is not None else None,
                "token_attempts": len(bot_tokens),
                "init_data": self._safe_init_data_diagnostics(init_data),
            },
        )
        if last_error is not None:
            raise last_error
        raise ApiError("TELEGRAM_INIT_DATA_INVALID", status_code=401)

    def _safe_init_data_diagnostics(self, init_data: str) -> dict[str, Any]:
        diagnostics: dict[str, Any] = {
            "length": len(init_data or ""),
            "keys": [],
            "has_hash": False,
            "has_user": False,
            "has_auth_date": False,
        }
        try:
            pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
        except ValueError:
            diagnostics["parse_error"] = True
            return diagnostics

        keys = sorted(pairs)
        diagnostics["keys"] = keys
        diagnostics["has_hash"] = "hash" in pairs
        diagnostics["has_user"] = "user" in pairs
        diagnostics["has_auth_date"] = "auth_date" in pairs
        if "auth_date" in pairs:
            try:
                auth_date = int(pairs["auth_date"])
                diagnostics["auth_age_seconds"] = int(time.time()) - auth_date
                diagnostics["auth_date_in_future"] = auth_date > int(time.time()) + 60
            except ValueError:
                diagnostics["auth_date_invalid"] = True
        if "user" in pairs:
            try:
                user_payload = json.loads(pairs["user"])
                diagnostics["telegram_user_id"] = int(user_payload["id"])
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                diagnostics["user_parse_error"] = True
        return diagnostics

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

    def refresh(self, *, refresh_token: str, request_id: str, ip_address: str | None = None) -> dict:
        self._check_rate_limit(f"auth:refresh:ip:{ip_address or 'unknown'}")
        jwt_secret, jwt_refresh_secret = self._require_session_secrets()
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
        rotated = self._repository.rotate_session_if_current(
            session,
            current_refresh_token_hash=refresh_hash,
            refresh_token_hash=hash_refresh_token(next_refresh_token, jwt_refresh_secret),
            access_token_jti=access_token_jti,
            expires_at=utc_now() + timedelta(seconds=self._settings.refresh_token_ttl_seconds),
        )
        if not rotated:
            raise ApiError("SESSION_EXPIRED", status_code=401)
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

    def logout(self, *, refresh_token: str, request_id: str, ip_address: str | None = None) -> dict:
        self._check_rate_limit(f"auth:logout:ip:{ip_address or 'unknown'}")
        _, jwt_refresh_secret = self._require_session_secrets()
        refresh_hash = hash_refresh_token(refresh_token, jwt_refresh_secret)
        session = self._repository.get_session_by_refresh_hash(refresh_hash)
        user = self._repository.get_user_by_id(session.user_id) if session is not None else None
        if session is not None and session.status != "revoked":
            self._repository.revoke_session(session)
        self._audit.write(
            event_type="user_logout",
            actor_user_id=user.id if user else None,
            actor_role=user.role if user else None,
            resource_type="user",
            resource_id=user.id if user else None,
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
