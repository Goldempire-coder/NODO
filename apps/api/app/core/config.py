from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

SECRET_ENV_KEYS = {
    "BOT_TOKEN",
    "BUSINESS_INTAKE_BOT_TOKEN",
    "JWT_SECRET",
    "JWT_REFRESH_SECRET",
    "DATABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_JWT_SECRET",
    "REDIS_URL",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "STORAGE_ACCESS_KEY",
    "STORAGE_SECRET_KEY",
    "ADMIN_BOOTSTRAP_SECRET",
    "BASE_RPC_URL",
    "BASE_RPC_API_KEY",
}

REQUIRED_ENV_KEYS = ("APP_ENV", "APP_VERSION", "DATABASE_URL", "REDIS_URL")
SUPABASE_STORAGE_ENV_KEYS = ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")


class EnvValidationError(RuntimeError):
    def __init__(self, missing_keys: list[str]) -> None:
        self.missing_keys = missing_keys
        super().__init__(f"Missing required environment keys: {', '.join(missing_keys)}")


@dataclass(frozen=True)
class Settings:
    app_env: str
    app_name: str
    app_version: str
    build_id: str
    database_url: str
    redis_url: str
    bot_token: str | None
    business_intake_bot_token: str | None
    jwt_secret: str | None
    jwt_refresh_secret: str | None
    stripe_secret_key: str | None
    stripe_webhook_secret: str | None
    base_rpc_url: str | None
    base_rpc_api_key: str | None
    nodo_credit_receiving_wallet_base: str | None
    onchain_credit_min_confirmations: int
    onchain_credit_purchase_ttl_minutes: int
    onchain_credit_watcher_batch_size: int
    onchain_credit_watcher_timeout_seconds: int
    legacy_credit_payment_methods_enabled: bool
    auth_init_data_max_age_seconds: int
    access_token_ttl_seconds: int
    refresh_token_ttl_seconds: int
    auth_rate_limit_max_attempts: int
    auth_rate_limit_window_seconds: int
    business_rate_limit_max_attempts: int
    business_rate_limit_window_seconds: int
    marketplace_cache_ttl_seconds: int
    marketplace_cache_version_ttl_seconds: float
    marketplace_cache_shared_hit_local_ttl_seconds: int
    marketplace_read_auth_claim_ttl_seconds: int
    admin_read_model_cache_ttl_seconds: int
    auth_user_cache_ttl_seconds: int
    api_thread_limit: int
    observability_ingest_enabled: bool
    observability_max_events_per_batch: int
    observability_max_event_bytes: int
    order_notification_sender_enabled: bool
    order_notification_sender_interval_seconds: int
    order_notification_sender_batch_size: int
    private_storage_mode: str
    private_storage_root: str
    storage_signed_url_ttl_seconds: int
    supabase_url: str | None
    supabase_service_role_key: str | None
    supabase_storage_bucket_business_verification: str
    supabase_storage_bucket_payment_evidence: str
    supabase_storage_bucket_credit_purchase_proofs: str
    supabase_storage_bucket_message_attachments: str
    supabase_storage_bucket_business_intake: str
    telegram_web_app_url: str
    telegram_welcome_image_url: str
    cors_origins: list[str]


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _read_int(source: Mapping[str, str], key: str, default: int) -> int:
    raw_value = source.get(key)
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise EnvValidationError([key]) from exc
    if value <= 0:
        raise EnvValidationError([key])
    return value


def _read_bool(source: Mapping[str, str], key: str, default: bool) -> bool:
    raw_value = source.get(key)
    if raw_value is None or raw_value == "":
        return default
    return raw_value.strip().lower() in {"1", "true", "on", "yes"}


def validate_env(environ: Mapping[str, str] | None = None) -> None:
    source = environ or os.environ
    missing = [key for key in REQUIRED_ENV_KEYS if not source.get(key)]
    if source.get("PRIVATE_STORAGE_MODE") == "supabase":
        missing.extend(key for key in SUPABASE_STORAGE_ENV_KEYS if not source.get(key))
    if missing:
        raise EnvValidationError(missing)


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    source = environ or os.environ
    validate_env(source)
    return Settings(
        app_env=source.get("APP_ENV", "local"),
        app_name=source.get("APP_NAME", "NODO"),
        app_version=source["APP_VERSION"],
        build_id=source.get("NODO_BUILD_ID", "local"),
        database_url=source["DATABASE_URL"],
        redis_url=source["REDIS_URL"],
        bot_token=source.get("BOT_TOKEN") or None,
        business_intake_bot_token=source.get("BUSINESS_INTAKE_BOT_TOKEN") or None,
        jwt_secret=source.get("JWT_SECRET") or None,
        jwt_refresh_secret=source.get("JWT_REFRESH_SECRET") or None,
        stripe_secret_key=source.get("STRIPE_SECRET_KEY") or None,
        stripe_webhook_secret=source.get("STRIPE_WEBHOOK_SECRET") or None,
        base_rpc_url=source.get("BASE_RPC_URL") or None,
        base_rpc_api_key=source.get("BASE_RPC_API_KEY") or None,
        nodo_credit_receiving_wallet_base=source.get("NODO_CREDIT_RECEIVING_WALLET_BASE") or None,
        onchain_credit_min_confirmations=_read_int(source, "ONCHAIN_CREDIT_MIN_CONFIRMATIONS", 6),
        onchain_credit_purchase_ttl_minutes=_read_int(source, "ONCHAIN_CREDIT_PURCHASE_TTL_MINUTES", 30),
        onchain_credit_watcher_batch_size=_read_int(source, "ONCHAIN_CREDIT_WATCHER_BATCH_SIZE", 50),
        onchain_credit_watcher_timeout_seconds=_read_int(source, "ONCHAIN_CREDIT_WATCHER_TIMEOUT_SECONDS", 10),
        legacy_credit_payment_methods_enabled=_read_bool(source, "LEGACY_CREDIT_PAYMENT_METHODS_ENABLED", False),
        auth_init_data_max_age_seconds=_read_int(source, "AUTH_INIT_DATA_MAX_AGE_SECONDS", 86400),
        access_token_ttl_seconds=_read_int(source, "ACCESS_TOKEN_TTL_SECONDS", 900),
        refresh_token_ttl_seconds=_read_int(source, "REFRESH_TOKEN_TTL_SECONDS", 2_592_000),
        auth_rate_limit_max_attempts=_read_int(source, "AUTH_RATE_LIMIT_MAX_ATTEMPTS", 10),
        auth_rate_limit_window_seconds=_read_int(source, "AUTH_RATE_LIMIT_WINDOW_SECONDS", 60),
        business_rate_limit_max_attempts=_read_int(source, "BUSINESS_RATE_LIMIT_MAX_ATTEMPTS", 30),
        business_rate_limit_window_seconds=_read_int(source, "BUSINESS_RATE_LIMIT_WINDOW_SECONDS", 60),
        marketplace_cache_ttl_seconds=_read_int(source, "MARKETPLACE_CACHE_TTL_SECONDS", 30),
        marketplace_cache_version_ttl_seconds=float(source.get("MARKETPLACE_CACHE_VERSION_TTL_SECONDS", "1")),
        marketplace_cache_shared_hit_local_ttl_seconds=_read_int(source, "MARKETPLACE_CACHE_SHARED_HIT_LOCAL_TTL_SECONDS", 5),
        marketplace_read_auth_claim_ttl_seconds=_read_int(source, "MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS", 300),
        admin_read_model_cache_ttl_seconds=_read_int(source, "ADMIN_READ_MODEL_CACHE_TTL_SECONDS", 5),
        auth_user_cache_ttl_seconds=_read_int(source, "AUTH_USER_CACHE_TTL_SECONDS", 2),
        api_thread_limit=_read_int(source, "API_THREAD_LIMIT", 40),
        observability_ingest_enabled=_read_bool(source, "OBSERVABILITY_INGEST_ENABLED", False),
        observability_max_events_per_batch=_read_int(source, "OBSERVABILITY_MAX_EVENTS_PER_BATCH", 20),
        observability_max_event_bytes=_read_int(source, "OBSERVABILITY_MAX_EVENT_BYTES", 2048),
        order_notification_sender_enabled=_read_bool(source, "ORDER_NOTIFICATION_SENDER_ENABLED", source.get("APP_ENV") != "test"),
        order_notification_sender_interval_seconds=_read_int(source, "ORDER_NOTIFICATION_SENDER_INTERVAL_SECONDS", 10),
        order_notification_sender_batch_size=_read_int(source, "ORDER_NOTIFICATION_SENDER_BATCH_SIZE", 50),
        private_storage_mode=source.get("PRIVATE_STORAGE_MODE", "unavailable"),
        private_storage_root=source.get("PRIVATE_STORAGE_ROOT", ".local/private_storage"),
        storage_signed_url_ttl_seconds=_read_int(source, "STORAGE_SIGNED_URL_TTL_SECONDS", 300),
        supabase_url=(source.get("SUPABASE_URL") or "").rstrip("/") or None,
        supabase_service_role_key=source.get("SUPABASE_SERVICE_ROLE_KEY") or None,
        supabase_storage_bucket_business_verification=source.get(
            "SUPABASE_STORAGE_BUCKET_BUSINESS_VERIFICATION",
            "business-verification",
        ),
        supabase_storage_bucket_payment_evidence=source.get(
            "SUPABASE_STORAGE_BUCKET_PAYMENT_EVIDENCE",
            "payment-evidence",
        ),
        supabase_storage_bucket_credit_purchase_proofs=source.get(
            "SUPABASE_STORAGE_BUCKET_CREDIT_PURCHASE_PROOFS",
            "credit-purchase-proofs",
        ),
        supabase_storage_bucket_message_attachments=source.get(
            "SUPABASE_STORAGE_BUCKET_MESSAGE_ATTACHMENTS",
            "message-attachments",
        ),
        supabase_storage_bucket_business_intake=source.get(
            "SUPABASE_STORAGE_BUCKET_BUSINESS_INTAKE",
            "business-intake",
        ),
        telegram_web_app_url=source.get("TELEGRAM_WEB_APP_URL", "https://nodo-staging.pages.dev").rstrip("/"),
        telegram_welcome_image_url=source.get(
            "TELEGRAM_WELCOME_IMAGE_URL",
            "https://main.nodo-staging.pages.dev/telegram-welcome.jpg?v=20260707170427",
        ),
        cors_origins=_split_csv(source.get("API_CORS_ORIGINS", "http://localhost:3000")),
    )


def redact_env_value(key: str, value: str | None) -> str | None:
    if value is None:
        return None
    if key.upper() in SECRET_ENV_KEYS:
        return "[REDACTED]"
    return value
