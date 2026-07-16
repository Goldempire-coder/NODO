drop index if exists businesses_marketplace_operational_idx;

alter table businesses
  drop column if exists is_accepting_orders;
