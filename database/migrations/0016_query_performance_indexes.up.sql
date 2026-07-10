create index if not exists users_remitter_phone_updated_idx
    on users (updated_at desc)
    where role = 'remitter' and phone is not null and phone <> '';

create index if not exists businesses_created_at_idx
    on businesses (created_at desc);

create index if not exists businesses_risk_level_created_idx
    on businesses (risk_level, created_at desc);

create index if not exists orders_created_at_idx
    on orders (created_at desc);

create index if not exists orders_active_created_idx
    on orders (created_at desc)
    where status not in ('completed', 'cancelled');

create index if not exists credit_purchases_created_at_idx
    on credit_purchases (created_at desc);

create index if not exists disputes_created_at_idx
    on disputes (created_at desc);

create index if not exists job_runs_created_at_idx
    on job_runs (created_at desc);

create index if not exists business_intake_requests_created_at_idx
    on business_intake_requests (created_at desc);

create index if not exists business_intake_requests_chat_status_updated_idx
    on business_intake_requests (telegram_chat_id, status, updated_at desc);

create index if not exists business_intake_requests_chat_updated_idx
    on business_intake_requests (telegram_chat_id, updated_at desc);

create index if not exists referral_events_referred_created_idx
    on referral_events (referred_business_id, created_at desc);
