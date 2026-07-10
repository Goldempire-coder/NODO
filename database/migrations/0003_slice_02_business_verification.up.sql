create table if not exists businesses (
    id uuid primary key default gen_random_uuid(),
    owner_user_id uuid not null references users(id),
    business_name text not null,
    rif text null,
    address text null,
    phone text null,
    country text not null default 'VE',
    verification_status text not null default 'pending',
    trust_level text not null default 'new',
    risk_level text not null default 'normal',
    max_order_amount_usd numeric(12,2) not null default 100.00,
    daily_limit_usd numeric(12,2) not null default 300.00,
    active_order_limit integer not null default 1,
    rating_avg numeric(4,2) null,
    completed_orders_count integer not null default 0,
    disputes_count integer not null default 0,
    evasion_reports_count integer not null default 0,
    referral_code text null,
    referral_credits_earned integer not null default 0,
    founder_status text null,
    founder_started_at timestamptz null,
    founder_expires_at timestamptz null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    approved_at timestamptz null,
    constraint businesses_verification_status_check check (verification_status in ('pending', 'approved', 'rejected', 'suspended', 'blocked')),
    constraint businesses_trust_level_check check (trust_level in ('new', 'basic', 'plus', 'pro', 'premium')),
    constraint businesses_risk_level_check check (risk_level in ('normal', 'watch', 'under_review', 'restricted', 'high_risk')),
    constraint businesses_approved_at_check check (
        (verification_status = 'approved' and approved_at is not null)
        or (verification_status <> 'approved' and approved_at is null)
    ),
    constraint businesses_limits_check check (
        max_order_amount_usd >= 0
        and daily_limit_usd >= 0
        and active_order_limit >= 0
        and completed_orders_count >= 0
        and disputes_count >= 0
        and evasion_reports_count >= 0
        and referral_credits_earned >= 0
    )
);

create unique index if not exists businesses_one_active_per_owner_idx
    on businesses(owner_user_id)
    where verification_status <> 'blocked';

create index if not exists businesses_owner_user_id_idx
    on businesses(owner_user_id);

create index if not exists businesses_verification_status_created_idx
    on businesses(verification_status, created_at desc);

create index if not exists businesses_verification_status_risk_level_idx
    on businesses(verification_status, risk_level);

create index if not exists businesses_business_name_idx
    on businesses(business_name);

create table if not exists business_verification_submissions (
    id uuid primary key default gen_random_uuid(),
    business_id uuid not null references businesses(id),
    submitted_by_user_id uuid not null references users(id),
    status text not null default 'pending',
    submitted_data_json jsonb not null,
    admin_reviewed_by_user_id uuid null references users(id),
    admin_reason text null,
    submitted_at timestamptz not null default now(),
    reviewed_at timestamptz null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint business_verification_submissions_status_check check (status in ('pending', 'approved', 'rejected')),
    constraint business_verification_submissions_review_check check (
        (status = 'pending' and reviewed_at is null and admin_reviewed_by_user_id is null)
        or (status in ('approved', 'rejected') and reviewed_at is not null and admin_reviewed_by_user_id is not null)
    ),
    constraint business_verification_submissions_reason_check check (
        status <> 'rejected'
        or (admin_reason is not null and length(trim(admin_reason)) > 0)
    )
);

create unique index if not exists business_verification_submissions_one_pending_idx
    on business_verification_submissions(business_id)
    where status = 'pending';

create index if not exists business_verification_submissions_business_status_created_idx
    on business_verification_submissions(business_id, status, created_at desc);

create index if not exists business_verification_submissions_status_submitted_idx
    on business_verification_submissions(status, submitted_at desc);

create index if not exists business_verification_submissions_admin_reviewed_idx
    on business_verification_submissions(admin_reviewed_by_user_id, reviewed_at desc)
    where admin_reviewed_by_user_id is not null;

create table if not exists business_payment_methods (
    id uuid primary key default gen_random_uuid(),
    business_id uuid not null references businesses(id),
    method_type text not null,
    network text null,
    account_value text not null,
    account_masked text not null,
    holder_name text not null,
    verified_status text not null default 'pending',
    active boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint business_payment_methods_method_type_check check (method_type in ('zelle', 'usdt_trc20')),
    constraint business_payment_methods_network_check check (
        (method_type = 'zelle' and network is null)
        or (method_type = 'usdt_trc20' and network = 'trc20')
    ),
    constraint business_payment_methods_verified_status_check check (verified_status in ('pending', 'approved', 'rejected'))
);

create index if not exists business_payment_methods_business_active_idx
    on business_payment_methods(business_id, active);

create index if not exists business_payment_methods_business_method_network_idx
    on business_payment_methods(business_id, method_type, network);

create table if not exists file_assets (
    id uuid primary key default gen_random_uuid(),
    owner_user_id uuid not null references users(id),
    resource_type text not null,
    resource_id uuid not null,
    file_type text not null,
    storage_path text not null,
    mime_type text not null,
    size_bytes integer not null,
    created_at timestamptz not null default now(),
    deleted_at timestamptz null,
    constraint file_assets_resource_type_check check (resource_type = 'business'),
    constraint file_assets_file_type_check check (file_type in ('rif_document', 'business_license', 'owner_identity', 'address_proof')),
    constraint file_assets_mime_type_check check (mime_type in ('image/jpeg', 'image/png', 'image/webp', 'application/pdf')),
    constraint file_assets_size_check check (size_bytes > 0 and size_bytes <= 5242880)
);

create index if not exists file_assets_resource_created_idx
    on file_assets(resource_type, resource_id, created_at desc);

create index if not exists file_assets_owner_created_idx
    on file_assets(owner_user_id, created_at desc);
