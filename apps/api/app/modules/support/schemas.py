from __future__ import annotations

from pydantic import Field

from app.shared.validation import ResourceId, StrictRequestModel


class SupportTicketCreateRequest(StrictRequestModel):
    scope: str = Field(min_length=1, max_length=40)
    category: str = Field(min_length=1, max_length=80)
    subject: str = Field(min_length=1, max_length=140)
    message: str = Field(min_length=1, max_length=2000)
    order_id: ResourceId | None = None
    business_id: ResourceId | None = None
    ad_id: ResourceId | None = None
    credit_purchase_id: ResourceId | None = None
    attachment_ids: list[ResourceId] = Field(default_factory=list, max_length=5)


class OperationReportCreateRequest(StrictRequestModel):
    category: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=3, max_length=1000)


class SupportMessageCreateRequest(StrictRequestModel):
    body: str = Field(min_length=1, max_length=2000)
    attachment_ids: list[ResourceId] = Field(default_factory=list, max_length=5)


class AdminSupportMessageCreateRequest(StrictRequestModel):
    body: str = Field(min_length=1, max_length=2000)
    visibility: str = Field(default="participants", min_length=1, max_length=40)
    attachment_ids: list[ResourceId] = Field(default_factory=list, max_length=5)


class SupportAssignRequest(StrictRequestModel):
    assigned_support_user_id: ResourceId
    reason: str = Field(min_length=1, max_length=500)


class SupportEscalateRequest(StrictRequestModel):
    reason: str = Field(min_length=1, max_length=500)
    existing_dispute_id: ResourceId | None = None


class SupportReasonRequest(StrictRequestModel):
    reason: str = Field(min_length=1, max_length=500)
