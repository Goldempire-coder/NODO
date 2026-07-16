# API_CONTRACT.md

Todas las rutas usan `/api/v1`.

## POST /api/v1/business/credits/base-payment

- Auth: business_owner.
- Scope: negocio propio aprobado y acceso negocio activo.
- Idempotency-Key: obligatorio.
- Body:
  - package_code: starter | pro | business | enterprise
  - token: `USDC`
- Reglas:
  - network fija: Base mainnet.
  - chain_id fijo: `8453`.
  - token_contract_address fijo: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`.
  - destination_wallet_address desde `NODO_CREDIT_RECEIVING_WALLET_BASE`.
  - status inicial `pending_payment`.
- Response:
  - purchase id
  - package_code
  - credits_amount
  - price_usd
  - payment_method = `base_usdc_onchain`
  - status
  - network
  - chain_id
  - token_symbol
  - token_contract_address
  - token_decimals
  - expected_amount_units
  - expected_amount_display
  - destination_wallet_address
  - expires_at
  - min_confirmations
  - disclaimer
- Audit:
  - onchain_credit_purchase_created
- No acredita creditos.

## GET /api/v1/business/credits/purchases/{id}

- Auth: business_owner.
- Scope: compra propia.
- Response:
  - purchase safe fields
  - onchain status fields
  - masked tx_hash when present
  - confirmations
  - expires_at
  - capabilities
- No expone RPC keys, raw provider data, `storage_path`, `account_value` ni secretos.

## POST /api/v1/business/credits/purchases/{id}/tx-hash

- Auth: business_owner.
- Scope: compra propia.
- Idempotency-Key: obligatorio.
- Body:
  - tx_hash
- Reglas:
  - valida formato hash EVM.
  - purchase debe estar `pending_payment`, `detected`, `pending_onchain_confirmation` o `under_review` sin ledger.
  - backend verifica on-chain; no acredita por texto libre.
- Response:
  - purchase id
  - status
  - verification_status
  - confirmations
  - safe message
- Audit:
  - onchain_tx_hash_submitted
  - onchain_payment_verified o evento de fallo/review segun resultado

## Admin review

### GET /api/v1/admin/credit-purchases

Debe soportar `payment_method = base_usdc_onchain` y status on-chain.

### GET /api/v1/admin/credit-purchases/{id}

- Auth: admin/super_admin/support read-only.
- Response: metadata on-chain enmascarada, sin secretos ni raw RPC.

### POST /api/v1/admin/credit-purchases/{id}/onchain-reject

- Auth: admin/super_admin.
- Idempotency-Key: obligatorio.
- Body:
  - reason requerido
- Solo para `under_review`.
- Cambia status a `rejected`.
- No acredita creditos.
- Audit:
  - onchain_payment_rejected

## Errores

- ONCHAIN_CHAIN_INVALID
- ONCHAIN_TOKEN_NOT_ALLOWED
- ONCHAIN_DESTINATION_MISMATCH
- ONCHAIN_AMOUNT_INSUFFICIENT
- ONCHAIN_CONFIRMATIONS_PENDING
- ONCHAIN_TX_NOT_FOUND
- ONCHAIN_TX_ALREADY_USED
- ONCHAIN_TX_HASH_INVALID
- ONCHAIN_PURCHASE_EXPIRED
- ONCHAIN_PURCHASE_STATUS_INVALID
- ONCHAIN_RPC_UNAVAILABLE
- ONCHAIN_VERIFICATION_FAILED
- ONCHAIN_REVIEW_REQUIRED
- INVALID_PACKAGE
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_PAYLOAD_MISMATCH
- FORBIDDEN
- RATE_LIMITED
