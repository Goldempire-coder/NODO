alter table business_intake_requests
    drop constraint if exists business_intake_requests_daily_limit_check;

alter table business_intake_requests
    drop column if exists daily_limit_usd,
    drop column if exists responsible_id_number,
    drop column if exists business_tax_id;
