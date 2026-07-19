alter table business_intake_requests
    add column if not exists business_tax_id text,
    add column if not exists responsible_id_number text,
    add column if not exists daily_limit_usd numeric(12,2);

alter table business_intake_requests
    drop constraint if exists business_intake_requests_daily_limit_check;

alter table business_intake_requests
    add constraint business_intake_requests_daily_limit_check
    check (daily_limit_usd is null or daily_limit_usd > 0);
