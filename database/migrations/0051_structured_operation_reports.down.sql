drop index if exists support_tickets_active_operation_report_order_uidx;

alter table support_tickets
    drop constraint if exists support_tickets_report_kind_check;

alter table support_tickets
    drop column if exists report_kind;
