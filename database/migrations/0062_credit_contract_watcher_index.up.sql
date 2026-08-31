create index if not exists credit_purchases_contract_pending_watcher_idx
    on credit_purchases(created_at, id)
    where payment_method = 'base_usdc_contract'
      and status in ('pending_payment', 'pending_onchain_confirmation', 'detected')
      and expected_amount_units is not null
      and destination_wallet_address is not null
      and onchain_purchase_ref is not null
      and onchain_payer_address is not null
      and payment_contract_address is not null
      and payment_contract_version is not null;
