from __future__ import annotations

from app.modules.businesses.models import BusinessPaymentMethodRecord, new_id


class InMemoryBusinessPaymentMethodsMixin:
    def add_payment_method(
        self,
        *,
        business_id: str,
        method_type: str,
        network: str | None,
        account_value: str,
        account_masked: str,
        holder_name: str,
    ) -> BusinessPaymentMethodRecord:
        with self._lock:  # type: ignore[attr-defined]
            method = BusinessPaymentMethodRecord(
                id=new_id(),
                business_id=business_id,
                method_type=method_type,
                network=network,
                account_value=account_value,
                account_masked=account_masked,
                holder_name=holder_name,
            )
            self.payment_methods[method.id] = method  # type: ignore[attr-defined]
            return method

    def get_payment_method(self, payment_method_id: str) -> BusinessPaymentMethodRecord | None:
        return self.payment_methods.get(payment_method_id)  # type: ignore[attr-defined]

    def list_payment_methods_for_business(self, business_id: str) -> list[BusinessPaymentMethodRecord]:
        return [method for method in self.payment_methods.values() if method.business_id == business_id]  # type: ignore[attr-defined]
