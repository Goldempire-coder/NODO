create table if not exists business_access_links (
    id uuid primary key default gen_random_uuid(),
    business_id uuid not null references businesses(id) on delete cascade,
    user_id uuid not null references users(id) on delete cascade,
    telegram_id_snapshot bigint not null,
    role_in_business text not null default 'owner',
    status text not null default 'active',
    linked_by_admin_id uuid not null references users(id),
    linked_at timestamptz not null default now(),
    suspended_at timestamptz,
    blocked_at timestamptz,
    revoked_at timestamptz,
    reason text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint business_access_links_role_check check (role_in_business in ('owner', 'operator')),
    constraint business_access_links_status_check check (status in ('active', 'suspended', 'revoked', 'blocked')),
    constraint business_access_links_reason_check check (
        status = 'active'
        or (reason is not null and length(trim(reason)) > 0)
    ),
    constraint business_access_links_timestamps_check check (
        (status <> 'suspended' or suspended_at is not null)
        and (status <> 'blocked' or blocked_at is not null)
        and (status <> 'revoked' or revoked_at is not null)
    )
);

create unique index if not exists business_access_links_active_business_user_idx
    on business_access_links (business_id, user_id, role_in_business)
    where status = 'active';

create unique index if not exists business_access_links_active_owner_idx
    on business_access_links (business_id)
    where role_in_business = 'owner' and status = 'active';

create index if not exists business_access_links_business_status_idx
    on business_access_links (business_id, status, created_at desc);

create index if not exists business_access_links_user_status_idx
    on business_access_links (user_id, status, created_at desc);

create index if not exists business_access_links_telegram_idx
    on business_access_links (telegram_id_snapshot, status);
