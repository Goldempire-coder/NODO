create table if not exists sessions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id),
    refresh_token_hash text not null unique,
    status text not null default 'active',
    access_token_jti text null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    expires_at timestamptz not null,
    revoked_at timestamptz null,
    last_used_at timestamptz null,
    ip_hash text null,
    user_agent text null,
    constraint sessions_status_check check (status in ('active', 'revoked', 'expired')),
    constraint sessions_revoked_at_check check (
        (status = 'revoked' and revoked_at is not null)
        or (status <> 'revoked')
    )
);

create unique index if not exists sessions_refresh_token_hash_idx
    on sessions(refresh_token_hash);

create index if not exists sessions_user_status_created_idx
    on sessions(user_id, status, created_at desc);

create index if not exists sessions_access_token_jti_idx
    on sessions(access_token_jti)
    where access_token_jti is not null;

create index if not exists sessions_expires_at_idx
    on sessions(expires_at);
