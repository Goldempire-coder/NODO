alter table businesses
    add column if not exists min_order_amount_usd numeric(12,2) not null default 20.00;

alter table businesses alter column daily_limit_usd set default 1000.00;

update businesses
set daily_limit_usd = 1000.00
where trust_level = 'new'
  and daily_limit_usd = 300.00;

update businesses
set max_order_amount_usd = min_order_amount_usd
where max_order_amount_usd < min_order_amount_usd;

alter table businesses drop constraint if exists businesses_limits_check;

alter table businesses
    add constraint businesses_limits_check check (
        min_order_amount_usd >= 0
        and max_order_amount_usd >= min_order_amount_usd
        and daily_limit_usd >= 0
        and active_order_limit >= 0
        and completed_orders_count >= 0
        and disputes_count >= 0
        and evasion_reports_count >= 0
        and referral_credits_earned >= 0
    );
