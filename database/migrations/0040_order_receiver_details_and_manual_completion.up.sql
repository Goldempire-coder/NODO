create table if not exists order_receiver_details (
    id uuid primary key default gen_random_uuid(),
    order_id uuid not null unique references orders(id) on delete restrict,
    bank_code text not null,
    phone text not null,
    document text not null,
    holder text not null,
    payload_hash text not null,
    shared_by_user_id uuid not null references users(id) on delete restrict,
    shared_at timestamptz not null default now(),
    constraint order_receiver_details_bank_code_check check (
        bank_code in (
            '0102', '0105', '0108', '0114', '0115', '0128', '0134', '0137',
            '0138', '0151', '0156', '0157', '0163', '0166', '0168', '0169',
            '0171', '0172', '0174', '0175', '0177', '0191'
        )
    ),
    constraint order_receiver_details_phone_check check (phone ~ '^\+58[0-9]{10}$'),
    constraint order_receiver_details_document_check check (document ~ '^[VEJGP][0-9]{6,10}$'),
    constraint order_receiver_details_holder_check check (
        char_length(holder) between 2 and 120
        and holder !~ '[<>]'
    ),
    constraint order_receiver_details_payload_hash_check check (payload_hash ~ '^[a-f0-9]{64}$')
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
            'support_message_created_participant'
        )
    );
