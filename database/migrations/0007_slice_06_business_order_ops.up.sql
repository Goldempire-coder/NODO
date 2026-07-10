alter table orders drop constraint if exists orders_status_check;
alter table orders
    add constraint orders_status_check check (
        status in (
            'waiting_payment',
            'payment_reported',
            'payment_rejected',
            'payment_confirmed',
            'delivered',
            'completed',
            'cancelled',
            'disputed'
        )
    );

alter table order_state_events drop constraint if exists order_state_events_to_status_check;
alter table order_state_events
    add constraint order_state_events_to_status_check check (
        to_status in (
            'waiting_payment',
            'payment_reported',
            'payment_rejected',
            'payment_confirmed',
            'delivered',
            'completed',
            'cancelled',
            'disputed'
        )
    );

alter table order_state_events drop constraint if exists order_state_events_from_status_check;
alter table order_state_events
    add constraint order_state_events_from_status_check check (
        from_status is null
        or from_status in (
            'waiting_payment',
            'payment_reported',
            'payment_rejected',
            'payment_confirmed',
            'delivered',
            'completed',
            'cancelled',
            'disputed'
        )
    );

create index if not exists payment_reports_order_status_created_idx
    on payment_reports(order_id, status, created_at desc);

create index if not exists credits_ledger_reference_type_id_type_idx
    on credits_ledger(reference_type, reference_id, type);

create index if not exists credits_ledger_related_order_type_idx
    on credits_ledger(related_order_id, type)
    where related_order_id is not null;
