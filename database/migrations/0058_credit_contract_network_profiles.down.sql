do $$
begin
    if exists (
        select 1
        from credit_purchases
        where payment_method = 'base_usdc_contract'
          and (
              chain_id = 84532
              or network = 'base_sepolia'
              or token_contract_address = '0x036cbd53842c5426634e7929541ec2318f3dcf7e'
          )
    ) then
        raise exception '0058 rollback blocked: base_sepolia contract purchases exist; apply an approved transition migration first'
            using errcode = 'P0001';
    end if;
end
$$;

alter table credit_purchases
    add constraint credit_purchases_base_usdc_contract_shape_0057_check check (
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
    ) not valid;

alter table credit_purchases
    validate constraint credit_purchases_base_usdc_contract_shape_0057_check;

alter table credit_purchases
    drop constraint if exists credit_purchases_base_usdc_contract_shape_check;

alter table credit_purchases
    rename constraint credit_purchases_base_usdc_contract_shape_0057_check
    to credit_purchases_base_usdc_contract_shape_check;
