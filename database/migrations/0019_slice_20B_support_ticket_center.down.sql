drop index if exists file_assets_support_resource_idx;
drop index if exists support_ticket_events_ticket_created_idx;
drop index if exists support_messages_ticket_created_idx;
drop index if exists support_tickets_queue_filters_idx;
drop index if exists support_tickets_assignee_status_updated_idx;
drop index if exists support_tickets_credit_purchase_created_idx;
drop index if exists support_tickets_ad_created_idx;
drop index if exists support_tickets_order_created_idx;
drop index if exists support_tickets_business_status_updated_idx;
drop index if exists support_tickets_requester_status_updated_idx;

drop table if exists support_ticket_events;
drop table if exists support_messages;
drop table if exists support_tickets;

alter table file_assets drop constraint if exists file_assets_resource_type_check;
alter table file_assets drop constraint if exists file_assets_file_type_check;

alter table file_assets
    add constraint file_assets_resource_type_check check (
        resource_type in ('business', 'payment_report', 'message', 'credit_purchase', 'business_intake')
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
            'intake_document'
        )
    );
