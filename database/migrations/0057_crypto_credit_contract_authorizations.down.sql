do $$
begin
    if exists (
        select 1
        from credit_purchases
        where payment_method = 'base_usdc_contract'
    ) then
        raise exception '0057 rollback blocked: base_usdc_contract purchases exist; apply an approved transition migration first'
            using errcode = 'P0001';
    end if;
end
$$;

drop index if exists credit_purchases_onchain_purchase_ref_unique_idx;

alter table credit_purchases drop constraint if exists credit_purchases_base_usdc_contract_shape_check;
alter table credit_purchases drop constraint if exists credit_purchases_manual_shape_check;
alter table credit_purchases drop constraint if exists credit_purchases_admin_reason_check;
alter table credit_purchases drop constraint if exists credit_purchases_method_check;

alter table credit_purchases
    add constraint credit_purchases_method_check check (
        payment_method in ('stripe_checkout', 'zelle_manual_admin_approved', 'usdt_manual_admin_approved', 'base_usdc_onchain')
    );

alter table credit_purchases
    add constraint credit_purchases_manual_shape_check check (
        payment_method in ('stripe_checkout', 'base_usdc_onchain')
        or (status = 'pending_manual_review' and proof_file_id is not null)
        or status in ('approved', 'rejected', 'failed', 'expired')
    );

alter table credit_purchases
    add constraint credit_purchases_admin_reason_check check (
        status not in ('approved', 'rejected')
        or payment_method in ('stripe_checkout', 'base_usdc_onchain')
        or admin_note is not null
    );

alter table credit_purchase_onchain_payments
    drop column if exists payment_contract_address,
    drop column if exists purchase_ref,
    drop column if exists payer_address,
    drop column if exists payment_contract_version;

alter table credit_purchases
    drop column if exists onchain_purchase_ref,
    drop column if exists onchain_payer_address,
    drop column if exists payment_contract_address,
    drop column if exists payment_contract_version,
    drop column if exists payment_authorization_expires_at,
    drop column if exists payment_authorization_digest,
    drop column if exists payment_authorization_signature,
    drop column if exists payment_authorization_signer_address,
    drop column if exists payment_authorization_signer_version,
    drop column if exists payment_authorization_signed_at;
