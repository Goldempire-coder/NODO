from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StoredPrivateFile:
    storage_path: str
    size_bytes: int
    checksum_sha256: str
