from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from collections.abc import Mapping
from typing import Any

from app.core.config import Settings
from app.core.errors import ApiError
from app.core.logging import get_logger
from app.modules.observability.schemas import ObservabilityEvent, ObservabilityEventsRequest
from app.modules.users.models import UserRecord
from app.shared.logging_redaction import redact_mapping, redact_text


logger = get_logger("nodo.frontend_observability")

SENSITIVE_METADATA_FRAGMENTS = {
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "pin",
    "otp",
    "wallet",
    "zelle",
    "email",
    "phone",
    "account",
    "account_value",
    "storage",
    "storage_path",
    "signed_url",
    "private",
    "seed",
    "mnemonic",
    "tx",
    "tx_hash",
    "hash",
    "url",
}

LOG_LEVEL_BY_SEVERITY = {
    "trace": logging.DEBUG,
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "error": logging.ERROR,
}


def _stable_actor_hash(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16]


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(fragment in normalized for fragment in SENSITIVE_METADATA_FRAGMENTS)


def _safe_metadata_value(key: str, value: Any) -> Any:
    if _is_sensitive_key(key):
        return "[REDACTED]"
    if isinstance(value, str):
        return redact_text(value)[:160]
    if isinstance(value, bool) or isinstance(value, int) or isinstance(value, float) or value is None:
        return value
    if isinstance(value, Mapping):
        return {str(item_key)[:80]: _safe_metadata_value(str(item_key), item_value) for item_key, item_value in list(value.items())[:20]}
    if isinstance(value, list):
        return [_safe_metadata_value(key, item) for item in value[:20]]
    return str(value)[:160]


def sanitize_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    sanitized = {str(key)[:80]: _safe_metadata_value(str(key), value) for key, value in list(metadata.items())[:40]}
    return redact_mapping(sanitized)


def _serialized_event_size(event: ObservabilityEvent) -> int:
    return len(json.dumps(event.model_dump(mode="json"), separators=(",", ":"), sort_keys=True).encode("utf-8"))


class ObservabilityIngestService:
    def __init__(self, *, settings: Settings, repository=None) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository

    def ingest(
        self,
        *,
        payload: ObservabilityEventsRequest,
        user: UserRecord,
        surface: str,
        request_id: str,
    ) -> dict[str, int]:
        if not self._settings.observability_ingest_enabled:
            raise ApiError("OBSERVABILITY_DISABLED", status_code=403)
        if surface == "unknown" or not surface:
            raise ApiError("OBSERVABILITY_ACCESS_DENIED", status_code=403)
        if len(payload.events) > self._settings.observability_max_events_per_batch:
            raise ApiError("OBSERVABILITY_BATCH_TOO_LARGE", status_code=413)

        accepted = 0
        for event in payload.events:
            if _serialized_event_size(event) > self._settings.observability_max_event_bytes:
                raise ApiError("OBSERVABILITY_EVENT_TOO_LARGE", status_code=413)
            metadata = sanitize_metadata(event.metadata)
            resource_refs = redact_mapping(event.resource_refs.model_dump(exclude_none=True))
            self._log_event(payload=payload, event=event, user=user, surface=surface, request_id=request_id, metadata=metadata, resource_refs=resource_refs)
            self._record_event(payload=payload, event=event, user=user, surface=surface, request_id=request_id, metadata=metadata, resource_refs=resource_refs)
            accepted += 1
        return {"accepted": accepted}

    def _log_event(
        self,
        *,
        payload: ObservabilityEventsRequest,
        event: ObservabilityEvent,
        user: UserRecord,
        surface: str,
        request_id: str,
        metadata: dict[str, Any],
        resource_refs: dict[str, Any],
    ) -> None:
        level = LOG_LEVEL_BY_SEVERITY.get(event.severity, logging.INFO)
        logger.log(
            level,
            "frontend_observability_event",
            extra={
                "request_id": event.request_id or request_id,
                "correlation_id": event.correlation_id,
                "operation_id": event.operation_id,
                "event_id": event.event_id,
                "event_type": event.event_type,
                "severity": event.severity,
                "surface": surface,
                "session_id": payload.session_id,
                "app_version": payload.app_version,
                "build_id": payload.build_id,
                "actor_user_hash": _stable_actor_hash(user.id),
                "actor_role": user.role,
                "screen": event.screen,
                "previous_screen": event.previous_screen,
                "action": event.action,
                "method": event.method,
                "route_template": event.route_template,
                "status_code": event.status_code,
                "duration_ms": event.duration_ms,
                "error_code": event.error_code,
                "resource_refs": resource_refs,
                "metadata": metadata,
            },
        )

    def _record_event(
        self,
        *,
        payload: ObservabilityEventsRequest,
        event: ObservabilityEvent,
        user: UserRecord,
        surface: str,
        request_id: str,
        metadata: dict[str, Any],
        resource_refs: dict[str, Any],
    ) -> None:
        if self._repository is None:
            return
        self._repository.record_event(
            event_id=event.event_id,
            event_type=event.event_type,
            severity=event.severity,
            surface=surface,
            session_id_hash=_stable_actor_hash(payload.session_id),
            actor_user_hash=_stable_actor_hash(user.id),
            actor_role=user.role,
            request_id=event.request_id or request_id,
            correlation_id=event.correlation_id,
            operation_id=event.operation_id,
            screen=event.screen,
            previous_screen=event.previous_screen,
            action=event.action,
            method=event.method,
            route_template=event.route_template,
            status_code=event.status_code,
            duration_ms=event.duration_ms,
            error_code=event.error_code,
            resource_refs_json=json.dumps(resource_refs, separators=(",", ":"), sort_keys=True),
            metadata_json=json.dumps(metadata, separators=(",", ":"), sort_keys=True),
            occurred_at=event.timestamp,
            created_at=datetime.now(timezone.utc),
        )
