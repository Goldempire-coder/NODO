import os
import traceback
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from threading import RLock

import anyio
import anyio.to_thread
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.core.config import admin_telegram_alerts_configured, load_settings
from app.core.errors import ApiError, api_error_response
from app.core.logging import configure_logging, get_logger
from app.modules.admin_notifications import AdminNotificationService, InMemoryAdminNotificationRepository, PostgresAdminNotificationRepository
from app.modules.admin_notifications.routes import router as admin_notifications_router
from app.modules.admin.investigation_case_file_repository import (
    InMemoryAdminInvestigationCaseFileRepository,
    PostgresAdminInvestigationCaseFileRepository,
)
from app.modules.admin.investigation_candidates_repository import (
    InMemoryAdminInvestigationCandidatesRepository,
    PostgresAdminInvestigationCandidatesRepository,
)
from app.modules.admin.repository import InMemoryAdminRepository, PostgresAdminRepository
from app.modules.admin.routes import router as admin_router
from app.modules.ads.repository import InMemoryAdRepository, PostgresAdRepository
from app.modules.ads.routes import router as ads_router
from app.modules.business_intake.repository import InMemoryBusinessIntakeRepository, PostgresBusinessIntakeRepository
from app.modules.business_capacity import InMemoryBusinessCapacityRepository, PostgresBusinessCapacityRepository
from app.modules.business_intake.routes import router as business_intake_router
from app.modules.businesses.repository import InMemoryBusinessRepository, PostgresBusinessRepository
from app.modules.businesses.routes import router as businesses_router
from app.modules.chat.repository import InMemoryChatRepository, PostgresChatRepository
from app.modules.chat.routes import router as chat_router
from app.modules.credits.repository import InMemoryCreditRepository, PostgresCreditRepository
from app.modules.credits.routes import router as credits_router
from app.modules.credits.onchain import JsonRpcBaseUsdcVerifier
from app.modules.credits.watcher import BaseUsdcCreditPurchaseWatcher
from app.modules.disputes.repository import InMemoryDisputeRepository, PostgresDisputeRepository
from app.modules.disputes.routes import router as disputes_router
from app.modules.jobs.lock import InMemoryJobLockManager, RedisJobLockManager
from app.modules.jobs.repository import InMemoryJobRepository, PostgresJobRepository
from app.modules.jobs.routes import router as jobs_router
from app.modules.jobs.worker import ExpireAndEscalateOrdersWorker
from app.modules.notifications.telegram_sender import NotificationSenderWorker
from app.modules.notifications.attention_read_repository import (
    InMemorySurfaceAttentionReadRepository,
    PostgresSurfaceAttentionReadRepository,
)
from app.modules.notifications.attention_routes import router as notification_attention_router
from app.modules.observability.repository import InMemoryFrontendObservabilityRepository, PostgresFrontendObservabilityRepository
from app.modules.observability.routes import router as observability_router
from app.modules.operations import InMemoryEmergencyModeRepository, PostgresEmergencyModeRepository
from app.modules.orders.repository import InMemoryOrderRepository, PostgresOrderRepository
from app.modules.orders.ratings_repository import InMemoryOrderRatingRepository, PostgresOrderRatingRepository
from app.modules.orders.routes import router as orders_router
from app.modules.support.repository import InMemorySupportRepository, PostgresSupportRepository
from app.modules.support.routes import router as support_router
from app.modules.staff.repository import InMemoryStaffRepository, PostgresStaffRepository
from app.modules.staff.routes import router as staff_router
from app.modules.users.repository import InMemoryUserRepository, PostgresUserRepository
from app.routes.auth import router as auth_router
from app.routes.admin_telegram_bot import router as admin_telegram_bot_router
from app.routes.health import router as health_router
from app.routes.surface import router as surface_router
from app.routes.telegram_bot import router as telegram_bot_router
from app.routes.users import router as users_router
from app.shared.audit.audit_service import InMemoryAuditWriter, PostgresAuditWriter
from app.shared.cache import InMemoryTTLCache, RedisTTLCache, VersionedLayeredTTLCache
from app.shared.db.connection import pool_snapshot, warm_pool
from app.shared.idempotency.store import InMemoryIdempotencyStore, RedisIdempotencyStore
from app.shared.observability import ObservabilityMiddleware, get_correlation_id, get_operation_id, get_request_id
from app.shared.rate_limit.in_memory import InMemoryRateLimiter
from app.shared.rate_limit.redis import RedisRateLimiter
from app.shared.security.headers import RuntimeTimingMiddleware, SecurityHeadersMiddleware
from app.core.config import Settings
from app.shared.storage.private import (
    InMemoryPrivateStorage,
    LocalFilePrivateStorage,
    SupabasePrivateStorage,
    UnavailablePrivateStorage,
)


def build_private_storage(settings: Settings):  # type: ignore[no-untyped-def]
    if settings.private_storage_mode == "local_file":
        return LocalFilePrivateStorage(settings.private_storage_root)
    if settings.private_storage_mode == "supabase":
        if not settings.supabase_url or not settings.supabase_service_role_key:
            return UnavailablePrivateStorage()
        return SupabasePrivateStorage(
            supabase_url=settings.supabase_url,
            service_role_key=settings.supabase_service_role_key,
            business_verification_bucket=settings.supabase_storage_bucket_business_verification,
            payment_evidence_bucket=settings.supabase_storage_bucket_payment_evidence,
            credit_purchase_proofs_bucket=settings.supabase_storage_bucket_credit_purchase_proofs,
            message_attachments_bucket=settings.supabase_storage_bucket_message_attachments,
            business_intake_bucket=settings.supabase_storage_bucket_business_intake,
        )
    return UnavailablePrivateStorage()


def _build_cost_rate_limiter(redis_url: str | None):  # type: ignore[no-untyped-def]
    if redis_url is None:
        return InMemoryRateLimiter()
    return RedisRateLimiter(redis_url, failure_mode="deny")


def create_app() -> FastAPI:
    settings = load_settings()
    configure_logging(settings.app_env)
    logger = get_logger(__name__)
    logger.info("api_boot", extra={"event": "system_bootstrapped", "app_version": settings.app_version})

    app = _new_fastapi_app(settings, logger=logger)
    app.state.settings = settings
    if settings.app_env == "test":
        _configure_test_state(app)
    else:
        _configure_runtime_state(app, settings=settings, logger=logger)
    _configure_workers(app)
    _configure_middlewares(app, settings=settings)
    _include_routes(app)
    _register_error_handlers(app, logger=logger)
    return app


def _new_fastapi_app(settings: Settings, *, logger) -> FastAPI:  # type: ignore[no-untyped-def]
    return FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
        lifespan=_lifespan(settings=settings, logger=logger),
    )


def _lifespan(*, settings: Settings, logger):  # type: ignore[no-untyped-def]
    @asynccontextmanager
    async def app_lifespan(_app: FastAPI) -> AsyncIterator[None]:
        limiter = anyio.to_thread.current_default_thread_limiter()
        previous_limit = limiter.total_tokens
        limiter.total_tokens = settings.api_thread_limit
        logger.info(
            "api_thread_limit_configured",
            extra={"previous_limit": previous_limit, "api_thread_limit": settings.api_thread_limit},
        )
        async with anyio.create_task_group() as task_group:
            if settings.order_notification_sender_enabled:
                task_group.start_soon(_order_notification_sender_loop, _app, settings, logger)
            if settings.onchain_credit_watcher_enabled:
                task_group.start_soon(_base_usdc_credit_watcher_loop, _app, settings, logger)
            try:
                yield
            finally:
                task_group.cancel_scope.cancel()

    return app_lifespan


async def _order_notification_sender_loop(app: FastAPI, settings: Settings, logger) -> None:  # type: ignore[no-untyped-def]
    await anyio.sleep(1)
    while True:
        try:
            result = await anyio.to_thread.run_sync(
                lambda: app.state.notification_sender_worker.run(
                    batch_size=settings.order_notification_sender_batch_size,
                    request_id="scheduler_order_notification_sender",
                )
            )
            counters = result.get("counters", {})
            if counters.get("processed"):
                logger.info(
                    "order_notification_sender_finished",
                    extra={
                        "event": "order_notification_sender_finished",
                        "processed": counters.get("processed", 0),
                        "sent": counters.get("sent", 0),
                        "retryable_failed": counters.get("retryable_failed", 0),
                        "failed_permanent": counters.get("failed_permanent", 0),
                    },
                )
        except Exception as exc:
            logger.warning(
                "order_notification_sender_failed",
                extra={"event": "order_notification_sender_failed", "error_code": getattr(exc, "code", "INTERNAL_ERROR")},
            )
        await anyio.sleep(settings.order_notification_sender_interval_seconds)


async def _base_usdc_credit_watcher_loop(app: FastAPI, settings: Settings, logger) -> None:  # type: ignore[no-untyped-def]
    await anyio.sleep(2)
    while True:
        try:
            result = await anyio.to_thread.run_sync(
                lambda: app.state.verify_base_usdc_credit_purchases_worker.run_once(
                    request_id="scheduler_base_usdc_credit_watcher"
                )
            )
            if result.get("eligible") or result.get("credited") or result.get("errors"):
                logger.info(
                    "base_usdc_credit_watcher_finished",
                    extra={
                        "event": "base_usdc_credit_watcher_finished",
                        "scanned": result.get("scanned", 0),
                        "eligible": result.get("eligible", 0),
                        "verified_attempts": result.get("verified_attempts", 0),
                        "credited": result.get("credited", 0),
                        "under_review": result.get("under_review", 0),
                        "pending": result.get("pending", 0),
                        "errors_count": len(result.get("errors", [])),
                        "rpc_calls": result.get("rpc_calls", 0),
                    },
                )
        except Exception as exc:
            logger.warning(
                "base_usdc_credit_watcher_failed",
                extra={"event": "base_usdc_credit_watcher_failed", "error_code": getattr(exc, "code", "INTERNAL_ERROR")},
            )
        await anyio.sleep(settings.onchain_credit_watcher_interval_seconds)


def _configure_test_state(app: FastAPI) -> None:
    app.state.audit_writer = InMemoryAuditWriter()
    app.state.user_repository = InMemoryUserRepository()
    app.state.business_repository = InMemoryBusinessRepository()
    ad_capacity_lock = RLock()
    app.state.ad_repository = InMemoryAdRepository(lock=ad_capacity_lock)
    app.state.capacity_repository = InMemoryBusinessCapacityRepository(
        lock=ad_capacity_lock,
        ad_repository=app.state.ad_repository,
    )
    app.state.ad_repository.bind_capacity_repository(app.state.capacity_repository)
    app.state.ad_repository.bind_business_repository(app.state.business_repository)
    app.state.business_intake_repository = InMemoryBusinessIntakeRepository()
    app.state.dispute_repository = InMemoryDisputeRepository()
    app.state.job_repository = InMemoryJobRepository()
    app.state.order_repository = InMemoryOrderRepository(
        capacity_repository=app.state.capacity_repository,
        audit_writer=app.state.audit_writer,
        dispute_repository=app.state.dispute_repository,
        job_repository=app.state.job_repository,
        business_repository=app.state.business_repository,
    )
    app.state.chat_repository = InMemoryChatRepository()
    app.state.support_repository = InMemorySupportRepository()
    app.state.ad_repository.bind_publication_hold_repository(app.state.support_repository)
    app.state.business_repository.bind_publication_hold_repository(app.state.support_repository)
    app.state.order_repository.bind_publication_hold_repository(app.state.support_repository)
    app.state.surface_attention_read_repository = InMemorySurfaceAttentionReadRepository()
    app.state.credit_repository = InMemoryCreditRepository(app.state.ad_repository, app.state.business_repository)
    app.state.rating_repository = InMemoryOrderRatingRepository(
        order_repository=app.state.order_repository,
        business_repository=app.state.business_repository,
        dispute_repository=app.state.dispute_repository,
    )
    app.state.admin_notification_repository = InMemoryAdminNotificationRepository()
    app.state.admin_notification_service = AdminNotificationService(
        repository=app.state.admin_notification_repository,
        job_repository=app.state.job_repository,
        user_repository=app.state.user_repository,
        admin_telegram_alerts_enabled=admin_telegram_alerts_configured(app.state.settings),
        admin_app_url=app.state.settings.telegram_web_app_url,
    )
    app.state.staff_repository = InMemoryStaffRepository(users=app.state.user_repository, audit_writer=app.state.audit_writer)
    app.state.admin_repository = InMemoryAdminRepository(
        users=app.state.user_repository,
        businesses=app.state.business_repository,
        orders=app.state.order_repository,
        disputes=app.state.dispute_repository,
        credits=app.state.credit_repository,
        audit_writer=app.state.audit_writer,
        business_intake=app.state.business_intake_repository,
        support=app.state.support_repository,
    )
    app.state.admin_case_file_repository = InMemoryAdminInvestigationCaseFileRepository(
        users=app.state.user_repository,
        businesses=app.state.business_repository,
        business_intake=app.state.business_intake_repository,
        orders=app.state.order_repository,
        support=app.state.support_repository,
        chat=app.state.chat_repository,
    )
    app.state.admin_investigation_candidates_repository = InMemoryAdminInvestigationCandidatesRepository(
        users=app.state.user_repository,
        businesses=app.state.business_repository,
        orders=app.state.order_repository,
        support=app.state.support_repository,
    )
    app.state.rate_limiter = InMemoryRateLimiter()
    app.state.cost_rate_limiter = _build_cost_rate_limiter(None)
    app.state.marketplace_rate_limiter = app.state.cost_rate_limiter
    app.state.idempotency_store = InMemoryIdempotencyStore()
    app.state.marketplace_cache = InMemoryTTLCache()
    app.state.admin_read_model_cache = InMemoryTTLCache()
    app.state.auth_user_cache = None
    app.state.private_storage = InMemoryPrivateStorage()
    app.state.job_lock_manager = InMemoryJobLockManager()
    app.state.onchain_credit_verifier = JsonRpcBaseUsdcVerifier(rpc_url=None, timeout_seconds=1)
    app.state.emergency_mode_repository = InMemoryEmergencyModeRepository()
    app.state.observability_repository = InMemoryFrontendObservabilityRepository()


def _configure_runtime_state(app: FastAPI, *, settings: Settings, logger) -> None:  # type: ignore[no-untyped-def]
    app.state.audit_writer = PostgresAuditWriter(settings.database_url)
    app.state.user_repository = PostgresUserRepository(settings.database_url)
    app.state.business_repository = PostgresBusinessRepository(settings.database_url)
    app.state.capacity_repository = PostgresBusinessCapacityRepository(settings.database_url)
    app.state.business_intake_repository = PostgresBusinessIntakeRepository(settings.database_url)
    app.state.ad_repository = PostgresAdRepository(settings.database_url)
    app.state.job_repository = PostgresJobRepository(settings.database_url)
    app.state.order_repository = PostgresOrderRepository(
        settings.database_url,
        capacity_repository=app.state.capacity_repository,
        ad_repository=app.state.ad_repository,
        job_repository=app.state.job_repository,
    )
    app.state.chat_repository = PostgresChatRepository(settings.database_url)
    app.state.support_repository = PostgresSupportRepository(settings.database_url)
    app.state.surface_attention_read_repository = PostgresSurfaceAttentionReadRepository(settings.database_url)
    app.state.credit_repository = PostgresCreditRepository(settings.database_url)
    app.state.dispute_repository = PostgresDisputeRepository(settings.database_url)
    app.state.rating_repository = PostgresOrderRatingRepository(settings.database_url)
    app.state.admin_notification_repository = PostgresAdminNotificationRepository(settings.database_url)
    app.state.admin_notification_service = AdminNotificationService(
        repository=app.state.admin_notification_repository,
        job_repository=app.state.job_repository,
        user_repository=app.state.user_repository,
        admin_telegram_alerts_enabled=admin_telegram_alerts_configured(settings),
        admin_app_url=settings.telegram_web_app_url,
    )
    app.state.staff_repository = PostgresStaffRepository(settings.database_url)
    app.state.admin_repository = PostgresAdminRepository(settings.database_url)
    app.state.admin_case_file_repository = PostgresAdminInvestigationCaseFileRepository(settings.database_url)
    app.state.admin_investigation_candidates_repository = PostgresAdminInvestigationCandidatesRepository(
        settings.database_url
    )
    try:
        warm_pool(settings.database_url, size=int(os.environ.get("NODO_DB_POOL_WARM_SIZE", "8")))
        logger.info(
            "db_pool_configured",
            extra={"pool": pool_snapshot(settings.database_url), "api_thread_limit": settings.api_thread_limit},
        )
    except Exception as exc:
        logger.warning("db_pool_warm_failed", extra={"error": str(exc)})
    app.state.rate_limiter = RedisRateLimiter(settings.redis_url)
    app.state.cost_rate_limiter = _build_cost_rate_limiter(settings.redis_url)
    app.state.marketplace_rate_limiter = app.state.cost_rate_limiter
    app.state.idempotency_store = RedisIdempotencyStore(settings.redis_url)
    app.state.marketplace_cache = VersionedLayeredTTLCache(
        local_cache=InMemoryTTLCache(),
        shared_cache=RedisTTLCache(settings.redis_url),
        namespace="marketplace:ads",
        version_cache_ttl_seconds=settings.marketplace_cache_version_ttl_seconds,
        shared_hit_local_ttl_seconds=settings.marketplace_cache_shared_hit_local_ttl_seconds,
    )
    app.state.admin_read_model_cache = InMemoryTTLCache()
    app.state.auth_user_cache = InMemoryTTLCache()
    app.state.private_storage = build_private_storage(settings)
    app.state.job_lock_manager = RedisJobLockManager(settings.redis_url)
    app.state.onchain_credit_verifier = JsonRpcBaseUsdcVerifier(rpc_url=settings.base_rpc_url, timeout_seconds=settings.onchain_credit_watcher_timeout_seconds)
    app.state.emergency_mode_repository = PostgresEmergencyModeRepository(settings.database_url)
    app.state.observability_repository = PostgresFrontendObservabilityRepository(settings.database_url)


def _configure_workers(app: FastAPI) -> None:
    app.state.expire_and_escalate_orders_worker = ExpireAndEscalateOrdersWorker(
        job_repository=app.state.job_repository,
        lock_manager=app.state.job_lock_manager,
        order_repository=app.state.order_repository,
        ad_repository=app.state.ad_repository,
        business_repository=app.state.business_repository,
        dispute_repository=app.state.dispute_repository,
        audit_writer=app.state.audit_writer,
    )
    app.state.verify_base_usdc_credit_purchases_worker = BaseUsdcCreditPurchaseWatcher(
        settings=app.state.settings,
        credit_repository=app.state.credit_repository,
        audit_writer=app.state.audit_writer,
        onchain_verifier=app.state.onchain_credit_verifier,
        admin_notifications=app.state.admin_notification_service,
    )
    app.state.notification_sender_worker = NotificationSenderWorker(
        settings=app.state.settings,
        job_repository=app.state.job_repository,
        user_repository=app.state.user_repository,
        admin_notifications=app.state.admin_notification_service,
    )


def _configure_middlewares(app: FastAPI, *, settings: Settings) -> None:
    app.add_middleware(ObservabilityMiddleware)
    app.add_middleware(RuntimeTimingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    cloudflare_preview_origin_regex = r"^https://[a-z0-9-]+\.nodo-staging\.pages\.dev$"
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=cloudflare_preview_origin_regex,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-Id",
            "X-Correlation-Id",
            "X-NODO-Operation-Id",
            "X-NODO-Surface",
            "X-NODO-Profile",
            "X-NODO-Bot-Webhook-Secret",
            "Idempotency-Key",
            "Stripe-Signature",
        ],
        expose_headers=[
            "X-Request-Id",
            "X-Correlation-Id",
            "X-NODO-Operation-Id",
            "X-NODO-Surface",
            "X-NODO-Process-Time-Ms",
            "Server-Timing",
        ],
    )


def _include_routes(app: FastAPI) -> None:
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(surface_router, prefix="/api/v1")
    app.include_router(businesses_router, prefix="/api/v1")
    app.include_router(business_intake_router, prefix="/api/v1")
    app.include_router(ads_router, prefix="/api/v1")
    app.include_router(orders_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(support_router, prefix="/api/v1")
    app.include_router(staff_router, prefix="/api/v1")
    app.include_router(credits_router, prefix="/api/v1")
    app.include_router(disputes_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(admin_notifications_router, prefix="/api/v1")
    app.include_router(notification_attention_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")
    app.include_router(observability_router, prefix="/api/v1")
    app.include_router(admin_telegram_bot_router, prefix="/api/v1")
    app.include_router(telegram_bot_router, prefix="/api/v1")
    app.include_router(health_router)


def _register_error_handlers(app: FastAPI, *, logger) -> None:  # type: ignore[no-untyped-def]
    def _observability_error_headers(request) -> dict[str, str]:  # type: ignore[no-untyped-def]
        headers = {}
        correlation_id = get_correlation_id(request)
        operation_id = get_operation_id(request)
        surface = getattr(request.state, "surface", "")
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id
        if operation_id:
            headers["X-NODO-Operation-Id"] = operation_id
        if surface:
            headers["X-NODO-Surface"] = surface
        return headers

    @app.exception_handler(ApiError)
    async def api_error_handler(request, exc: ApiError):  # type: ignore[no-untyped-def]
        request_id = get_request_id(request)
        return api_error_response(exc.code, exc.message, request_id, status_code=exc.status_code, headers=_observability_error_headers(request))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc: RequestValidationError):  # type: ignore[no-untyped-def]
        request_id = get_request_id(request)
        return api_error_response("VALIDATION_ERROR", "Revisa los datos enviados.", request_id, status_code=422, headers=_observability_error_headers(request))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request, exc):  # type: ignore[no-untyped-def]
        request_id = get_request_id(request)
        traceback_frames = [
            {"file": frame.filename.rsplit("\\", 1)[-1].rsplit("/", 1)[-1], "line": frame.lineno, "function": frame.name}
            for frame in traceback.extract_tb(exc.__traceback__)[-8:]
        ]
        logger.error(
            "api_unhandled_error",
            extra={
                "request_id": request_id,
                "correlation_id": get_correlation_id(request),
                "operation_id": get_operation_id(request),
                "surface": getattr(request.state, "surface", "unknown"),
                "error_code": "INTERNAL_ERROR",
                "exception_class": exc.__class__.__name__,
                "traceback_frames": traceback_frames,
            },
        )
        return api_error_response("INTERNAL_ERROR", "Ocurrio un error temporal.", request_id, status_code=500, headers=_observability_error_headers(request))


app = create_app()
