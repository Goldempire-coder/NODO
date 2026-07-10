from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class DisputeCreateRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=2000)
    evidence_file_ids: list[str] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def require_reason(self) -> "DisputeCreateRequest":
        if not self.reason.strip():
            raise ValueError("reason required")
        return self


class DisputeResolveRequest(BaseModel):
    resolution_type: str = Field(min_length=1, max_length=40)
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_resolution_reason(self) -> "DisputeResolveRequest":
        if not self.reason.strip():
            raise ValueError("reason required")
        return self
