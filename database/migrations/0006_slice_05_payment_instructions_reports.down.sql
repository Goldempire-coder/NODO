drop index if exists payment_reports_order_submitted_idx;
drop index if exists payment_reports_reported_by_idempotency_idx;
drop index if exists payment_reports_reported_by_created_idx;
drop index if exists payment_reports_status_created_idx;
drop index if exists payment_reports_order_created_idx;
drop index if exists orders_business_response_deadline_idx;
drop index if exists orders_business_response_warning_idx;

drop table if exists payment_reports;

delete from file_assets
where resource_type = 'payment_report'
   or file_type = 'payment_evidence';

alter table file_assets drop constraint if exists file_assets_file_type_check;
alter table file_assets drop constraint if exists file_assets_resource_type_check;

alter table file_assets
    add constraint file_assets_resource_type_check check (resource_type = 'business');

alter table file_assets
    add constraint file_assets_file_type_check check (
        file_type in ('rif_document', 'business_license', 'owner_identity', 'address_proof')
    );
