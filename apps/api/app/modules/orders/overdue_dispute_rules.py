from __future__ import annotations

# Each reason belongs to one source state and one deadline, even for stale jobs.
OVERDUE_DISPUTE_RULES = {
    "business_no_payment_confirmation": (
        "payment_reported",
        "business_response_deadline_at",
        "order_disputed_business_no_payment_confirmation",
    ),
    "business_confirmed_payment_but_not_delivered": (
        "payment_confirmed",
        "delivery_deadline_at",
        "order_disputed_business_confirmed_payment_but_not_delivered",
    ),
}
OVERDUE_DISPUTE_DESCRIPTION = (
    "Disputa abierta automaticamente por vencimiento de deadline operativo."
)
