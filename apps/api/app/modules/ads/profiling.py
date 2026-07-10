from __future__ import annotations

import os
from typing import Any

from app.shared import profiling as shared_profiling


def profile_enabled() -> bool:
    return os.environ.get("NODO_INTERNAL_PROFILING") == "1"


def profile_mark(profile: list[dict[str, Any]] | None, stage: str, started: float) -> None:
    shared_profiling.profile_mark(profile, stage, started)


def profile_attach(payload: dict[str, Any], profile: list[dict[str, Any]] | None, started: float) -> dict[str, Any]:
    return shared_profiling.profile_attach(payload, profile, started)
