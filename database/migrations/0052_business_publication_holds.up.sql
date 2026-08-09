create table business_publication_holds (
    id uuid primary key default gen_random_uuid(),
    business_id uuid not null references businesses(id),
    order_id uuid not null references orders(id),
    support_ticket_id uuid not null unique references support_tickets(id),
    status text not null default 'active' check (status in ('active', 'released')),
    reason_type text not null default 'structured_operation_report'
        check (reason_type = 'structured_operation_report'),
    created_at timestamptz not null default now(),
    released_at timestamptz null,
    released_by uuid null references users(id),
    release_reason text null,
    constraint business_publication_holds_release_state_check check (
        (
            status = 'active'
            and released_at is null
            and released_by is null
            and release_reason is null
        )
        or (
            status = 'released'
            and released_at is not null
            and released_by is not null
            and nullif(trim(release_reason), '') is not null
        )
    )
);

create index business_publication_holds_active_business_idx
    on business_publication_holds(business_id)
    where status = 'active';

create unique index business_publication_holds_active_order_uidx
    on business_publication_holds(order_id)
    where status = 'active';
