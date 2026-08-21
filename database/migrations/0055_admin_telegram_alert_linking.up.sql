alter table users
    add column if not exists admin_alert_telegram_id bigint;

create unique index if not exists users_admin_alert_telegram_id_unique
    on users (admin_alert_telegram_id)
    where admin_alert_telegram_id is not null;

create table if not exists admin_telegram_link_codes (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    code_hash text not null unique,
    status text not null default 'pending'
        check (status in ('pending', 'used', 'expired')),
    expires_at timestamptz not null,
    used_at timestamptz,
    telegram_hash text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists admin_telegram_link_codes_user_status_idx
    on admin_telegram_link_codes (user_id, status, expires_at desc);
