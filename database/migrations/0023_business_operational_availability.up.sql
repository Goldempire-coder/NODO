alter table businesses
  add column if not exists is_accepting_orders boolean not null default true;

create index if not exists businesses_marketplace_operational_idx
  on businesses (verification_status, risk_level, is_accepting_orders)
  where verification_status = 'approved';
