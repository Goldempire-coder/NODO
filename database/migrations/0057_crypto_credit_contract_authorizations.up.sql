alter table credit_purchases
    add column if not exists onchain_purchase_ref text null,
    add column if not exists onchain_payer_address text null,
    add column if not exists payment_contract_address text null,
    add column if not exists payment_contract_version integer null,
    add column if not exists payment_authorization_expires_at timestamptz null,
    add column if not exists payment_authorization_digest text null,
    add column if not exists payment_authorization_signature text null,
    add column if not exists payment_authorization_signer_address text null,
    add column if not exists payment_authorization_signer_version text null,
    add column if not exists payment_authorization_signed_at timestamptz null;

alter table credit_purchase_onchain_payments
    add column if not exists payment_contract_address text null,
    add column if not exists purchase_ref text null,
    add column if not exists payer_address text null,
    add column if not exists payment_contract_version integer null;

alter table credit_purchases drop constraint if exists credit_purchases_method_check;
alter table credit_purchases drop constraint if exists credit_purchases_manual_shape_check;
alter table credit_purchases drop constraint if exists credit_purchases_admin_reason_check;

alter table credit_purchases
    add constraint credit_purchases_method_check check (
        payment_method in (
            'stripe_checkout',
            'zelle_manual_admin_approved',
            'usdt_manual_admin_approved',
            'base_usdc_onchain',
            'base_usdc_contract'
        )
    );

alter table credit_purchases
    add constraint credit_purchases_manual_shape_check check (
        payment_method in ('stripe_checkout', 'base_usdc_onchain', 'base_usdc_contract')
        or (status = 'pending_manual_review' and proof_file_id is not null)
        or status in ('approved', 'rejected', 'failed', 'expired')
    );

alter table credit_purchases
    add constraint credit_purchases_admin_reason_check check (
        status not in ('approved', 'rejected')
        or payment_method in ('stripe_checkout', 'base_usdc_onchain', 'base_usdc_contract')
        or admin_note is not null
    );

alter table credit_purchases
    add constraint credit_purchases_base_usdc_contract_shape_check check (
        payment_method <> 'base_usdc_contract'
        or (
            chain_id = 8453
            and network = 'base_mainnet'
            and token_symbol = 'USDC'
            and token_decimals = 6
            and token_contract_address = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
            and expected_amount_units > 0
            and destination_wallet_address ~ '^0x[0-9a-f]{40}$'
            and onchain_purchase_ref ~ '^0x[0-9a-f]{64}$'
            and onchain_payer_address ~ '^0x[0-9a-f]{40}$'
            and payment_contract_address ~ '^0x[0-9a-f]{40}$'
            and payment_contract_version > 0
            and payment_authorization_expires_at is not null
            and payment_authorization_expires_at = expires_at
            and payment_authorization_digest ~ '^0x[0-9a-f]{64}$'
            and payment_authorization_signature ~ '^0x[0-9a-f]{130}$'
            and payment_authorization_signer_address ~ '^0x[0-9a-f]{40}$'
            and length(payment_authorization_signer_version) between 1 and 64
            and payment_authorization_signed_at is not null
            and payment_authorization_signed_at < payment_authorization_expires_at
        )
    );

create unique index if not exists credit_purchases_onchain_purchase_ref_unique_idx
    on credit_purchases(onchain_purchase_ref)
    where onchain_purchase_ref is not null;
