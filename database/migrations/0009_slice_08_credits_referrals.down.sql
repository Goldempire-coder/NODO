drop index if exists credits_ledger_related_credit_purchase_idx;
drop index if exists file_assets_credit_purchase_resource_idx;
drop index if exists referral_events_status_created_idx;
drop index if exists referral_events_referrer_created_idx;
drop index if exists referral_events_referred_active_idx;
drop index if exists referral_codes_code_status_idx;
drop index if exists referral_codes_business_idx;
drop index if exists credit_purchases_manual_tx_hash_idx;
drop index if exists credit_purchases_manual_reference_idx;
drop index if exists credit_purchases_stripe_payment_intent_idx;
drop index if exists credit_purchases_stripe_event_idx;
drop index if exists credit_purchases_stripe_session_idx;
drop index if exists credit_purchases_business_idempotency_idx;
drop index if exists credit_purchases_status_created_idx;
drop index if exists credit_purchases_business_created_idx;

alter table credits_ledger
    drop constraint if exists credits_ledger_related_credit_purchase_fk;

delete from credits_ledger
where related_credit_purchase_id is not null
   or type in ('referral_bonus', 'admin_adjustment');

drop table if exists referral_events;
drop table if exists referral_codes;
drop table if exists credit_purchases;

alter table file_assets drop constraint if exists file_assets_file_type_check;
alter table file_assets drop constraint if exists file_assets_resource_type_check;

alter table file_assets
    add constraint file_assets_resource_type_check check (
        resource_type in ('business', 'payment_report', 'message')
    );

alter table file_assets
    add constraint file_assets_file_type_check check (
        file_type in (
            'rif_document',
            'business_license',
            'owner_identity',
            'address_proof',
            'payment_evidence',
            'message_attachment'
        )
    );

alter table credits_ledger drop constraint if exists credits_ledger_type_check;

alter table credits_ledger
    add constraint credits_ledger_type_check check (
        type in ('purchase', 'founder_free_use', 'hold', 'consume', 'release', 'refund', 'adjustment')
    );
