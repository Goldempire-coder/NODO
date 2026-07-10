alter table file_assets drop constraint if exists file_assets_resource_type_check;
alter table file_assets drop constraint if exists file_assets_file_type_check;

alter table file_assets
    add constraint file_assets_resource_type_check check (resource_type in ('business', 'payment_report', 'message'));

alter table file_assets
    add constraint file_assets_file_type_check check (
        file_type in (
            'rif_document',
            'business_license',
            'owner_identity',
            'address_proof',
            'payment_evidence',
            'message_attachment'
        )
    );

create table if not exists messages (
    id uuid primary key default gen_random_uuid(),
    order_id uuid not null references orders(id),
    sender_user_id uuid not null references users(id),
    sender_role text not null,
    body text null,
    visibility text not null default 'parties',
    status text not null default 'visible',
    idempotency_key text null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    deleted_at timestamptz null,
    constraint messages_sender_role_check check (sender_role in ('remitter', 'business_owner', 'admin', 'super_admin', 'support')),
    constraint messages_visibility_check check (visibility in ('parties', 'admin_only')),
    constraint messages_status_check check (status in ('visible', 'hidden', 'deleted')),
    constraint messages_body_length_check check (body is null or char_length(body) <= 2000)
);

create table if not exists message_attachments (
    id uuid primary key default gen_random_uuid(),
    message_id uuid null references messages(id),
    order_id uuid not null references orders(id),
    file_asset_id uuid not null references file_assets(id),
    uploaded_by_user_id uuid not null references users(id),
    file_type text not null default 'message_attachment',
    mime_type text not null,
    size_bytes integer not null,
    status text not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    deleted_at timestamptz null,
    constraint message_attachments_file_type_check check (file_type = 'message_attachment'),
    constraint message_attachments_mime_type_check check (mime_type in ('image/jpeg', 'image/png', 'image/webp', 'application/pdf')),
    constraint message_attachments_size_check check (size_bytes > 0 and size_bytes <= 5242880),
    constraint message_attachments_status_check check (status in ('active', 'deleted'))
);

create table if not exists disputes (
    id uuid primary key default gen_random_uuid(),
    order_id uuid not null references orders(id),
    opened_by_user_id uuid not null references users(id),
    opened_by_role text not null,
    previous_order_status text not null,
    reason text not null,
    description text null,
    status text not null default 'open',
    resolution_type text null,
    resolution_reason text null,
    resolved_by_admin_id uuid null references users(id),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    resolved_at timestamptz null,
    cancelled_at timestamptz null,
    constraint disputes_opened_by_role_check check (opened_by_role in ('remitter', 'business_owner', 'admin', 'super_admin', 'support')),
    constraint disputes_previous_order_status_check check (previous_order_status in ('payment_reported', 'payment_rejected', 'payment_confirmed', 'delivered')),
    constraint disputes_status_check check (status in ('open', 'in_review', 'resolved', 'cancelled')),
    constraint disputes_reason_check check (
        reason in (
            'business_no_payment_confirmation',
            'business_confirmed_payment_but_not_delivered',
            'payment_mobile_not_received',
            'amount_incorrect',
            'wrong_receiver_data',
            'other'
        )
    ),
    constraint disputes_resolution_type_future_check check (
        resolution_type is null
        or resolution_type in ('future_admin_resolution')
    )
);

create table if not exists dispute_events (
    id uuid primary key default gen_random_uuid(),
    dispute_id uuid not null references disputes(id),
    order_id uuid not null references orders(id),
    actor_user_id uuid not null references users(id),
    actor_role text not null,
    event_type text not null,
    old_status text null,
    new_status text null,
    reason text null,
    metadata_json jsonb null,
    created_at timestamptz not null default now(),
    constraint dispute_events_actor_role_check check (actor_role in ('remitter', 'business_owner', 'admin', 'super_admin', 'support')),
    constraint dispute_events_event_type_check check (event_type in ('dispute_opened', 'dispute_status_changed', 'dispute_note_added', 'dispute_resolved', 'dispute_cancelled', 'dispute_message_created')),
    constraint dispute_events_status_check check (
        (old_status is null or old_status in ('open', 'in_review', 'resolved', 'cancelled'))
        and (new_status is null or new_status in ('open', 'in_review', 'resolved', 'cancelled'))
    )
);

create index if not exists messages_order_created_idx
    on messages(order_id, created_at asc)
    where deleted_at is null;

create unique index if not exists messages_sender_idempotency_idx
    on messages(sender_user_id, idempotency_key)
    where idempotency_key is not null and deleted_at is null;

create index if not exists message_attachments_order_created_idx
    on message_attachments(order_id, created_at desc)
    where deleted_at is null;

create index if not exists message_attachments_message_created_idx
    on message_attachments(message_id, created_at asc)
    where deleted_at is null;

create index if not exists file_assets_message_resource_idx
    on file_assets(resource_type, resource_id, created_at desc)
    where resource_type = 'message';

create unique index if not exists disputes_open_order_idx
    on disputes(order_id)
    where status in ('open', 'in_review');

create index if not exists disputes_status_created_idx
    on disputes(status, created_at desc);

create index if not exists disputes_order_created_idx
    on disputes(order_id, created_at desc);

create index if not exists dispute_events_dispute_created_idx
    on dispute_events(dispute_id, created_at asc);

create index if not exists dispute_events_order_created_idx
    on dispute_events(order_id, created_at asc);
