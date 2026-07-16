create table if not exists staff_profiles (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id),
    staff_role text not null check (staff_role in ('support_agent', 'support_lead', 'operations_readonly', 'admin', 'super_admin')),
    status text not null check (status in ('active', 'suspended', 'revoked')),
    display_name text null,
    created_by_super_admin_id uuid not null references users(id),
    activated_by_super_admin_id uuid null references users(id),
    suspended_by_super_admin_id uuid null references users(id),
    revoked_by_super_admin_id uuid null references users(id),
    activated_at timestamptz null,
    suspended_at timestamptz null,
    revoked_at timestamptz null,
    reason text null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists staff_permissions (
    id uuid primary key default gen_random_uuid(),
    staff_profile_id uuid not null references staff_profiles(id),
    permission text not null check (permission in (
        'view_support_queue',
        'view_assigned_support_tickets',
        'reply_support_ticket',
        'assign_support_ticket',
        'escalate_support_ticket',
        'resolve_support_ticket',
        'close_support_ticket',
        'view_support_attachment',
        'view_users_masked',
        'view_businesses_masked',
        'view_orders_masked',
        'view_audit_limited',
        'view_metrics_limited'
    )),
    scope text not null check (scope in ('assigned_only', 'queue_scope', 'category_scope', 'global_readonly')),
    scope_value text null,
    status text not null check (status in ('active', 'revoked')),
    granted_by_super_admin_id uuid not null references users(id),
    revoked_by_super_admin_id uuid null references users(id),
    revoked_at timestamptz null,
    reason text not null check (length(trim(reason)) > 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists staff_invites (
    id uuid primary key default gen_random_uuid(),
    target_user_id uuid null references users(id),
    target_telegram_id bigint null,
    target_username text null,
    invite_code_hash text null,
    staff_role text not null check (staff_role in ('support_agent', 'support_lead', 'operations_readonly', 'admin', 'super_admin')),
    status text not null check (status in ('pending', 'accepted', 'expired', 'revoked')),
    expires_at timestamptz not null,
    created_by_super_admin_id uuid not null references users(id),
    accepted_by_user_id uuid null references users(id),
    accepted_at timestamptz null,
    revoked_at timestamptz null,
    expired_at timestamptz null,
    reason text not null check (length(trim(reason)) > 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint staff_invites_target_required check (
        target_user_id is not null or target_telegram_id is not null or nullif(trim(target_username), '') is not null
    )
);

create index if not exists staff_profiles_user_status_idx on staff_profiles (user_id, status);
create index if not exists staff_profiles_role_status_created_idx on staff_profiles (staff_role, status, created_at desc);
create unique index if not exists staff_profiles_one_active_per_user_idx on staff_profiles (user_id) where status = 'active';

create index if not exists staff_permissions_profile_status_idx on staff_permissions (staff_profile_id, status);
create unique index if not exists staff_permissions_active_unique_idx
    on staff_permissions (staff_profile_id, permission, scope, coalesce(scope_value, ''))
    where status = 'active';

create index if not exists staff_invites_status_expires_idx on staff_invites (status, expires_at);
create index if not exists staff_invites_target_user_status_idx on staff_invites (target_user_id, status) where target_user_id is not null;
create index if not exists staff_invites_target_telegram_status_idx on staff_invites (target_telegram_id, status) where target_telegram_id is not null;
create index if not exists staff_invites_target_username_status_idx on staff_invites (lower(target_username), status) where target_username is not null;
