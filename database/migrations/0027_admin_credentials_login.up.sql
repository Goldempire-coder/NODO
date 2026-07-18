create table if not exists admin_credentials (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id),
    username text not null,
    username_normalized text not null,
    password_hash text not null,
    status text not null default 'active',
    failed_attempts integer not null default 0,
    locked_until timestamptz null,
    last_login_at timestamptz null,
    password_changed_at timestamptz null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint admin_credentials_status_check check (status in ('active', 'disabled')),
    constraint admin_credentials_failed_attempts_check check (failed_attempts >= 0),
    constraint admin_credentials_hash_check check (password_hash like 'pbkdf2_sha256$%')
);

create unique index if not exists admin_credentials_username_normalized_unique_idx
    on admin_credentials (username_normalized);

create unique index if not exists admin_credentials_user_id_unique_idx
    on admin_credentials (user_id);

create index if not exists admin_credentials_status_updated_at_idx
    on admin_credentials (status, updated_at desc);
