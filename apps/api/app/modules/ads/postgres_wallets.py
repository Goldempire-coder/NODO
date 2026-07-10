from __future__ import annotations

from app.modules.ads.models import CreditWalletRecord
from app.modules.ads.row_mappers import wallet_from_row


class PostgresAdWalletsMixin:
    def ensure_wallet(self, business_id: str) -> CreditWalletRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                insert into credit_wallets (business_id, available_credits, blocked_credits, consumed_credits, created_at, updated_at)
                values (%s, 0, 0, 0, now(), now())
                on conflict (business_id) do update set updated_at = credit_wallets.updated_at
                returning *
                """,
                (business_id,),
            ).fetchone()
            conn.commit()
        return wallet_from_row(row)

    def get_wallet(self, business_id: str) -> CreditWalletRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute("select * from credit_wallets where business_id = %s", (business_id,)).fetchone()
        return wallet_from_row(row) if row else None
