from __future__ import annotations

from app.modules.business_intake.models import (
    BusinessIntakeRequestRecord,
)
from app.modules.business_intake.postgres_admin import PostgresBusinessIntakeAdminMixin
from app.modules.business_intake.postgres_conversation import PostgresBusinessIntakeConversationMixin
from app.modules.business_intake.postgres_documents import PostgresBusinessIntakeDocumentsMixin
from app.modules.business_intake.postgres_submit import PostgresBusinessIntakeSubmitMixin
from app.modules.business_intake.repository_common import (
    intake_from_row,
)
from app.shared.db.connection import pooled_connect


class PostgresBusinessIntakeRepository(
    PostgresBusinessIntakeAdminMixin,
    PostgresBusinessIntakeConversationMixin,
    PostgresBusinessIntakeDocumentsMixin,
    PostgresBusinessIntakeSubmitMixin,
):
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def get_by_update(self, *, telegram_chat_id: int, update_id: int) -> BusinessIntakeRequestRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "select * from business_intake_requests where telegram_chat_id = %s and last_update_id = %s order by updated_at desc limit 1",
                (telegram_chat_id, update_id),
            ).fetchone()
        return intake_from_row(row) if row else None

    def get_active_for_chat(self, *, telegram_chat_id: int) -> BusinessIntakeRequestRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "select * from business_intake_requests where telegram_chat_id = %s and status = 'draft' order by updated_at desc limit 1",
                (telegram_chat_id,),
            ).fetchone()
        return intake_from_row(row) if row else None

    def get_latest_for_chat(self, *, telegram_chat_id: int) -> BusinessIntakeRequestRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "select * from business_intake_requests where telegram_chat_id = %s order by updated_at desc limit 1",
                (telegram_chat_id,),
            ).fetchone()
        return intake_from_row(row) if row else None

    def create_or_get_draft(
        self,
        *,
        telegram_user_id: int,
        telegram_chat_id: int,
        update_id: int,
        referral_code: str | None,
    ) -> BusinessIntakeRequestRecord:
        existing = self.get_by_update(telegram_chat_id=telegram_chat_id, update_id=update_id)
        if existing is not None:
            return existing
        existing_draft = self.get_active_for_chat(telegram_chat_id=telegram_chat_id)
        if existing_draft is not None:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    update business_intake_requests
                    set last_update_id = %s, last_step = 'awaiting_referral_code', updated_at = now()
                    where id = %s
                    returning *
                    """,
                    (update_id, existing_draft.id),
                ).fetchone()
                conn.commit()
            return intake_from_row(row)
        with self._connect() as conn:
            row = conn.execute(
                """
                insert into business_intake_requests (
                    telegram_user_id, telegram_chat_id, referral_code, status,
                    last_step, last_update_id, created_at, updated_at
                )
                values (%s, %s, %s, 'draft', 'awaiting_referral_code', %s, now(), now())
                returning *
                """,
                (telegram_user_id, telegram_chat_id, referral_code, update_id),
            ).fetchone()
            conn.commit()
        return intake_from_row(row)

    def get(self, intake_id: str) -> BusinessIntakeRequestRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from business_intake_requests where id = %s", (intake_id,)).fetchone()
        return intake_from_row(row) if row else None

    def save_contact(self, *, intake: BusinessIntakeRequestRecord, update_id: int, contact_phone: str) -> BusinessIntakeRequestRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                update business_intake_requests
                set contact_phone = %s, last_update_id = %s, last_step = 'awaiting_business_name', updated_at = now()
                where id = %s
                returning *
                """,
                (contact_phone, update_id, intake.id),
            ).fetchone()
            conn.commit()
        return intake_from_row(row)


