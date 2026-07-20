create table if not exists admin_notifications (
    id uuid primary key default gen_random_uuid(),
    notification_type text not null,
    priority text not null,
    status text not null default 'unread',
    source_surface text,
    resource_type text not null,
    resource_id uuid,
    business_id uuid,
    actor_user_id uuid,
    title text not null,
    summary text not null,
    action_route text,
    dedupe_key text not null unique,
    metadata_json jsonb not null default '{}'::jsonb,
    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),
    read_at timestamptz,
    read_by_user_id uuid,
    dismissed_at timestamptz,
    dismissed_by_user_id uuid,
    resolved_at timestamptz,
    resolved_by_user_id uuid,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint admin_notifications_priority_check check (priority in ('info', 'attention', 'high', 'critical')),
    constraint admin_notifications_status_check check (status in ('unread', 'read', 'dismissed', 'resolved')),
    constraint admin_notifications_title_nonempty check (nullif(trim(title), '') is not null),
    constraint admin_notifications_summary_nonempty check (nullif(trim(summary), '') is not null),
    constraint admin_notifications_dedupe_nonempty check (nullif(trim(dedupe_key), '') is not null)
);

create index if not exists admin_notifications_status_priority_last_seen_idx
    on admin_notifications (status, priority, last_seen_at desc);

create index if not exists admin_notifications_resource_idx
    on admin_notifications (resource_type, resource_id);

create index if not exists admin_notifications_business_last_seen_idx
    on admin_notifications (business_id, last_seen_at desc);
