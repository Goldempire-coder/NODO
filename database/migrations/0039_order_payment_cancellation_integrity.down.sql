drop index if exists payment_reports_network_tx_hash_unique_idx;
drop index if exists payment_reports_proof_content_sha256_unique_idx;
drop index if exists payment_reports_proof_file_unique_idx;

alter table payment_reports drop constraint if exists payment_reports_tx_hash_format_check;
alter table payment_reports drop constraint if exists payment_reports_proof_content_sha256_check;
alter table payment_reports drop column if exists proof_content_sha256;

update orders
set cancel_reason = 'remitter_cancelled_before_payment'
where cancel_reason = 'business_unavailable';

alter table orders drop constraint if exists orders_cancel_reason_check;
alter table orders
    add constraint orders_cancel_reason_check check (
        cancel_reason is null
        or cancel_reason in (
            'remitter_cancelled_before_payment',
            'payment_not_reported_in_time',
            'admin_cancelled'
        )
    );

update notification_jobs
set notification_type = 'order_cancelled_payment_not_reported',
    status = case
        when status = 'pending' then 'skipped'
        else status
    end,
    last_error_code = case
        when status = 'pending' then 'SLICE_49A_ROLLED_BACK'
        else last_error_code
    end,
    metadata_json = coalesce(metadata_json, '{}'::jsonb)
        || jsonb_build_object(
            'rolled_back_notification_type',
            'order_cancelled_business_unavailable'
        )
where notification_type = 'order_cancelled_business_unavailable';

alter table notification_jobs drop constraint if exists notification_jobs_type_check;
alter table notification_jobs
    add constraint notification_jobs_type_check check (
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
