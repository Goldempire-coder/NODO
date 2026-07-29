from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.shared.validation import ResourceId, StrictRequestModel


class AttentionAcknowledgeRequest(StrictRequestModel):
    kind: Literal["order", "support"]
    resource_id: ResourceId
    signature: str = Field(min_length=16, max_length=96)
