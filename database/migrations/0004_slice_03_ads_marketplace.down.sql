drop index if exists credits_ledger_active_hold_per_ad_idx;
drop index if exists credits_ledger_related_ad_idx;
drop index if exists credits_ledger_reference_created_idx;
drop index if exists credits_ledger_type_created_idx;
drop index if exists credits_ledger_business_created_idx;
drop index if exists ads_no_overlap_lookup_idx;
drop index if exists ads_payment_method_id_idx;
drop index if exists ads_expires_status_idx;
drop index if exists ads_business_status_created_idx;
drop index if exists ads_marketplace_active_idx;
drop index if exists credit_wallets_business_id_idx;

alter table if exists ads drop constraint if exists ads_credit_consumed_ledger_fk;
alter table if exists ads drop constraint if exists ads_credit_hold_ledger_fk;

drop table if exists credits_ledger;
drop table if exists ads;
drop table if exists credit_wallets;
