alter table support_tickets
    add column if not exists report_kind text null;

alter table support_tickets
    drop constraint if exists support_tickets_report_kind_check;

alter table support_tickets
    add constraint support_tickets_report_kind_check check (
        report_kind is null
        or report_kind = 'structured_operation_report'
    );

create unique index if not exists support_tickets_active_operation_report_order_uidx
    on support_tickets(order_id)
    where report_kind = 'structured_operation_report'
      and status in ('open', 'waiting_support', 'waiting_user', 'escalated');
