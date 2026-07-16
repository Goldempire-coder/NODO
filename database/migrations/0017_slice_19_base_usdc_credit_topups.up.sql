alter table credit_purchases drop constraint if exists credit_purchases_method_check;
alter table credit_purchases drop constraint if exists credit_purchases_status_check;
alter table credit_purchases drop constraint if exists credit_purchases_manual_shape_check;
alter table credit_purchases drop constraint if exists credit_purchases_admin_reason_check;

alter table credit_purchases
    add constraint credit_purchases_method_check check (
        payment_method in ('stripe_checkout', 'zelle_manual_admin_approved', 'usdt_manual_admin_approved', 'base_usdc_onchain')
    );

alter table credit_purchases
    add constraint credit_purchases_status_check check (
        status in (
            'created',
            'pending_payment',
            'pending_manual_review',
            'pending_onchain_confirmation',
            'detected',
            'verified',
            'credited',
            'under_review',
            'paid',
            'approved',
            'rejected',
            'failed',
            'expired',
            'verification_failed'
        )
    );

alter table credit_purchases
    add column if not exists chain_id integer null,
    add column if not exists network text null,
    add column if not exists token_symbol text null,
    add column if not exists token_contract_address text null,
    add column if not exists token_decimals integer null,
    add column if not exists expected_amount_units numeric(78,0) null,
    add column if not exists destination_wallet_address text null,
    add column if not exists tx_hash text null,
    add column if not exists tx_amount_units numeric(78,0) null,
    add column if not exists tx_from_address text null,
    add column if not exists tx_to_address text null,
    add column if not exists tx_block_number bigint null,
    add column if not exists tx_log_index integer null,
    add column if not exists confirmations integer null,
    add column if not exists verification_source text null,
    add column if not exists verification_status text null,
    add column if not exists detected_at timestamptz null,
    add column if not exists verified_at timestamptz null,
    add column if not exists credited_at timestamptz null,
    add column if not exists expires_at timestamptz null;

alter table credit_purchases drop constraint if exists credit_purchases_base_usdc_shape_check;
alter table credit_purchases
    add constraint credit_purchases_base_usdc_shape_check check (
        payment_method <> 'base_usdc_onchain'
        or (
            chain_id = 8453
            and network = 'base_mainnet'
            and token_symbol = 'USDC'
            and lower(token_contract_address) = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
            and token_contract_address = lower(token_contract_address)
            and token_decimals = 6
            and expected_amount_units is not null
            and expected_amount_units > 0
            and destination_wallet_address is not null
            and destination_wallet_address = lower(destination_wallet_address)
            and expires_at is not null
        )
    );

alter table credit_purchases
    add constraint credit_purchases_manual_shape_check check (
        payment_method = 'stripe_checkout'
        or payment_method = 'base_usdc_onchain'
        or (status = 'pending_manual_review' and proof_file_id is not null)
        or status in ('approved', 'rejected', 'failed', 'expired')
    );

alter table credit_purchases
    add constraint credit_purchases_admin_reason_check check (
        status not in ('approved', 'rejected')
        or payment_method in ('stripe_checkout', 'base_usdc_onchain')
        or admin_note is not null
    );

create table if not exists credit_purchase_onchain_payments (
    id uuid primary key default gen_random_uuid(),
    credit_purchase_id uuid not null references credit_purchases(id),
    chain_id integer not null,
    network text not null,
    token_symbol text not null,
    token_contract_address text not null,
    token_decimals integer not null,
    expected_amount_units numeric(78,0) not null,
    tx_hash text not null,
    tx_from_address text null,
    tx_to_address text not null,
    tx_amount_units numeric(78,0) not null,
    tx_block_number bigint not null,
    tx_log_index integer not null,
    confirmations integer not null default 0,
    verification_source text not null,
    verification_status text not null,
    detected_at timestamptz null,
    verified_at timestamptz null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint credit_purchase_onchain_chain_check check (chain_id = 8453 and network = 'base_mainnet'),
    constraint credit_purchase_onchain_token_check check (
        token_symbol = 'USDC'
        and token_decimals = 6
        and token_contract_address = lower(token_contract_address)
        and token_contract_address = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
    ),
    constraint credit_purchase_onchain_amounts_check check (expected_amount_units > 0 and tx_amount_units > 0),
    constraint credit_purchase_onchain_evm_normalized_check check (
        tx_hash = lower(tx_hash)
        and tx_to_address = lower(tx_to_address)
        and (tx_from_address is null or tx_from_address = lower(tx_from_address))
    ),
    constraint credit_purchase_onchain_status_check check (
        verification_status in ('pending_onchain_confirmation', 'detected', 'verified', 'credited', 'under_review', 'verification_failed')
    )
);

create unique index if not exists credit_purchase_onchain_tx_log_unique_idx
    on credit_purchase_onchain_payments(chain_id, tx_hash, tx_log_index);

create index if not exists credit_purchases_onchain_status_idx
    on credit_purchases(payment_method, status, created_at)
    where payment_method = 'base_usdc_onchain';

create index if not exists credit_purchase_onchain_purchase_idx
    on credit_purchase_onchain_payments(credit_purchase_id, created_at desc);

create index if not exists credit_purchase_onchain_status_idx
    on credit_purchase_onchain_payments(verification_status, created_at desc);
