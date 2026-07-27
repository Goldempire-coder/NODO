create index if not exists business_capacity_reservations_consumed_daily_idx
    on business_capacity_reservations (business_id, consumed_at)
    include (amount_usd, order_id, created_at)
    where status = 'consumed' and consumed_at is not null;

