from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.modules.jobs.models import NotificationJobRecord, mask_metadata
from app.modules.notifications.notification_types import TELEGRAM_NOTIFICATION_TYPES, USER_STATUS_NOTIFICATION_TYPES

logger = get_logger(__name__)

RETRYABLE_ERROR_CODES = {"TELEGRAM_BOT_SEND_FAILED", "TELEGRAM_RATE_LIMITED", "TELEGRAM_BOT_NOT_CONFIGURED"}
PERMANENT_ERROR_CODES = {"TELEGRAM_CHAT_UNAVAILABLE", "RECIPIENT_NOT_FOUND", "RECIPIENT_NOT_ACTIVE", "RECIPIENT_NOT_AUTHORIZED", "ROLE_RECIPIENT_NOT_SENDABLE"}
ADMIN_ALERT_TARGET_SURFACE = "admin_alerts"


@dataclass
class TelegramNotificationError(RuntimeError):
    code: str
    retryable: bool

    def __str__(self) -> str:
        return self.code


class TelegramNotificationAdapter:
    def send_message(self, *, bot_token: str, chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        try:
            with httpx.Client(timeout=8.0) as client:
                response = client.post(url, json=payload)
                data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        except httpx.HTTPError as exc:
            raise TelegramNotificationError("TELEGRAM_BOT_SEND_FAILED", retryable=True) from exc
        except ValueError as exc:
            raise TelegramNotificationError("TELEGRAM_BOT_SEND_FAILED", retryable=True) from exc

        if response.status_code == 429:
            raise TelegramNotificationError("TELEGRAM_RATE_LIMITED", retryable=True)
        if response.status_code in {400, 403}:
            raise TelegramNotificationError("TELEGRAM_CHAT_UNAVAILABLE", retryable=False)
        if response.status_code >= 500:
            raise TelegramNotificationError("TELEGRAM_BOT_SEND_FAILED", retryable=True)
        if response.status_code >= 400 or data.get("ok") is not True:
            raise TelegramNotificationError("TELEGRAM_BOT_SEND_FAILED", retryable=True)


class NotificationSenderWorker:
    def __init__(
        self,
        *,
        settings: Settings,
        job_repository,
        user_repository,
        adapter: TelegramNotificationAdapter | None = None,
        admin_notifications=None,
    ) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._jobs = job_repository
        self._users = user_repository
        self._adapter = adapter or TelegramNotificationAdapter()
        self._admin_notifications = admin_notifications

    def run(self, *, now: datetime | None = None, batch_size: int = 100, request_id: str = "notification_sender") -> dict[str, Any]:
        started = time.perf_counter()
        current_time = now or datetime.now(timezone.utc)
        notifications = self._jobs.list_due_telegram_notifications(
            now=current_time,
            limit=batch_size,
            notification_types=TELEGRAM_NOTIFICATION_TYPES,
        )
        counters = {"processed": 0, "sent": 0, "retryable_failed": 0, "failed_permanent": 0, "skipped": 0}
        for notification in notifications:
            counters["processed"] += 1
            result = self._process_one(notification, now=current_time, request_id=request_id)
            counters[result] += 1
        return {
            "status": "finished",
            "duration_ms": round((time.perf_counter() - started) * 1000, 4),
            "counters": counters,
        }

    def _process_one(self, notification: NotificationJobRecord, *, now: datetime, request_id: str) -> str:
        try:
            bot_token, chat_id, text, reply_markup = self._send_context(notification)
            self._adapter.send_message(bot_token=bot_token, chat_id=chat_id, text=text, reply_markup=reply_markup)
        except TelegramNotificationError as exc:
            if exc.retryable and notification.attempts + 1 < notification.max_attempts:
                self._mark_retryable_failed(notification, now=now, error_code=exc.code, request_id=request_id)
                return "retryable_failed"
            self._mark_failed_permanent(notification, now=now, error_code=exc.code, request_id=request_id)
            return "failed_permanent"
        except Exception as exc:
            error_code = getattr(exc, "code", "TELEGRAM_BOT_SEND_FAILED")
            if notification.attempts + 1 < notification.max_attempts:
                self._mark_retryable_failed(notification, now=now, error_code=error_code, request_id=request_id)
                return "retryable_failed"
            self._mark_failed_permanent(notification, now=now, error_code=error_code, request_id=request_id)
            return "failed_permanent"

        metadata = self._metadata_with_delivery_state(notification, "sent", request_id=request_id)
        self._jobs.update_notification(
            notification,
            status="sent",
            sent_at=now,
            attempts=notification.attempts + 1,
            last_error_code=None,
            metadata_json=metadata,
        )
        logger.info(
            "notification_job_sent",
            extra={
                "event": "notification_job_sent",
                "notification_job_id": notification.id,
                "notification_type": notification.notification_type,
                "order_id": notification.order_id,
                "business_id": notification.business_id,
                "attempts": notification.attempts + 1,
                "request_id": request_id,
            },
        )
        return "sent"

    def _send_context(self, notification: NotificationJobRecord) -> tuple[str, int, str, dict[str, Any] | None]:
        metadata = notification.metadata_json or {}
        if notification.recipient_user_id is None:
            raise TelegramNotificationError("ROLE_RECIPIENT_NOT_SENDABLE", retryable=False)
        user = self._users.get_user_by_id(notification.recipient_user_id)
        if user is None:
            raise TelegramNotificationError("RECIPIENT_NOT_FOUND", retryable=False)
        if user.status != "active" and notification.notification_type not in USER_STATUS_NOTIFICATION_TYPES:
            raise TelegramNotificationError("RECIPIENT_NOT_ACTIVE", retryable=False)
        target_surface = str(metadata.get("target_surface") or "")
        if target_surface == ADMIN_ALERT_TARGET_SURFACE and user.role not in {"admin", "super_admin"}:
            raise TelegramNotificationError("RECIPIENT_NOT_AUTHORIZED", retryable=False)
        if user.telegram_id is None:
            raise TelegramNotificationError("TELEGRAM_CHAT_UNAVAILABLE", retryable=False)

        bot_token = self._bot_token_for_surface(target_surface)
        if not bot_token:
            raise TelegramNotificationError("TELEGRAM_BOT_NOT_CONFIGURED", retryable=True)
        text = str(metadata.get("message_text") or "Tienes una actualizacion en NODO.")
        action_url = str(metadata.get("action_url") or "")
        reply_markup = None
        if action_url:
            action_text = str(metadata.get("action_text") or "Abrir NODO")
            button: dict[str, Any]
            if target_surface == ADMIN_ALERT_TARGET_SURFACE:
                button = {"text": action_text, "url": action_url}
            else:
                button = {"text": action_text, "web_app": {"url": action_url}}
            reply_markup = {"inline_keyboard": [[button]]}
        return bot_token, int(user.telegram_id), text, reply_markup

    def _bot_token_for_surface(self, target_surface: str) -> str | None:
        if target_surface == ADMIN_ALERT_TARGET_SURFACE:
            return self._settings.nodo_admin_telegram_bot_token
        if target_surface == "business_mini_app":
            return self._settings.business_intake_bot_token
        return self._settings.bot_token

    def _mark_retryable_failed(self, notification: NotificationJobRecord, *, now: datetime, error_code: str, request_id: str) -> None:
        next_time = now + timedelta(seconds=min(300, 30 * (notification.attempts + 1)))
        metadata = self._metadata_with_delivery_state(notification, "retryable_failed", request_id=request_id)
        self._jobs.update_notification(
            notification,
            status="pending",
            scheduled_for=next_time,
            attempts=notification.attempts + 1,
            last_error_code=error_code,
            metadata_json=metadata,
        )
        self._log_failure(notification, "notification_job_retryable_failed", error_code, request_id)

    def _mark_failed_permanent(self, notification: NotificationJobRecord, *, now: datetime, error_code: str, request_id: str) -> None:
        metadata = self._metadata_with_delivery_state(notification, "failed_permanent", request_id=request_id)
        self._jobs.update_notification(
            notification,
            status="failed",
            failed_at=now,
            attempts=notification.attempts + 1,
            last_error_code=error_code,
            metadata_json=metadata,
        )
        if self._admin_notifications is not None:
            self._admin_notifications.telegram_failed_permanent(notification=notification, error_code=error_code, request_id=request_id)
        self._log_failure(notification, "notification_job_failed_permanent", error_code, request_id)

    def _metadata_with_delivery_state(self, notification: NotificationJobRecord, delivery_state: str, *, request_id: str) -> dict:
        metadata = dict(notification.metadata_json or {})
        metadata["delivery_state"] = delivery_state
        metadata["last_sender_request_id"] = request_id
        return mask_metadata(metadata)

    def _log_failure(self, notification: NotificationJobRecord, event: str, error_code: str, request_id: str) -> None:
        logger.warning(
            event,
            extra={
                "event": event,
                "notification_job_id": notification.id,
                "notification_type": notification.notification_type,
                "order_id": notification.order_id,
                "business_id": notification.business_id,
                "attempts": notification.attempts + 1,
                "error_code": error_code,
                "request_id": request_id,
            },
        )
