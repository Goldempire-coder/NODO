create table if not exists orders (
    id uuid primary key default gen_random_uuid(),
    public_order_code text unique not null,
    ad_id uuid not null references ads(id),
    business_id uuid not null references businesses(id),
    remitter_user_id uuid not null references users(id),
    status text not null,
    idempotency_key text null,
    completion_reason text null,
    cancel_reason text null,
    dispute_reason text null,
    amount_usd numeric(12,2) not null,
    rate_snapshot numeric(18,6) not null,
    amount_bs_calculated numeric(18,2) not null,
    business_name_snapshot text not null,
    payment_method_snapshot text not null,
    delivery_method_snapshot text not null,
    min_amount_snapshot numeric(12,2) not null,
    max_amount_snapshot numeric(12,2) not null,
    payment_instructions_snapshot jsonb not null,
    receiver_data_json jsonb not null,
    payment_data_revealed_at timestamptz null,
    payment_data_revealed_by uuid null references users(id),
    payment_report_deadline_at timestamptz not null,
    payment_report_extension_used_at timestamptz null,
    extension_used boolean not null default false,
    expires_at timestamptz not null,
    business_response_warning_at timestamptz null,
    business_response_deadline_at timestamptz null,
    delivery_warning_at timestamptz null,
    delivery_deadline_at timestamptz null,
    auto_complete_warning_12h_at timestamptz null,
    auto_complete_warning_23h_at timestamptz null,
    auto_complete_at timestamptz null,
    paid_reported_at timestamptz null,
    payment_confirmed_at timestamptz null,
    delivered_at timestamptz null,
    completed_at timestamptz null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint orders_status_check check (status in ('waiting_payment', 'payment_reported', 'payment_confirmed', 'delivered', 'completed', 'cancelled', 'disputed')),
    constraint orders_cancel_reason_check check (
        cancel_reason is null
        or cancel_reason in ('remitter_cancelled_before_payment', 'payment_not_reported_in_time')
    ),
    constraint orders_cancelled_reason_required_check check (
        status <> 'cancelled'
        or cancel_reason is not null
    ),
    constraint orders_amount_check check (amount_usd >= 20),
    constraint orders_rate_check check (rate_snapshot > 0),
    constraint orders_amount_bs_check check (amount_bs_calculated > 0),
    constraint orders_payment_method_check check (payment_method_snapshot in ('zelle', 'usdt_trc20')),
    constraint orders_delivery_method_check check (delivery_method_snapshot in ('pago_movil_ve')),
    constraint orders_snapshot_range_check check (min_amount_snapshot >= 20 and max_amount_snapshot >= min_amount_snapshot),
    constraint orders_waiting_deadline_check check (
        status <> 'waiting_payment'
        or (payment_report_deadline_at is not null and expires_at is not null)
    )
);

create table if not exists order_state_events (
    id uuid primary key default gen_random_uuid(),
    order_id uuid not null references orders(id),
    from_status text null,
    to_status text not null,
    event_type text not null,
    actor_user_id uuid null references users(id),
    actor_role text null,
    reason text null,
    request_id text not null,
    metadata_json jsonb null,
    created_at timestamptz not null default now(),
    constraint order_state_events_to_status_check check (to_status in ('waiting_payment', 'payment_reported', 'payment_confirmed', 'delivered', 'completed', 'cancelled', 'disputed')),
    constraint order_state_events_from_status_check check (
        from_status is null
        or from_status in ('waiting_payment', 'payment_reported', 'payment_confirmed', 'delivered', 'completed', 'cancelled', 'disputed')
    )
);

alter table credits_ledger
    add constraint credits_ledger_related_order_fk
    foreign key (related_order_id) references orders(id);

create unique index if not exists orders_public_order_code_idx
    on orders(public_order_code);

create unique index if not exists orders_remitter_idempotency_idx
    on orders(remitter_user_id, idempotency_key)
    where idempotency_key is not null;

create index if not exists orders_remitter_created_idx
    on orders(remitter_user_id, created_at desc);

create index if not exists orders_business_created_idx
    on orders(business_id, created_at desc);

create index if not exists orders_status_created_idx
    on orders(status, created_at desc);

create index if not exists orders_business_status_created_idx
    on orders(business_id, status, created_at desc);

create index if not exists orders_remitter_status_created_idx
    on orders(remitter_user_id, status, created_at desc);

create index if not exists orders_ad_idx
    on orders(ad_id);

create index if not exists orders_waiting_deadline_idx
    on orders(payment_report_deadline_at)
    where status = 'waiting_payment';

create index if not exists order_state_events_order_created_idx
    on order_state_events(order_id, created_at desc);

create index if not exists order_state_events_type_created_idx
    on order_state_events(event_type, created_at desc);
