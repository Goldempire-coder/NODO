drop index if exists credit_purchase_onchain_status_idx;
drop index if exists credit_purchase_onchain_purchase_idx;
drop index if exists credit_purchases_onchain_status_idx;
drop index if exists credit_purchase_onchain_tx_log_unique_idx;
drop table if exists credit_purchase_onchain_payments;

alter table credit_purchases drop constraint if exists credit_purchases_base_usdc_shape_check;
alter table credit_purchases drop constraint if exists credit_purchases_manual_shape_check;
alter table credit_purchases drop constraint if exists credit_purchases_admin_reason_check;
alter table credit_purchases drop constraint if exists credit_purchases_method_check;
alter table credit_purchases drop constraint if exists credit_purchases_status_check;

alter table credit_purchases
    drop column if exists chain_id,
    drop column if exists network,
    drop column if exists token_symbol,
    drop column if exists token_contract_address,
    drop column if exists token_decimals,
    drop column if exists expected_amount_units,
    drop column if exists destination_wallet_address,
    drop column if exists tx_hash,
    drop column if exists tx_amount_units,
    drop column if exists tx_from_address,
    drop column if exists tx_to_address,
    drop column if exists tx_block_number,
    drop column if exists tx_log_index,
    drop column if exists confirmations,
    drop column if exists verification_source,
    drop column if exists verification_status,
    drop column if exists detected_at,
    drop column if exists verified_at,
    drop column if exists credited_at,
    drop column if exists expires_at;

alter table credit_purchases
    add constraint credit_purchases_method_check check (
        payment_method in ('stripe_checkout', 'zelle_manual_admin_approved', 'usdt_manual_admin_approved')
    );

alter table credit_purchases
    add constraint credit_purchases_status_check check (
        status in ('created', 'pending_payment', 'pending_manual_review', 'paid', 'approved', 'rejected', 'failed', 'expired')
    );

alter table credit_purchases
    add constraint credit_purchases_manual_shape_check check (
        payment_method = 'stripe_checkout'
        or (status = 'pending_manual_review' and proof_file_id is not null)
        or status in ('approved', 'rejected', 'failed', 'expired')
    );

alter table credit_purchases
    add constraint credit_purchases_admin_reason_check check (
        status not in ('approved', 'rejected')
        or payment_method = 'stripe_checkout'
        or admin_note is not null
    );
