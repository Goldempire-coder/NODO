create table if not exists frontend_observability_events (
    id uuid primary key default gen_random_uuid(),
    event_id text not null,
    event_type text not null,
    severity text not null,
    surface text not null,
    session_id_hash text not null,
    actor_user_hash text not null,
    actor_role text not null,
    request_id text,
    correlation_id text,
    operation_id text,
    screen text,
    previous_screen text,
    action text,
    method text,
    route_template text,
    status_code integer,
    duration_ms numeric(12, 2),
    error_code text,
    resource_refs_json jsonb not null default '{}'::jsonb,
    metadata_json jsonb not null default '{}'::jsonb,
    occurred_at timestamptz not null,
    created_at timestamptz not null default now(),
    constraint frontend_observability_events_severity_check check (severity in ('trace', 'debug', 'info', 'warn', 'error')),
    constraint frontend_observability_events_surface_check check (surface in ('client_mini_app', 'business_mini_app', 'admin_web'))
);

create index if not exists frontend_observability_events_created_at_idx on frontend_observability_events (created_at desc);
create index if not exists frontend_observability_events_surface_created_at_idx on frontend_observability_events (surface, created_at desc);
create index if not exists frontend_observability_events_event_type_created_at_idx on frontend_observability_events (event_type, created_at desc);
create index if not exists frontend_observability_events_screen_created_at_idx on frontend_observability_events (screen, created_at desc);
create index if not exists frontend_observability_events_action_created_at_idx on frontend_observability_events (action, created_at desc);
