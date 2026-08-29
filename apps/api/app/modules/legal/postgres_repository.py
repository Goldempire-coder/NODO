from __future__ import annotations

from app.modules.legal.models import BusinessLegalAcceptanceRecord
from app.shared.db.connection import pooled_connect


def _acceptance_from_row(row: dict) -> BusinessLegalAcceptanceRecord:
    return BusinessLegalAcceptanceRecord(
        id=str(row["id"]),
        business_id=str(row["business_id"]),
        user_id=str(row["user_id"]),
        document_set=row["document_set"],
        document_version=row["document_version"],
        confirmation=row["confirmation"],
        surface=row["surface"],
        locale=row["locale"],
        request_id=row["request_id"],
        accepted_at=row["accepted_at"],
        created_at=row["created_at"],
    )


class PostgresBusinessLegalAcceptanceRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def list_for_business_user(self, *, business_id: str, user_id: str) -> list[BusinessLegalAcceptanceRecord]:
        with pooled_connect(self._database_url) as conn:
            rows = conn.execute(
                """
                select id, business_id, user_id, document_set, document_version,
                       confirmation, surface, locale, request_id, accepted_at, created_at
                from business_legal_acceptances
                where business_id = %s and user_id = %s
                order by accepted_at desc
                """,
                (business_id, user_id),
            ).fetchall()
        return [_acceptance_from_row(row) for row in rows]

    def get_for_document(
        self,
        *,
        business_id: str,
        user_id: str,
        document_set: str,
        document_version: str,
    ) -> BusinessLegalAcceptanceRecord | None:
        with pooled_connect(self._database_url) as conn:
            row = conn.execute(
                """
                select id, business_id, user_id, document_set, document_version,
                       confirmation, surface, locale, request_id, accepted_at, created_at
                from business_legal_acceptances
                where business_id = %s
                  and user_id = %s
                  and document_set = %s
                  and document_version = %s
                """,
                (business_id, user_id, document_set, document_version),
            ).fetchone()
        return _acceptance_from_row(row) if row else None

    def record_acceptance(
        self,
        *,
        business_id: str,
        user_id: str,
        document_set: str,
        document_version: str,
        confirmation: str,
        surface: str,
        locale: str,
        request_id: str,
    ) -> BusinessLegalAcceptanceRecord:
        with pooled_connect(self._database_url) as conn:
            row = conn.execute(
                """
                insert into business_legal_acceptances (
                    business_id, user_id, document_set, document_version,
                    confirmation, surface, locale, request_id, accepted_at, created_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                on conflict (business_id, user_id, document_set, document_version)
                do update set request_id = business_legal_acceptances.request_id
                returning id, business_id, user_id, document_set, document_version,
                          confirmation, surface, locale, request_id, accepted_at, created_at
                """,
                (
                    business_id,
                    user_id,
                    document_set,
                    document_version,
                    confirmation,
                    surface,
                    locale,
                    request_id,
                ),
            ).fetchone()
        return _acceptance_from_row(row)
