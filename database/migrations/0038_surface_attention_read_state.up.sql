create table if not exists surface_attention_read_state (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    surface text not null check (surface in ('business_mini_app', 'client_mini_app')),
    resource_kind text not null check (resource_kind in ('order', 'support')),
    resource_id uuid not null,
    signature text not null check (char_length(signature) between 16 and 96),
    acknowledged_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (user_id, surface, resource_kind, resource_id)
);

create index if not exists idx_surface_attention_read_state_user_surface
on surface_attention_read_state (user_id, surface, updated_at desc);
