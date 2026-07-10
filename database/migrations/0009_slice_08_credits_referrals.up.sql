alter table credits_ledger drop constraint if exists credits_ledger_type_check;

alter table credits_ledger
    add constraint credits_ledger_type_check check (
        type in (
            'purchase',
            'founder_free_use',
            'referral_bonus',
            'hold',
            'consume',
            'release',
            'expire',
            'admin_adjustment'
        )
    );

alter table file_assets drop constraint if exists file_assets_resource_type_check;
alter table file_assets drop constraint if exists file_assets_file_type_check;

alter table file_assets
    add constraint file_assets_resource_type_check check (
        resource_type in ('business', 'payment_report', 'message', 'credit_purchase')
    );

alter table file_assets
    add constraint file_assets_file_type_check check (
        file_type in (
            'rif_document',
            'business_license',
            'owner_identity',
            'address_proof',
            'payment_evidence',
            'message_attachment',
            'credit_purchase_proof'
        )
    );

create table if not exists credit_purchases (
    id uuid primary key default gen_random_uuid(),
    business_id uuid not null references businesses(id),
    package_code text not null,
    credits_amount integer not null,
    price_usd numeric(12,2) not null,
    payment_method text not null,
    status text not null,
    idempotency_key text null,
    stripe_checkout_session_id text null,
    stripe_payment_intent_id text null,
    stripe_event_id text null,
    manual_payment_reference text null,
    manual_tx_hash text null,
    manual_network text null,
    proof_file_id uuid null references file_assets(id),
    approved_by_admin_id uuid null references users(id),
    rejected_by_admin_id uuid null references users(id),
    admin_note text null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    paid_at timestamptz null,
    approved_at timestamptz null,
    rejected_at timestamptz null,
    failed_at timestamptz null,
    expired_at timestamptz null,
    constraint credit_purchases_package_check check (package_code in ('starter', 'pro', 'business', 'enterprise')),
    constraint credit_purchases_credits_amount_check check (credits_amount > 0),
    constraint credit_purchases_price_check check (price_usd > 0),
    constraint credit_purchases_method_check check (
        payment_method in ('stripe_checkout', 'zelle_manual_admin_approved', 'usdt_manual_admin_approved')
    ),
    constraint credit_purchases_status_check check (
        status in ('created', 'pending_payment', 'pending_manual_review', 'paid', 'approved', 'rejected', 'failed', 'expired')
    ),
    constraint credit_purchases_stripe_shape_check check (
        payment_method <> 'stripe_checkout'
        or stripe_checkout_session_id is not null
    ),
    constraint credit_purchases_manual_shape_check check (
        payment_method = 'stripe_checkout'
        or (status = 'pending_manual_review' and proof_file_id is not null)
        or status in ('approved', 'rejected', 'failed', 'expired')
    ),
    constraint credit_purchases_zelle_shape_check check (
        payment_method <> 'zelle_manual_admin_approved'
        or manual_payment_reference is not null
    ),
    constraint credit_purchases_usdt_shape_check check (
        payment_method <> 'usdt_manual_admin_approved'
        or (manual_tx_hash is not null and manual_network = 'TRC20')
    ),
    constraint credit_purchases_admin_reason_check check (
        status not in ('approved', 'rejected')
        or payment_method = 'stripe_checkout'
        or admin_note is not null
    )
);

create table if not exists referral_codes (
    id uuid primary key default gen_random_uuid(),
    business_id uuid not null references businesses(id),
    code text not null,
    status text not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    disabled_at timestamptz null,
    constraint referral_codes_business_unique unique (business_id),
    constraint referral_codes_code_unique unique (code),
    constraint referral_codes_status_check check (status in ('active', 'disabled')),
    constraint referral_codes_code_shape_check check (code ~ '^[A-Z0-9_-]{4,32}$')
);

create table if not exists referral_events (
    id uuid primary key default gen_random_uuid(),
    referral_code_id uuid not null references referral_codes(id),
    referrer_business_id uuid not null references businesses(id),
    referred_business_id uuid not null references businesses(id),
    related_credit_purchase_id uuid null references credit_purchases(id),
    status text not null default 'pending',
    credits_awarded integer not null default 0,
    reject_reason text null,
    created_at timestamptz not null default now(),
    approved_at timestamptz null,
    rewarded_at timestamptz null,
    rejected_at timestamptz null,
    constraint referral_events_status_check check (status in ('pending', 'approved', 'rewarded', 'rejected')),
    constraint referral_events_no_self_check check (referrer_business_id <> referred_business_id),
    constraint referral_events_credits_awarded_check check (credits_awarded >= 0 and credits_awarded <= 20)
);

alter table credits_ledger
    drop constraint if exists credits_ledger_related_credit_purchase_fk;

alter table credits_ledger
    add constraint credits_ledger_related_credit_purchase_fk
    foreign key (related_credit_purchase_id) references credit_purchases(id);

create index if not exists credit_purchases_business_created_idx
    on credit_purchases(business_id, created_at desc);

create index if not exists credit_purchases_status_created_idx
    on credit_purchases(status, created_at desc);

create unique index if not exists credit_purchases_business_idempotency_idx
    on credit_purchases(business_id, idempotency_key)
    where idempotency_key is not null;

create unique index if not exists credit_purchases_stripe_session_idx
    on credit_purchases(stripe_checkout_session_id)
    where stripe_checkout_session_id is not null;

create unique index if not exists credit_purchases_stripe_event_idx
    on credit_purchases(stripe_event_id)
    where stripe_event_id is not null;

create unique index if not exists credit_purchases_stripe_payment_intent_idx
    on credit_purchases(stripe_payment_intent_id)
    where stripe_payment_intent_id is not null;

create index if not exists credit_purchases_manual_reference_idx
    on credit_purchases(manual_payment_reference)
    where manual_payment_reference is not null;

create index if not exists credit_purchases_manual_tx_hash_idx
    on credit_purchases(manual_tx_hash)
    where manual_tx_hash is not null;

create index if not exists referral_codes_business_idx
    on referral_codes(business_id);

create index if not exists referral_codes_code_status_idx
    on referral_codes(code, status);

create unique index if not exists referral_events_referred_active_idx
    on referral_events(referred_business_id)
    where status in ('pending', 'approved', 'rewarded');

create index if not exists referral_events_referrer_created_idx
    on referral_events(referrer_business_id, created_at desc);

create index if not exists referral_events_status_created_idx
    on referral_events(status, created_at desc);

create index if not exists file_assets_credit_purchase_resource_idx
    on file_assets(resource_type, resource_id, created_at desc)
    where resource_type = 'credit_purchase';

create index if not exists credits_ledger_related_credit_purchase_idx
    on credits_ledger(related_credit_purchase_id)
    where related_credit_purchase_id is not null;
