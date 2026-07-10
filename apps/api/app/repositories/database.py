from __future__ import annotations

from app.core.network import ConnectivityResult
from app.shared.db.connection import connect


class DatabaseRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def check_connectivity(self) -> ConnectivityResult:
        try:
            with connect(self._database_url, connect_timeout=1):
                return ConnectivityResult(True)
        except Exception:
            return ConnectivityResult(False, "UPSTREAM_UNAVAILABLE", "Connection failed.")
