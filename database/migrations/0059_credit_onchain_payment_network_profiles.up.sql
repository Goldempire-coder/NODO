alter table credit_purchase_onchain_payments
    add constraint credit_purchase_onchain_network_profile_0059_check check (
        token_symbol = 'USDC'
        and token_decimals = 6
        and token_contract_address = lower(token_contract_address)
        and (
            (
                chain_id = 8453
                and network = 'base_mainnet'
                and token_contract_address = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
            )
            or (
                chain_id = 84532
                and network = 'base_sepolia'
                and token_contract_address = '0x036cbd53842c5426634e7929541ec2318f3dcf7e'
            )
        )
    ) not valid;

alter table credit_purchase_onchain_payments
    validate constraint credit_purchase_onchain_network_profile_0059_check;

alter table credit_purchase_onchain_payments
    drop constraint if exists credit_purchase_onchain_chain_check;

alter table credit_purchase_onchain_payments
    drop constraint if exists credit_purchase_onchain_token_check;

alter table credit_purchase_onchain_payments
    rename constraint credit_purchase_onchain_network_profile_0059_check
    to credit_purchase_onchain_network_profile_check;

alter table credit_purchase_onchain_payments
    add constraint credit_purchase_onchain_contract_metadata_check check (
        (
            payment_contract_address is null
            and purchase_ref is null
            and payer_address is null
            and payment_contract_version is null
        )
        or (
            payment_contract_address is not null
            and payment_contract_address ~ '^0x[0-9a-f]{40}$'
            and purchase_ref is not null
            and purchase_ref ~ '^0x[0-9a-f]{64}$'
            and payer_address is not null
            and payer_address ~ '^0x[0-9a-f]{40}$'
            and payment_contract_version is not null
            and payment_contract_version > 0
        )
    ) not valid;

alter table credit_purchase_onchain_payments
    validate constraint credit_purchase_onchain_contract_metadata_check;
