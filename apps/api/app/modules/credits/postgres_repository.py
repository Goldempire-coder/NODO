from __future__ import annotations

from app.modules.ads.models import CreditLedgerRecord, CreditWalletRecord
from app.modules.businesses.models import FileAssetRecord
from app.modules.credits.models import CreditPurchaseRecord, ReferralCodeRecord, ReferralEventRecord
from app.modules.credits.postgres_referral_bonus import award_referral_on_business_approval_pg
from app.modules.credits.postgres_admin_adjustment import adjust_wallet_pg
from app.modules.credits.postgres_purchases import (
    apply_onchain_verification_pg,
    approve_purchase_pg,
    create_base_usdc_purchase_pg,
    create_manual_purchase_pg,
    create_stripe_purchase_pg,
    find_purchase_by_checkout_session_pg,
    get_purchase_pg,
    list_purchases_pg,
    list_onchain_pending_purchases_pg,
    reject_purchase_pg,
    stripe_event_processed_pg,
)
from app.modules.credits.postgres_referrals import admin_referral_summary_pg, apply_referral_code_pg, get_or_create_referral_code_pg, list_referral_events_for_business_pg
from app.modules.credits.row_mappers import ledger_from_row, wallet_from_row
from app.shared.db.connection import pooled_connect


class PostgresCreditRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def ensure_wallet(self, business_id: str) -> CreditWalletRecord:
        with self._connect() as conn:
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
        with self._connect() as conn:
            row = conn.execute("select * from credit_wallets where business_id = %s", (business_id,)).fetchone()
        return wallet_from_row(row) if row else None

    def list_ledger(self, *, business_id: str, ledger_type: str | None, cursor: str | None, limit: int) -> tuple[list[CreditLedgerRecord], str | None]:
        sql = "select * from credits_ledger where business_id = %s"
        params: list[object] = [business_id]
        if ledger_type:
            sql += " and type = %s"
            params.append(ledger_type)
        if cursor:
            sql += " and created_at < %s"
            params.append(cursor)
        sql += " order by created_at desc limit %s"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        items = [ledger_from_row(row) for row in rows]
        return items, items[-1].created_at.isoformat() if len(items) == limit else None

    def create_stripe_purchase(self, *, business_id: str, package_code: str, idempotency_key: str) -> CreditPurchaseRecord:
        return create_stripe_purchase_pg(self._connect, business_id=business_id, package_code=package_code, idempotency_key=idempotency_key)

    def create_manual_purchase(
        self,
        *,
        business_id: str,
        owner_user_id: str,
        package_code: str,
        payment_method: str,
        idempotency_key: str,
        storage_path: str,
        mime_type: str,
        size_bytes: int,
        manual_payment_reference: str | None,
        manual_tx_hash: str | None,
        manual_network: str | None,
    ) -> tuple[CreditPurchaseRecord, FileAssetRecord]:
        return create_manual_purchase_pg(
            self._connect,
            business_id=business_id,
            owner_user_id=owner_user_id,
            package_code=package_code,
            payment_method=payment_method,
            idempotency_key=idempotency_key,
            storage_path=storage_path,
            mime_type=mime_type,
            size_bytes=size_bytes,
            manual_payment_reference=manual_payment_reference,
            manual_tx_hash=manual_tx_hash,
            manual_network=manual_network,
        )

    def create_base_usdc_purchase(
        self,
        *,
        business_id: str,
        package_code: str,
        idempotency_key: str,
        expected_amount_units: int,
        destination_wallet_address: str,
        expires_at,
    ) -> CreditPurchaseRecord:  # type: ignore[no-untyped-def]
        return create_base_usdc_purchase_pg(
            self._connect,
            business_id=business_id,
            package_code=package_code,
            idempotency_key=idempotency_key,
            expected_amount_units=expected_amount_units,
            destination_wallet_address=destination_wallet_address,
            expires_at=expires_at,
        )

    def get_purchase(self, purchase_id: str) -> CreditPurchaseRecord | None:
        return get_purchase_pg(self._connect, purchase_id)

    def find_purchase_by_checkout_session(self, session_id: str) -> CreditPurchaseRecord | None:
        return find_purchase_by_checkout_session_pg(self._connect, session_id)

    def stripe_event_processed(self, event_id: str) -> bool:
        return stripe_event_processed_pg(self._connect, event_id)

    def approve_purchase(self, *, purchase: CreditPurchaseRecord, actor_user_id: str | None, event_id: str | None = None, payment_intent_id: str | None = None, admin_note: str | None = None) -> tuple[CreditPurchaseRecord, CreditLedgerRecord | None]:
        return approve_purchase_pg(self._connect, purchase=purchase, actor_user_id=actor_user_id, event_id=event_id, payment_intent_id=payment_intent_id, admin_note=admin_note)

    def apply_onchain_verification(self, *, purchase: CreditPurchaseRecord, verification, actor_user_id: str | None, min_confirmations: int) -> tuple[CreditPurchaseRecord, CreditLedgerRecord | None]:  # type: ignore[no-untyped-def]
        return apply_onchain_verification_pg(
            self._connect,
            purchase=purchase,
            verification=verification,
            actor_user_id=actor_user_id,
            min_confirmations=min_confirmations,
        )

    def reject_purchase(self, *, purchase: CreditPurchaseRecord, admin_user_id: str, reason: str) -> CreditPurchaseRecord:
        return reject_purchase_pg(self._connect, purchase=purchase, admin_user_id=admin_user_id, reason=reason)

    def list_purchases(self, *, status: str | None, business_id: str | None, cursor: str | None, limit: int) -> tuple[list[CreditPurchaseRecord], str | None]:
        return list_purchases_pg(self._connect, status=status, business_id=business_id, cursor=cursor, limit=limit)

    def list_onchain_pending_purchases(self, *, limit: int) -> list[CreditPurchaseRecord]:
        return list_onchain_pending_purchases_pg(self._connect, limit=limit)

    def adjust_wallet(self, *, business_id: str, amount: int, direction: str, reason: str, notes: str | None, created_by: str) -> CreditLedgerRecord:
        return adjust_wallet_pg(self._connect, business_id=business_id, amount=amount, direction=direction, reason=reason, notes=notes, created_by=created_by)

    def get_or_create_referral_code(self, business_id: str) -> ReferralCodeRecord:
        return get_or_create_referral_code_pg(self._connect, business_id)

    def apply_referral_code(self, *, referred_business_id: str, referral_code: str) -> ReferralEventRecord:
        return apply_referral_code_pg(self._connect, referred_business_id=referred_business_id, referral_code=referral_code)

    def list_referral_events_for_business(self, business_id: str) -> list[ReferralEventRecord]:
        return list_referral_events_for_business_pg(self._connect, business_id)

    def award_referral_on_business_approval(self, *, referred_business_id: str, referral_code: str | None, actor_user_id: str | None):  # type: ignore[no-untyped-def]
        return award_referral_on_business_approval_pg(
            self._connect,
            referred_business_id=referred_business_id,
            referral_code=referral_code,
            actor_user_id=actor_user_id,
        )

    def admin_referral_summary(self, business_id: str) -> dict:
        return admin_referral_summary_pg(self._connect, business_id)
