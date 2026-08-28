alter table credit_purchases
    add column if not exists owner_dismissed_at timestamptz null,
    add column if not exists owner_dismissed_by_user_id uuid null references users(id) on delete set null;

create index if not exists credit_purchases_contract_owner_dismissed_idx
    on credit_purchases(business_id, created_at, id)
    where payment_method = 'base_usdc_contract'
      and status = 'pending_payment'
      and owner_dismissed_at is not null;
