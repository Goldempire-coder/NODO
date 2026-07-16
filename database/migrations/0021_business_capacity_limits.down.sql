alter table businesses drop constraint if exists businesses_limits_check;

alter table businesses alter column daily_limit_usd set default 300.00;

update businesses
set daily_limit_usd = 300.00
where trust_level = 'new'
  and daily_limit_usd = 1000.00;

alter table businesses drop column if exists min_order_amount_usd;

alter table businesses
    add constraint businesses_limits_check check (
        max_order_amount_usd >= 0
        and daily_limit_usd >= 0
        and active_order_limit >= 0
        and completed_orders_count >= 0
        and disputes_count >= 0
        and evasion_reports_count >= 0
        and referral_credits_earned >= 0
    );
