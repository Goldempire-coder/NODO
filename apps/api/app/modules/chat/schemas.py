from __future__ import annotations

from pydantic import BaseModel, Field


class MessageCreateRequest(BaseModel):
    body: str | None = Field(default=None, max_length=2000)
    attachment_ids: list[str] = Field(default_factory=list, max_length=5)


class MessageAttachmentUploadResult(BaseModel):
    id: str
    file_asset_id: str
    file_type: str
    mime_type: str
    size_bytes: int
    created_at: str
