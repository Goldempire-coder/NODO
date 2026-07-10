drop index if exists dispute_events_order_created_idx;
drop index if exists dispute_events_dispute_created_idx;
drop index if exists disputes_order_created_idx;
drop index if exists disputes_status_created_idx;
drop index if exists disputes_open_order_idx;
drop index if exists file_assets_message_resource_idx;
drop index if exists message_attachments_message_created_idx;
drop index if exists message_attachments_order_created_idx;
drop index if exists messages_sender_idempotency_idx;
drop index if exists messages_order_created_idx;

drop table if exists dispute_events;
drop table if exists disputes;
drop table if exists message_attachments;
drop table if exists messages;

alter table file_assets drop constraint if exists file_assets_file_type_check;
alter table file_assets drop constraint if exists file_assets_resource_type_check;

alter table file_assets
    add constraint file_assets_resource_type_check check (resource_type in ('business', 'payment_report'));

alter table file_assets
    add constraint file_assets_file_type_check check (
        file_type in (
            'rif_document',
            'business_license',
            'owner_identity',
            'address_proof',
            'payment_evidence'
        )
    );
