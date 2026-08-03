from __future__ import annotations

from app.modules.businesses.models import BusinessPaymentMethodRecord
from app.modules.businesses.row_mappers import payment_method_from_row


class PostgresBusinessPaymentMethodsMixin:
    def add_payment_method(
        self,
        *,
        business_id: str,
        method_type: str,
        network: str | None,
        account_value: str,
        account_masked: str,
        holder_name: str,
        verified_status: str = "pending",
        active: bool = False,
    ) -> BusinessPaymentMethodRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                insert into business_payment_methods (
                    business_id, method_type, network, account_value, account_masked,
                    holder_name, verified_status, active, created_at, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                returning *
                """,
                (business_id, method_type, network, account_value, account_masked, holder_name, verified_status, active),
            ).fetchone()
            conn.commit()
        return payment_method_from_row(row)

    def get_payment_method(self, payment_method_id: str) -> BusinessPaymentMethodRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute("select * from business_payment_methods where id = %s", (payment_method_id,)).fetchone()
        if row is None:
            return None
        return payment_method_from_row(row)

    def list_payment_methods_for_business(self, business_id: str) -> list[BusinessPaymentMethodRecord]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(
                "select * from business_payment_methods where business_id = %s order by created_at desc",
                (business_id,),
            ).fetchall()
        return [payment_method_from_row(row) for row in rows]

    def update_payment_method(
        self,
        payment_method_id: str,
        *,
        network: str | None,
        account_value: str,
        account_masked: str,
        holder_name: str,
    ) -> BusinessPaymentMethodRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                update business_payment_methods
                   set network = %s,
                       account_value = %s,
                       account_masked = %s,
                       holder_name = %s,
                       updated_at = now()
                 where id = %s
                returning *
                """,
                (network, account_value, account_masked, holder_name, payment_method_id),
            ).fetchone()
            conn.commit()
        if row is None:
            return None
        return payment_method_from_row(row)

    def deactivate_payment_method(self, payment_method_id: str) -> BusinessPaymentMethodRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                update business_payment_methods
                   set active = false,
                       updated_at = now()
                 where id = %s
                returning *
                """,
                (payment_method_id,),
            ).fetchone()
            conn.commit()
        if row is None:
            return None
        return payment_method_from_row(row)
