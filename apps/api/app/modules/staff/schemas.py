from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.shared.validation import ResourceId, StrictRequestModel


class StaffPermissionInput(StrictRequestModel):
    permission: str = Field(min_length=1, max_length=80)
    scope: str = Field(min_length=1, max_length=80)
    scope_value: str | None = Field(default=None, max_length=160)


class StaffInviteCreateRequest(StrictRequestModel):
    target_user_id: ResourceId | None = None
    target_telegram_id: str | None = Field(default=None, min_length=1, max_length=32)
    target_username: str | None = Field(default=None, min_length=1, max_length=80)
    staff_role: str = Field(min_length=1, max_length=40)
    permissions: list[StaffPermissionInput] = Field(default_factory=list, max_length=20)
    expires_at: datetime
    reason: str = Field(min_length=1, max_length=500)


class StaffReasonRequest(StrictRequestModel):
    reason: str = Field(min_length=1, max_length=500)


class StaffPermissionsUpdateRequest(StrictRequestModel):
    permissions: list[StaffPermissionInput] = Field(default_factory=list, max_length=20)
    reason: str = Field(min_length=1, max_length=500)
