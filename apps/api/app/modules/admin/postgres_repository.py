from __future__ import annotations

from app.modules.admin.postgres_audit import PostgresAdminAuditMixin
from app.modules.admin.postgres_businesses import PostgresAdminBusinessesMixin
from app.modules.admin.postgres_dashboard import PostgresAdminDashboardMixin
from app.modules.admin.postgres_investigation import PostgresAdminInvestigationMixin
from app.modules.admin.postgres_orders import PostgresAdminOrdersMixin
from app.modules.admin.postgres_users import PostgresAdminUsersMixin
from app.shared.db.connection import pooled_connect


class PostgresAdminRepository(
    PostgresAdminAuditMixin,
    PostgresAdminBusinessesMixin,
    PostgresAdminDashboardMixin,
    PostgresAdminInvestigationMixin,
    PostgresAdminOrdersMixin,
    PostgresAdminUsersMixin,
):
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)
