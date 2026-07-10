drop index if exists order_state_events_type_created_idx;
drop index if exists order_state_events_order_created_idx;
drop index if exists orders_waiting_deadline_idx;
drop index if exists orders_ad_idx;
drop index if exists orders_remitter_status_created_idx;
drop index if exists orders_business_status_created_idx;
drop index if exists orders_status_created_idx;
drop index if exists orders_business_created_idx;
drop index if exists orders_remitter_created_idx;
drop index if exists orders_remitter_idempotency_idx;
drop index if exists orders_public_order_code_idx;

alter table if exists credits_ledger drop constraint if exists credits_ledger_related_order_fk;

drop table if exists order_state_events;
drop table if exists orders;
