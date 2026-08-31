alter table notification_jobs
    drop constraint if exists notification_jobs_type_check;

alter table notification_jobs
    add constraint notification_jobs_type_check
    check (
        notification_type in (
            'order_payment_deadline_warning',
            'order_cancelled_payment_not_reported',
            'order_business_response_warning',
            'order_disputed_business_no_payment_confirmation',
            'order_delivery_warning',
            'order_disputed_business_confirmed_payment_but_not_delivered',
            'delivered_reminder_immediate',
            'delivered_reminder_12h',
            'delivered_reminder_23h',
            'order_auto_completed_after_24h',
            'ad_expired',
            'founder_access_expired',
            'order_created_business',
            'payment_reported_business',
            'payment_confirmed_client',
            'payment_rejected_client',
            'order_delivered_client',
            'order_disputed_parties_admin',
            'order_cancelled_business_unavailable',
            'order_receiver_details_shared_business',
            'order_completed_business',
            'business_suspended_owner',
            'business_reactivated_owner',
            'business_blocked_owner',
            'user_suspended_account',
            'user_reactivated_account',
            'user_blocked_account',
            'business_access_suspended_owner',
            'business_access_reactivated_owner',
            'business_access_blocked_owner',
            'business_access_revoked_owner',
            'support_ticket_resolved_participant',
            'support_ticket_closed_participant',
            'order_message_created_business',
            'order_message_created_client',
            'support_message_created_participant',
            'admin_alert_test',
            'admin_alert_business_intake_submitted',
            'admin_alert_credit_purchase_attention',
            'admin_alert_dispute_opened'
        )
    );
