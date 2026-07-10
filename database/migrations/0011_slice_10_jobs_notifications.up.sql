alter table job_runs add column if not exists duration_ms integer null;
alter table job_runs add column if not exists lock_acquired boolean not null default false;
alter table job_runs add column if not exists processed_count integer not null default 0;
alter table job_runs add column if not exists changed_count integer not null default 0;
alter table job_runs add column if not exists skipped_count integer not null default 0;
alter table job_runs add column if not exists failed_count integer not null default 0;

alter table job_runs drop constraint if exists job_runs_status_check;
alter table job_runs
    add constraint job_runs_status_check check (status in ('started', 'finished', 'failed', 'skipped', 'lock_not_acquired'));

alter table job_runs drop constraint if exists job_runs_job_type_check;
alter table job_runs
    add constraint job_runs_job_type_check check (job_type in ('expire_and_escalate_orders'));

alter table job_runs drop constraint if exists job_runs_duration_non_negative_check;
alter table job_runs
    add constraint job_runs_duration_non_negative_check check (duration_ms is null or duration_ms >= 0);

alter table job_runs drop constraint if exists job_runs_attempts_non_negative_check;
alter table job_runs
    add constraint job_runs_attempts_non_negative_check check (attempts >= 0);

alter table job_runs drop constraint if exists job_runs_counters_non_negative_check;
alter table job_runs
    add constraint job_runs_counters_non_negative_check check (
        processed_count >= 0
        and changed_count >= 0
        and skipped_count >= 0
        and failed_count >= 0
    );

alter table job_runs drop constraint if exists job_runs_terminal_finished_at_check;
alter table job_runs
    add constraint job_runs_terminal_finished_at_check check (
        status not in ('finished', 'failed', 'skipped', 'lock_not_acquired')
        or finished_at is not null
    );

alter table job_runs drop constraint if exists job_runs_failed_error_check;
alter table job_runs
    add constraint job_runs_failed_error_check check (status <> 'failed' or error_code is not null);

create table if not exists notification_jobs (
    id uuid primary key default gen_random_uuid(),
    notification_type text not null,
    recipient_user_id uuid null references users(id),
    recipient_role text null,
    order_id uuid null references orders(id),
    business_id uuid null references businesses(id),
    dispute_id uuid null references disputes(id),
    status text not null default 'pending',
    scheduled_for timestamptz not null,
    sent_at timestamptz null,
    failed_at timestamptz null,
    attempts integer not null default 0,
    max_attempts integer not null default 3,
    last_error_code text null,
    dedupe_key text not null,
    metadata_json jsonb null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint notification_jobs_status_check check (status in ('pending', 'sent', 'failed', 'skipped', 'cancelled')),
    constraint notification_jobs_attempts_check check (attempts >= 0 and max_attempts > 0),
    constraint notification_jobs_recipient_check check (recipient_user_id is not null or recipient_role is not null),
    constraint notification_jobs_recipient_role_check check (
        recipient_role is null or recipient_role in ('remitter', 'business_owner', 'admin', 'support', 'super_admin')
    )
);

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
            'founder_access_expired'
        )
    );

alter table notification_jobs drop constraint if exists notification_jobs_terminal_timestamp_check;
alter table notification_jobs
    add constraint notification_jobs_terminal_timestamp_check check (
        (sent_at is null or status = 'sent')
        and (failed_at is null or status = 'failed')
        and (status <> 'failed' or failed_at is not null)
    );

create unique index if not exists notification_jobs_dedupe_key_unique_idx
    on notification_jobs(dedupe_key);

create index if not exists notification_jobs_status_scheduled_idx
    on notification_jobs(status, scheduled_for asc);

create index if not exists notification_jobs_type_status_scheduled_idx
    on notification_jobs(notification_type, status, scheduled_for asc);

create index if not exists notification_jobs_order_type_created_idx
    on notification_jobs(order_id, notification_type, created_at desc)
    where order_id is not null;

create index if not exists notification_jobs_business_type_created_idx
    on notification_jobs(business_id, notification_type, created_at desc)
    where business_id is not null;

create index if not exists notification_jobs_dispute_type_created_idx
    on notification_jobs(dispute_id, notification_type, created_at desc)
    where dispute_id is not null;

create index if not exists job_runs_job_type_started_at_idx
    on job_runs(job_type, started_at desc);

create index if not exists job_runs_job_type_status_created_idx
    on job_runs(job_type, status, created_at desc);

create index if not exists job_runs_lock_key_idx
    on job_runs(lock_key)
    where lock_key is not null;

create index if not exists orders_waiting_payment_deadline_idx
    on orders(status, payment_report_deadline_at)
    where status = 'waiting_payment';

create index if not exists orders_payment_confirmed_delivery_warning_idx
    on orders(status, delivery_warning_at)
    where status = 'payment_confirmed';

create index if not exists orders_payment_confirmed_delivery_deadline_idx
    on orders(status, delivery_deadline_at)
    where status = 'payment_confirmed';

create index if not exists orders_delivered_auto_complete_idx
    on orders(status, auto_complete_at)
    where status = 'delivered';

create index if not exists ads_status_expires_at_idx
    on ads(status, expires_at)
    where status in ('active', 'paused');

create index if not exists businesses_founder_status_expires_at_idx
    on businesses(founder_status, founder_expires_at)
    where founder_status = 'active';
