create table if not exists platform_emergency_mode (
    id text primary key default 'platform' check (id = 'platform'),
    enabled boolean not null default false,
    reason text,
    message text,
    activated_by_user_id uuid references users(id),
    activated_at timestamptz,
    deactivated_by_user_id uuid references users(id),
    deactivated_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

insert into platform_emergency_mode (id, enabled, created_at, updated_at)
values ('platform', false, now(), now())
on conflict (id) do nothing;
