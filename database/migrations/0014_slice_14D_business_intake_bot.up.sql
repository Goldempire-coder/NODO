create table if not exists business_intake_requests (
    id uuid primary key default gen_random_uuid(),
    telegram_user_id bigint not null,
    telegram_chat_id bigint not null,
    contact_phone text null,
    business_phone text null,
    referral_code text null,
    status text not null default 'draft',
    last_step text not null default 'start',
    last_update_id bigint null,
    business_name text null,
    responsible_name text null,
    city text null,
    operation text null,
    banks_json jsonb not null default '[]'::jsonb,
    methods_json jsonb not null default '[]'::jsonb,
    min_amount_usd numeric(12,2) null,
    max_amount_usd numeric(12,2) null,
    schedule_text text null,
    references_json jsonb not null default '[]'::jsonb,
    submitted_at timestamptz null,
    reviewed_by_admin_id uuid null references users(id),
    reviewed_at timestamptz null,
    admin_reason text null,
    created_business_id uuid null references businesses(id),
    linked_telegram_user_id bigint null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    archived_at timestamptz null,
    constraint business_intake_requests_status_check check (status in ('draft', 'submitted', 'accepted', 'rejected')),
    constraint business_intake_requests_operation_check check (operation is null or operation in ('buy_usd', 'sell_usd', 'both')),
    constraint business_intake_requests_amounts_check check (
        (min_amount_usd is null or min_amount_usd > 0)
        and (max_amount_usd is null or min_amount_usd is null or max_amount_usd >= min_amount_usd)
    ),
    constraint business_intake_requests_review_check check (
        status in ('draft', 'submitted')
        or (reviewed_at is not null and reviewed_by_admin_id is not null and admin_reason is not null and length(trim(admin_reason)) > 0)
    )
);

alter table file_assets add column if not exists metadata_json jsonb null;

alter table file_assets drop constraint if exists file_assets_resource_type_check;
alter table file_assets drop constraint if exists file_assets_file_type_check;

alter table file_assets
    add constraint file_assets_resource_type_check check (
        resource_type in ('business', 'payment_report', 'message', 'credit_purchase', 'business_intake')
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
            'credit_purchase_proof',
            'intake_document'
        )
    );

create index if not exists business_intake_requests_status_submitted_idx
    on business_intake_requests(status, submitted_at desc);

create index if not exists business_intake_requests_telegram_user_created_idx
    on business_intake_requests(telegram_user_id, created_at desc);

create index if not exists business_intake_requests_telegram_chat_created_idx
    on business_intake_requests(telegram_chat_id, created_at desc);

create unique index if not exists business_intake_requests_chat_update_unique_idx
    on business_intake_requests(telegram_chat_id, last_update_id)
    where last_update_id is not null;

create index if not exists business_intake_requests_contact_phone_created_idx
    on business_intake_requests(contact_phone, created_at desc)
    where contact_phone is not null;

create index if not exists business_intake_requests_created_business_idx
    on business_intake_requests(created_business_id)
    where created_business_id is not null;

create index if not exists file_assets_business_intake_resource_idx
    on file_assets(resource_type, resource_id, created_at desc)
    where resource_type = 'business_intake';
