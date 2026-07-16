create table if not exists support_tickets (
    id uuid primary key default gen_random_uuid(),
    requester_user_id uuid not null references users(id),
    requester_role text not null,
    requester_surface text not null,
    business_id uuid null references businesses(id),
    order_id uuid null references orders(id),
    ad_id uuid null references ads(id),
    credit_purchase_id uuid null references credit_purchases(id),
    dispute_id uuid null references disputes(id),
    assigned_support_user_id uuid null references users(id),
    scope text not null,
    category text not null,
    status text not null,
    priority text not null default 'normal',
    subject text not null,
    last_message_at timestamptz null,
    escalated_at timestamptz null,
    resolved_at timestamptz null,
    closed_at timestamptz null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint support_tickets_requester_role_check check (requester_role in ('remitter', 'business_owner', 'admin', 'super_admin', 'support')),
    constraint support_tickets_requester_surface_check check (requester_surface in ('client_mini_app', 'business_mini_app', 'admin_web')),
    constraint support_tickets_scope_check check (scope in ('client_general', 'client_order', 'business_general', 'business_order', 'business_ad', 'business_credit', 'admin_internal')),
    constraint support_tickets_category_check check (category in ('technical_issue', 'account_access', 'order_help', 'payment_report_help', 'business_access', 'credits_help', 'suspicious_activity', 'other')),
    constraint support_tickets_status_check check (status in ('open', 'waiting_support', 'waiting_user', 'escalated', 'resolved', 'closed')),
    constraint support_tickets_priority_check check (priority in ('low', 'normal', 'high', 'urgent')),
    constraint support_tickets_scope_resource_check check (
        (scope = 'client_order' and order_id is not null and ad_id is null and credit_purchase_id is null)
        or (scope = 'business_order' and business_id is not null and order_id is not null and ad_id is null and credit_purchase_id is null)
        or (scope = 'business_ad' and business_id is not null and ad_id is not null and order_id is null and credit_purchase_id is null)
        or (scope = 'business_credit' and business_id is not null and credit_purchase_id is not null and order_id is null and ad_id is null)
        or (scope = 'business_general' and business_id is not null and order_id is null and ad_id is null and credit_purchase_id is null)
        or (scope in ('client_general', 'admin_internal') and order_id is null and ad_id is null and credit_purchase_id is null)
    )
);

create table if not exists support_messages (
    id uuid primary key default gen_random_uuid(),
    ticket_id uuid not null references support_tickets(id),
    sender_user_id uuid not null references users(id),
    sender_role text not null,
    body text not null,
    visibility text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    deleted_at timestamptz null,
    constraint support_messages_sender_role_check check (sender_role in ('remitter', 'business_owner', 'admin', 'super_admin', 'support')),
    constraint support_messages_visibility_check check (visibility in ('participants', 'support_internal', 'admin_internal')),
    constraint support_messages_body_check check (char_length(body) > 0 and char_length(body) <= 2000)
);

create table if not exists support_ticket_events (
    id uuid primary key default gen_random_uuid(),
    ticket_id uuid not null references support_tickets(id),
    actor_user_id uuid not null references users(id),
    actor_role text not null,
    event_type text not null,
    from_status text null,
    to_status text null,
    reason text null,
    metadata_json jsonb not null default '{}',
    created_at timestamptz not null default now(),
    constraint support_ticket_events_actor_role_check check (actor_role in ('remitter', 'business_owner', 'admin', 'super_admin', 'support')),
    constraint support_ticket_events_type_check check (
        event_type in (
            'support_ticket_created',
            'support_message_created',
            'support_attachment_uploaded',
            'support_attachment_viewed',
            'support_ticket_assigned',
            'support_ticket_escalated',
            'support_ticket_linked_to_dispute',
            'support_ticket_resolved',
            'support_ticket_closed'
        )
    )
);

alter table file_assets drop constraint if exists file_assets_resource_type_check;
alter table file_assets drop constraint if exists file_assets_file_type_check;

alter table file_assets
    add constraint file_assets_resource_type_check check (
        resource_type in ('business', 'payment_report', 'message', 'credit_purchase', 'business_intake', 'support_ticket', 'support_message')
    );

alter table file_assets
    add constraint file_assets_file_type_check check (
        file_type in (
            'rif_document',
            'business_license',
            'owner_identity',
            'address_proof',
            'payment_evidence',
            'message_attachment',
            'credit_purchase_proof',
            'intake_document',
            'support_attachment'
        )
    );

create index if not exists support_tickets_requester_status_updated_idx
    on support_tickets(requester_user_id, status, updated_at desc);

create index if not exists support_tickets_business_status_updated_idx
    on support_tickets(business_id, status, updated_at desc)
    where business_id is not null;

create index if not exists support_tickets_order_created_idx
    on support_tickets(order_id, created_at desc)
    where order_id is not null;

create index if not exists support_tickets_ad_created_idx
    on support_tickets(ad_id, created_at desc)
    where ad_id is not null;

create index if not exists support_tickets_credit_purchase_created_idx
    on support_tickets(credit_purchase_id, created_at desc)
    where credit_purchase_id is not null;

create index if not exists support_tickets_assignee_status_updated_idx
    on support_tickets(assigned_support_user_id, status, updated_at desc)
    where assigned_support_user_id is not null;

create index if not exists support_tickets_queue_filters_idx
    on support_tickets(scope, category, status, priority, updated_at desc);

create index if not exists support_messages_ticket_created_idx
    on support_messages(ticket_id, created_at asc)
    where deleted_at is null;

create index if not exists support_ticket_events_ticket_created_idx
    on support_ticket_events(ticket_id, created_at asc);

create index if not exists file_assets_support_resource_idx
    on file_assets(resource_type, resource_id, created_at desc)
    where file_type = 'support_attachment';
