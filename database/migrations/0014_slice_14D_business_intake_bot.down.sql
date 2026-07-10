drop index if exists file_assets_business_intake_resource_idx;
drop index if exists business_intake_requests_created_business_idx;
drop index if exists business_intake_requests_contact_phone_created_idx;
drop index if exists business_intake_requests_chat_update_unique_idx;
drop index if exists business_intake_requests_telegram_chat_created_idx;
drop index if exists business_intake_requests_telegram_user_created_idx;
drop index if exists business_intake_requests_status_submitted_idx;

drop table if exists business_intake_requests;

alter table file_assets drop constraint if exists file_assets_resource_type_check;
alter table file_assets drop constraint if exists file_assets_file_type_check;

alter table file_assets
    add constraint file_assets_resource_type_check check (
        resource_type in ('business', 'payment_report', 'message', 'credit_purchase')
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
            'credit_purchase_proof'
        )
    );
