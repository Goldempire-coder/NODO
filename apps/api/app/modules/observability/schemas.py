from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.shared.validation import StrictRequestModel


class ObservabilityResourceRefs(StrictRequestModel):
    business_id: str | None = Field(default=None, max_length=80)
    ad_id: str | None = Field(default=None, max_length=80)
    order_id: str | None = Field(default=None, max_length=80)
    credit_purchase_id: str | None = Field(default=None, max_length=80)
    support_ticket_id: str | None = Field(default=None, max_length=80)


class ObservabilityEvent(StrictRequestModel):
    event_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=80)
    severity: Literal["trace", "debug", "info", "warn", "error"] = "info"
    timestamp: datetime
    request_id: str | None = Field(default=None, max_length=128)
    correlation_id: str | None = Field(default=None, max_length=128)
    operation_id: str | None = Field(default=None, max_length=128)
    screen: str | None = Field(default=None, max_length=80)
    previous_screen: str | None = Field(default=None, max_length=80)
    action: str | None = Field(default=None, max_length=120)
    method: str | None = Field(default=None, max_length=10)
    route_template: str | None = Field(default=None, max_length=200)
    status_code: int | None = Field(default=None, ge=0, le=599)
    duration_ms: float | None = Field(default=None, ge=0, le=120000)
    error_code: str | None = Field(default=None, max_length=120)
    resource_refs: ObservabilityResourceRefs = Field(default_factory=ObservabilityResourceRefs)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ObservabilityEventsRequest(StrictRequestModel):
    session_id: str = Field(min_length=1, max_length=128)
    app_version: str | None = Field(default=None, max_length=80)
    build_id: str | None = Field(default=None, max_length=120)
    events: list[ObservabilityEvent] = Field(min_length=1, max_length=20)
