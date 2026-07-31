update notification_jobs
set status = 'skipped',
    last_error_code = 'ROLLBACK_NOTIFICATION_TYPE_UNAVAILABLE',
    notification_type = case
        when notification_type = 'order_receiver_details_shared_business'
            then 'order_created_business'
        else 'order_delivered_client'
    end,
    updated_at = now()
where notification_type in (
    'order_receiver_details_shared_business',
    'order_completed_business'
);

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
            'support_message_created_participant'
        )
    );

drop table if exists order_receiver_details;
