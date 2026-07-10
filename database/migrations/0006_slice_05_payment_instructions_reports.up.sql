alter table file_assets drop constraint if exists file_assets_resource_type_check;
alter table file_assets drop constraint if exists file_assets_file_type_check;

alter table file_assets
    add constraint file_assets_resource_type_check check (resource_type in ('business', 'payment_report'));

alter table file_assets
    add constraint file_assets_file_type_check check (
        file_type in ('rif_document', 'business_license', 'owner_identity', 'address_proof', 'payment_evidence')
    );

create table if not exists payment_reports (
    id uuid primary key default gen_random_uuid(),
    order_id uuid not null references orders(id),
    reported_by_user_id uuid not null references users(id),
    status text not null default 'submitted',
    idempotency_key text null,
    payment_type text not null,
    payment_reference text null,
    payment_sender_name text null,
    payment_sender_account_masked text null,
    tx_hash text null,
    network text null,
    payment_amount numeric(12,2) not null,
    proof_file_id uuid null references file_assets(id),
    report_payload_hash text null,
    admin_notes text null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint payment_reports_status_check check (status in ('submitted', 'corrected', 'rejected', 'accepted')),
    constraint payment_reports_type_check check (payment_type in ('zelle', 'usdt_trc20')),
    constraint payment_reports_amount_check check (payment_amount > 0),
    constraint payment_reports_zelle_required_check check (
        payment_type <> 'zelle'
        or (payment_reference is not null and payment_sender_name is not null and proof_file_id is not null)
    ),
    constraint payment_reports_usdt_required_check check (
        payment_type <> 'usdt_trc20'
        or (tx_hash is not null and network = 'TRC20')
    )
);

create index if not exists orders_business_response_warning_idx
    on orders(status, business_response_warning_at)
    where status = 'payment_reported';

create index if not exists orders_business_response_deadline_idx
    on orders(status, business_response_deadline_at)
    where status = 'payment_reported';

create index if not exists payment_reports_order_created_idx
    on payment_reports(order_id, created_at desc);

create index if not exists payment_reports_status_created_idx
    on payment_reports(status, created_at desc);

create index if not exists payment_reports_reported_by_created_idx
    on payment_reports(reported_by_user_id, created_at desc);

create unique index if not exists payment_reports_reported_by_idempotency_idx
    on payment_reports(reported_by_user_id, idempotency_key)
    where idempotency_key is not null;

create unique index if not exists payment_reports_order_submitted_idx
    on payment_reports(order_id)
    where status = 'submitted';
