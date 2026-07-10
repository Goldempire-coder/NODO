create table if not exists credit_wallets (
    id uuid primary key default gen_random_uuid(),
    business_id uuid not null references businesses(id),
    available_credits integer not null default 0,
    blocked_credits integer not null default 0,
    consumed_credits integer not null default 0,
    lifetime_purchased_credits integer not null default 0,
    lifetime_bonus_credits integer not null default 0,
    lifetime_adjusted_credits integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint credit_wallets_business_unique unique (business_id),
    constraint credit_wallets_balances_check check (
        available_credits >= 0
        and blocked_credits >= 0
        and consumed_credits >= 0
        and lifetime_purchased_credits >= 0
        and lifetime_bonus_credits >= 0
        and lifetime_adjusted_credits >= 0
    )
);

create table if not exists ads (
    id uuid primary key default gen_random_uuid(),
    business_id uuid not null references businesses(id),
    payment_method_id uuid not null references business_payment_methods(id),
    payment_method text not null,
    delivery_method text not null,
    rate_bs_per_usd numeric(18,6) not null,
    amount_min_usd numeric(12,2) not null,
    amount_max_usd numeric(12,2) not null,
    required_credits integer not null,
    status text not null default 'active',
    credit_hold_ledger_id uuid null,
    credit_consumed_ledger_id uuid null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    activated_at timestamptz null,
    expires_at timestamptz null,
    last_rate_updated_at timestamptz null,
    constraint ads_payment_method_check check (payment_method in ('zelle', 'usdt_trc20')),
    constraint ads_delivery_method_check check (delivery_method in ('pago_movil_ve')),
    constraint ads_status_check check (status in ('draft', 'active', 'in_order', 'paused', 'expired', 'archived', 'suspended')),
    constraint ads_amount_range_check check (
        amount_min_usd >= 20
        and amount_max_usd >= amount_min_usd
        and amount_max_usd <= 2000
    ),
    constraint ads_required_credits_check check (required_credits in (1, 2, 3)),
    constraint ads_rate_check check (rate_bs_per_usd > 0),
    constraint ads_active_dates_check check (
        status not in ('active', 'paused', 'in_order')
        or (activated_at is not null and expires_at is not null)
    )
);

create table if not exists credits_ledger (
    id uuid primary key default gen_random_uuid(),
    business_id uuid not null references businesses(id),
    type text not null,
    amount integer not null,
    available_before integer not null,
    available_after integer not null,
    blocked_before integer not null,
    blocked_after integer not null,
    consumed_before integer not null,
    consumed_after integer not null,
    related_ad_id uuid null references ads(id),
    related_order_id uuid null,
    related_referral_id uuid null,
    related_credit_purchase_id uuid null,
    reason text not null,
    source text not null,
    reference_type text not null,
    reference_id uuid not null,
    notes text null,
    created_by uuid null references users(id),
    created_at timestamptz not null default now(),
    constraint credits_ledger_type_check check (type in ('purchase', 'founder_free_use', 'hold', 'consume', 'release', 'refund', 'adjustment')),
    constraint credits_ledger_amount_check check (amount > 0),
    constraint credits_ledger_balances_check check (
        available_before >= 0
        and available_after >= 0
        and blocked_before >= 0
        and blocked_after >= 0
        and consumed_before >= 0
        and consumed_after >= 0
    ),
    constraint credits_ledger_hold_reference_check check (
        type <> 'hold'
        or (related_ad_id is not null and reference_type = 'ad' and reference_id = related_ad_id)
    ),
    constraint credits_ledger_release_reference_check check (
        type <> 'release'
        or (related_ad_id is not null and reference_type = 'ad' and reference_id = related_ad_id)
    )
);

alter table ads
    add constraint ads_credit_hold_ledger_fk
    foreign key (credit_hold_ledger_id) references credits_ledger(id);

alter table ads
    add constraint ads_credit_consumed_ledger_fk
    foreign key (credit_consumed_ledger_id) references credits_ledger(id);

create unique index if not exists credit_wallets_business_id_idx
    on credit_wallets(business_id);

create index if not exists ads_marketplace_active_idx
    on ads(payment_method, delivery_method, amount_min_usd, amount_max_usd, rate_bs_per_usd desc, created_at desc)
    where status = 'active';

create index if not exists ads_business_status_created_idx
    on ads(business_id, status, created_at desc);

create index if not exists ads_expires_status_idx
    on ads(status, expires_at)
    where status in ('active', 'paused');

create index if not exists ads_payment_method_id_idx
    on ads(payment_method_id);

create index if not exists ads_no_overlap_lookup_idx
    on ads(business_id, payment_method, delivery_method, amount_min_usd, amount_max_usd)
    where status in ('active', 'paused');

create index if not exists credits_ledger_business_created_idx
    on credits_ledger(business_id, created_at desc);

create index if not exists credits_ledger_type_created_idx
    on credits_ledger(type, created_at desc);

create index if not exists credits_ledger_reference_created_idx
    on credits_ledger(reference_type, reference_id, created_at desc);

create index if not exists credits_ledger_related_ad_idx
    on credits_ledger(related_ad_id)
    where related_ad_id is not null;

create unique index if not exists credits_ledger_active_hold_per_ad_idx
    on credits_ledger(related_ad_id)
    where type = 'hold' and related_ad_id is not null;
