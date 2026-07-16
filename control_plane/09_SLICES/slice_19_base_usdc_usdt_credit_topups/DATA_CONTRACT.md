# DATA_CONTRACT.md

## Modelo canonico

Extender `credit_purchases` con campos on-chain y crear tabla de intentos `credit_purchase_onchain_payments`.

`credit_purchases` conserva la compra como recurso principal y `credits_ledger.related_credit_purchase_id` como referencia de acreditacion.

## credit_purchases campos nuevos

- chain_id integer nullable
- network text nullable
- token_symbol text nullable
- token_contract_address text nullable
- token_decimals integer nullable
- expected_amount_units numeric(78,0) not null para on-chain
- destination_wallet_address text nullable
- verification_status text nullable
- verification_source text nullable
- detected_at timestamptz nullable
- verified_at timestamptz nullable
- credited_at timestamptz nullable
- expires_at timestamptz nullable

## credit_purchase_onchain_payments

- id uuid primary key
- credit_purchase_id uuid FK credit_purchases(id)
- business_id uuid FK businesses(id)
- chain_id integer not null
- network text not null
- token_symbol text not null
- token_contract_address text not null
- token_decimals integer not null
- tx_hash text not null
- tx_from_address text nullable
- tx_to_address text not null
- tx_block_number bigint nullable
- tx_log_index integer not null default 0
- tx_amount_units numeric(78,0) not null
- confirmations integer not null default 0
- verification_source text not null
- verification_status text not null
- failure_code text nullable
- detected_at timestamptz nullable
- verified_at timestamptz nullable
- credited_at timestamptz nullable
- created_at timestamptz not null
- updated_at timestamptz not null

## Constraints

- `chain_id = 8453` for active Base mainnet purchases.
- `network = 'base_mainnet'`.
- `token_symbol = 'USDC'`.
- `token_contract_address = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'`.
- `token_decimals = 6`.
- `payment_method = 'base_usdc_onchain'` for on-chain MVP.
- unique `(chain_id, tx_hash, tx_log_index)`.
- `expected_amount_units > 0`.
- `tx_amount_units > 0`.
- EVM values must be normalized lowercase before persistence and comparison:
  - token_contract_address
  - destination_wallet_address
  - tx_hash
  - tx_from_address
  - tx_to_address
- Constraints and queries must use `lower(...)` or an equivalent canonical normalization policy.
- `destination_wallet_address` required for `base_usdc_onchain`.
- `expires_at` required for `base_usdc_onchain`.
- no status `credited` unless ledger purchase exists for `related_credit_purchase_id`.

## Indexes

- `credit_purchases(business_id, status, created_at desc)`.
- `credit_purchases(payment_method, status, expires_at)`.
- `credit_purchases(chain_id, token_contract_address, status)`.
- `credit_purchase_onchain_payments(credit_purchase_id, created_at desc)`.
- `credit_purchase_onchain_payments(business_id, created_at desc)`.
- unique `credit_purchase_onchain_payments(chain_id, tx_hash, tx_log_index)`.
- `credit_purchase_onchain_payments(verification_status, created_at desc)`.

## Ledger

Accreditation:

- `credits_ledger.type = purchase`
- `related_credit_purchase_id = credit_purchases.id`
- `reason = base_usdc_onchain_verified`
- `source = credit_purchases`
- `reference_type = credit_purchase`
- `reference_id = credit_purchases.id`

Ledger y wallet se actualizan en una sola transaccion.
