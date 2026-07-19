from __future__ import annotations

ORDER_NOTIFICATION_TYPES = {
    "order_created_business",
    "payment_reported_business",
    "payment_confirmed_client",
    "payment_rejected_client",
    "order_delivered_client",
    "order_disputed_parties_admin",
}

BUSINESS_STATUS_NOTIFICATION_TYPES = {
    "business_suspended_owner",
    "business_reactivated_owner",
    "business_blocked_owner",
}

TELEGRAM_NOTIFICATION_TYPES = ORDER_NOTIFICATION_TYPES | BUSINESS_STATUS_NOTIFICATION_TYPES
