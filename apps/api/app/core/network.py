from __future__ import annotations

import socket
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ConnectivityResult:
    ok: bool
    code: str | None = None
    message: str | None = None


def socket_check(url: str, default_port: int, timeout_seconds: float = 0.35) -> ConnectivityResult:
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or default_port
    if not host:
        return ConnectivityResult(False, "VALIDATION_ERROR", "Host is missing.")
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return ConnectivityResult(True)
    except OSError:
        return ConnectivityResult(False, "UPSTREAM_UNAVAILABLE", "Connection failed.")
