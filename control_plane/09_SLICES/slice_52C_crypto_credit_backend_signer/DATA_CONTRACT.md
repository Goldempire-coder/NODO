# DATA_CONTRACT.md

52C requiere migracion futura reversible. Numero sugerido: `0057`.

## Campos En `credit_purchases`

Agregar o equivalente:

- `onchain_purchase_ref text null`
- `onchain_payer_address text null`
- `payment_contract_address text null`
- `payment_contract_version integer null`
- `payment_authorization_expires_at timestamptz null`
- `payment_authorization_digest text null`
- `payment_authorization_signature text null`
- `payment_authorization_signer_address text null`
- `payment_authorization_signer_version text null`
- `payment_authorization_signed_at timestamptz null`

## Campos En `credit_purchase_onchain_payments`

Agregar o equivalente:

- `payment_contract_address text null`
- `purchase_ref text null`
- `payer_address text null`
- `payment_contract_version integer null`

## Constraints

- `onchain_purchase_ref` canonical `0x` + 64 hex cuando exista.
- `onchain_purchase_ref` unique para compras contractuales.
- direcciones EVM normalizadas lowercase o comparacion canonica equivalente.
- `payment_authorization_expires_at` requerido para `base_usdc_contract`.
- `onchain_payer_address` requerido para `base_usdc_contract`.
- `payment_contract_address` requerido para `base_usdc_contract`.
- `payment_contract_version` requerido para `base_usdc_contract`.
- unique canonico de evento sigue siendo `(chain_id, tx_hash, tx_log_index)`.

## Estados

52C reutiliza estados on-chain existentes cuando sea posible:

- `pending_payment`
- `pending_onchain_confirmation`
- `detected`
- `verified`
- `credited`
- `under_review`
- `expired`
- `rejected`
- `verification_failed`

La firma/autorizacion no crea estado de credito. Una compra firmada sigue siendo
pendiente hasta que exista evidencia on-chain verificada.

## Metodo De Pago

Nuevo metodo propuesto:

```txt
base_usdc_contract
```

`base_usdc_onchain` directo a wallet queda legacy/fallback manual o staging y
nunca auto-acredita con trafico real controlado.
hasta decision de retiro. Para fondos reales, la ruta contractual es la
preferida.
