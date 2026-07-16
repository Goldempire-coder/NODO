from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import ApiError


RESOURCE_ID_MAX_LENGTH = 80
ResourceId = Annotated[str, Field(min_length=1, max_length=RESOURCE_ID_MAX_LENGTH)]


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def resource_id_field(**kwargs: Any):  # type: ignore[no-untyped-def]
    return Field(min_length=1, max_length=RESOURCE_ID_MAX_LENGTH, **kwargs)


async def read_limited_upload(file: Any, *, max_bytes: int, empty_or_too_large_error: str) -> bytes:
    content = await file.read(max_bytes + 1)
    if not content or len(content) > max_bytes:
        raise ApiError(empty_or_too_large_error, status_code=400)
    return content
