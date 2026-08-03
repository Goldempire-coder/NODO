from __future__ import annotations

from app.modules.businesses.models import utc_now
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
        verified_status: str = "pending",
        active: bool = False,
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
                verified_status=verified_status,
                active=active,
            )
            self.payment_methods[method.id] = method  # type: ignore[attr-defined]
            return method

    def get_payment_method(self, payment_method_id: str) -> BusinessPaymentMethodRecord | None:
        return self.payment_methods.get(payment_method_id)  # type: ignore[attr-defined]

    def list_payment_methods_for_business(self, business_id: str) -> list[BusinessPaymentMethodRecord]:
        return [method for method in self.payment_methods.values() if method.business_id == business_id]  # type: ignore[attr-defined]

    def update_payment_method(
        self,
        payment_method_id: str,
        *,
        network: str | None,
        account_value: str,
        account_masked: str,
        holder_name: str,
    ) -> BusinessPaymentMethodRecord | None:
        with self._lock:  # type: ignore[attr-defined]
            method = self.payment_methods.get(payment_method_id)  # type: ignore[attr-defined]
            if method is None:
                return None
            method.network = network
            method.account_value = account_value
            method.account_masked = account_masked
            method.holder_name = holder_name
            method.updated_at = utc_now()
            return method

    def deactivate_payment_method(self, payment_method_id: str) -> BusinessPaymentMethodRecord | None:
        with self._lock:  # type: ignore[attr-defined]
            method = self.payment_methods.get(payment_method_id)  # type: ignore[attr-defined]
            if method is None:
                return None
            method.active = False
            method.updated_at = utc_now()
            return method
