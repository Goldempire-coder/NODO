create table if not exists business_capacity (
    business_id uuid primary key references businesses(id) on delete cascade,
    declared_available_capacity_usd numeric(12,2) not null default 0.00,
    updated_by_user_id uuid null references users(id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint business_capacity_amount_check check (
        declared_available_capacity_usd >= 0
    )
);

insert into business_capacity (
    business_id,
    declared_available_capacity_usd,
    created_at,
    updated_at
)
select id, 0.00, now(), now()
from businesses
on conflict (business_id) do nothing;

create table if not exists business_capacity_reservations (
    id uuid primary key default gen_random_uuid(),
    order_id uuid not null references orders(id) on delete restrict,
    business_id uuid not null references businesses(id) on delete restrict,
    amount_usd numeric(12,2) not null,
    status text not null default 'reserved',
    reason text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    released_at timestamptz null,
    consumed_at timestamptz null,
    constraint business_capacity_reservations_order_id_key unique (order_id),
    constraint business_capacity_reservations_amount_check check (amount_usd > 0),
    constraint business_capacity_reservations_status_check check (
        status in ('reserved', 'released', 'consumed')
    ),
    constraint business_capacity_reservations_terminal_check check (
        (status = 'reserved' and released_at is null and consumed_at is null)
        or (status = 'released' and released_at is not null and consumed_at is null)
        or (status = 'consumed' and consumed_at is not null and released_at is null)
    )
);

create index if not exists business_capacity_reservations_active_idx
    on business_capacity_reservations (business_id, created_at, order_id)
    where status = 'reserved';

create index if not exists business_capacity_reservations_daily_idx
    on business_capacity_reservations (business_id, created_at);
