do $$
begin
    if exists (
        select 1
        from credit_purchase_onchain_payments
        where chain_id <> 8453
           or network <> 'base_mainnet'
           or token_contract_address <> '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
    ) then
        raise exception '0059 rollback blocked: non-mainnet onchain payment evidence exists; apply an approved transition migration first';
    end if;
end $$;

alter table credit_purchase_onchain_payments
    add constraint credit_purchase_onchain_chain_0017_check check (
        chain_id = 8453
        and network = 'base_mainnet'
    ) not valid;

alter table credit_purchase_onchain_payments
    validate constraint credit_purchase_onchain_chain_0017_check;

alter table credit_purchase_onchain_payments
    add constraint credit_purchase_onchain_token_0017_check check (
        token_symbol = 'USDC'
        and token_decimals = 6
        and token_contract_address = lower(token_contract_address)
        and token_contract_address = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
    ) not valid;

alter table credit_purchase_onchain_payments
    validate constraint credit_purchase_onchain_token_0017_check;

alter table credit_purchase_onchain_payments
    drop constraint if exists credit_purchase_onchain_network_profile_check;

alter table credit_purchase_onchain_payments
    drop constraint if exists credit_purchase_onchain_contract_metadata_check;

alter table credit_purchase_onchain_payments
    rename constraint credit_purchase_onchain_chain_0017_check
    to credit_purchase_onchain_chain_check;

alter table credit_purchase_onchain_payments
    rename constraint credit_purchase_onchain_token_0017_check
    to credit_purchase_onchain_token_check;
