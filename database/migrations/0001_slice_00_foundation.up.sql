create extension if not exists pgcrypto;

create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    telegram_id bigint null,
    username text null,
    first_name text null,
    last_name text null,
    phone text null,
    role text not null default 'remitter',
    status text not null default 'active',
    trust_level text null,
    orders_created_count integer not null default 0,
    orders_completed_count integer not null default 0,
    orders_expired_count integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    last_seen_at timestamptz null,
    constraint users_role_check check (role in ('remitter', 'business_owner', 'admin', 'support', 'super_admin')),
    constraint users_status_check check (status in ('active', 'restricted', 'blocked', 'dormant')),
    constraint users_order_counts_non_negative_check check (
        orders_created_count >= 0 and orders_completed_count >= 0 and orders_expired_count >= 0
    )
);

create unique index if not exists users_telegram_id_unique_idx on users (telegram_id) where telegram_id is not null;
create index if not exists users_status_created_at_idx on users (status, created_at desc);
create index if not exists users_role_status_idx on users (role, status);

create table if not exists job_runs (
    id uuid primary key default gen_random_uuid(),
    job_type text not null,
    status text not null,
    lock_key text null,
    attempts integer not null default 0,
    started_at timestamptz null,
    finished_at timestamptz null,
    error_code text null,
    error_message_safe text null,
    metadata_json jsonb null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint job_runs_attempts_non_negative_check check (attempts >= 0)
);

create index if not exists job_runs_job_type_status_created_at_idx on job_runs (job_type, status, created_at desc);
create index if not exists job_runs_lock_key_partial_idx on job_runs (lock_key) where lock_key is not null;

create table if not exists audit_logs (
    id uuid primary key default gen_random_uuid(),
    actor_user_id uuid null references users(id),
    actor_role text null,
    event_type text not null,
    resource_type text not null,
    resource_id uuid null,
    old_value_json jsonb null,
    new_value_json jsonb null,
    reason text null,
    request_id text not null,
    job_id uuid null references job_runs(id),
    ip_hash text null,
    user_agent text null,
    metadata_json jsonb null,
    created_at timestamptz not null default now(),
    constraint audit_logs_actor_role_check check (
        actor_role is null or actor_role in ('remitter', 'business_owner', 'admin', 'support', 'super_admin')
    )
);

create index if not exists audit_logs_resource_created_at_idx on audit_logs (resource_type, resource_id, created_at desc);
create index if not exists audit_logs_actor_user_created_at_idx on audit_logs (actor_user_id, created_at desc);
create index if not exists audit_logs_event_type_created_at_idx on audit_logs (event_type, created_at desc);
create index if not exists audit_logs_created_at_idx on audit_logs (created_at desc);

create or replace function prevent_audit_logs_mutation()
returns trigger as $$
begin
    raise exception 'audit_logs are append-only';
end;
$$ language plpgsql;

drop trigger if exists audit_logs_prevent_update on audit_logs;
create trigger audit_logs_prevent_update
before update on audit_logs
for each row execute function prevent_audit_logs_mutation();

drop trigger if exists audit_logs_prevent_delete on audit_logs;
create trigger audit_logs_prevent_delete
before delete on audit_logs
for each row execute function prevent_audit_logs_mutation();

create table if not exists app_metadata (
    id uuid primary key default gen_random_uuid(),
    key text unique not null,
    value_json jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists app_metadata_key_unique_idx on app_metadata (key);
