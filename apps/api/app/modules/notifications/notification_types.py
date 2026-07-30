from __future__ import annotations

ORDER_NOTIFICATION_TYPES = {
    "order_created_business",
    "payment_reported_business",
    "payment_confirmed_client",
    "payment_rejected_client",
    "order_delivered_client",
    "order_disputed_parties_admin",
    "order_cancelled_payment_not_reported",
    "order_cancelled_business_unavailable",
}

CHAT_NOTIFICATION_TYPES = {
    "order_message_created_business",
    "order_message_created_client",
}

BUSINESS_STATUS_NOTIFICATION_TYPES = {
    "business_suspended_owner",
    "business_reactivated_owner",
    "business_blocked_owner",
}

USER_STATUS_NOTIFICATION_TYPES = {
    "user_suspended_account",
    "user_reactivated_account",
    "user_blocked_account",
}

BUSINESS_ACCESS_NOTIFICATION_TYPES = {
    "business_access_suspended_owner",
    "business_access_reactivated_owner",
    "business_access_blocked_owner",
    "business_access_revoked_owner",
}

SUPPORT_NOTIFICATION_TYPES = {
    "support_message_created_participant",
    "support_ticket_resolved_participant",
    "support_ticket_closed_participant",
}

TELEGRAM_NOTIFICATION_TYPES = (
    ORDER_NOTIFICATION_TYPES
    | CHAT_NOTIFICATION_TYPES
    | BUSINESS_STATUS_NOTIFICATION_TYPES
    | USER_STATUS_NOTIFICATION_TYPES
    | BUSINESS_ACCESS_NOTIFICATION_TYPES
    | SUPPORT_NOTIFICATION_TYPES
)
