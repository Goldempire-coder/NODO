# CREDITS_API.md

Contrato canonico para creditos publicitarios, compras, Stripe, pagos manuales,
founder access y referrals.

Todas las rutas activas usan prefijo `/api/v1`.

Rutas legacy prohibidas/no validas:

- `GET /credits/balance`
- `GET /credits/ledger`
- `POST /credit-purchases`
- `POST /credit-purchases/:id/manual-proof`
- `POST /webhooks/stripe` sin prefijo `/api/v1`
- `GET /admin/credit-purchases` sin prefijo `/api/v1`
- `POST /admin/credit-purchases/:id/approve`
- `POST /admin/credit-purchases/:id/reject`
- `POST /admin/credits/adjust` sin prefijo `/api/v1`

## Endpoints business

### GET /api/v1/business/credits/wallet

- Auth: business_owner.
- Scope: negocio propio aprobado.
- Response:
  - business_id
  - available_credits
  - blocked_credits
  - consumed_credits
  - lifetime_purchased_credits
  - lifetime_bonus_credits
  - lifetime_adjusted_credits
  - founder_status
  - founder_expires_at
  - referral_credits_earned
  - disclaimer
- No expone datos Stripe, comprobantes ni `storage_path`.

### GET /api/v1/business/credits/ledger

- Auth: business_owner.
- Scope: ledger de negocio propio.
- Query:
  - cursor
  - limit 1..50
  - type opcional contra enum oficial `credits_ledger.type`
- Response:
  - items con id, type, amount, balances before/after, reason, source,
    reference_type, reference_id, created_at
  - next_cursor
- No expone comprobantes ni secretos.

### POST /api/v1/business/credits/stripe-checkout

- Auth: business_owner.
- Idempotency-Key: obligatorio.
- Body:
  - package_code: starter | pro | business | enterprise
  - success_url opcional controlada por allowlist del backend
  - cancel_url opcional controlada por allowlist del backend
- Crea `credit_purchases.status = pending_payment`.
- Crea Stripe Checkout session.
- Response:
  - credit_purchase id
  - status
  - package_code
  - credits_amount
  - price_usd
  - checkout_url
  - expires_at si Stripe lo devuelve
- Audit:
  - credit_purchase_created
  - stripe_checkout_started
- No acredita creditos.
- El redirect frontend no acredita creditos.

### POST /api/v1/business/credits/manual-payment

- Auth: business_owner.
- Idempotency-Key: obligatorio.
- Content-Type: multipart/form-data o JSON + file upload adapter aprobado.
- Body:
  - package_code: starter | pro | business | enterprise
  - payment_method: zelle_manual_admin_approved | usdt_manual_admin_approved
  - manual_payment_reference requerido para Zelle
  - manual_tx_hash requerido para USDT TRC20
  - network = TRC20 requerido para USDT TRC20
  - proof file requerido
  - tipos permitidos: JPG, PNG, WebP y PDF, maximo 5 MB
  - el backend valida contenido real antes de storage; el MIME declarado debe coincidir y el nombre final usa extension canonica
  - imagenes deben ser decodificables; PDF requiere encabezado PDF valido y marcador final `%%EOF`, sin ejecutar ni renderizar el documento
  - archivo invalido no crea compra, `file_asset`, audit ni objeto en storage
- Crea `credit_purchases.status = pending_manual_review`.
- Guarda comprobante en `file_assets`:
  - resource_type = credit_purchase
  - resource_id = credit_purchases.id
  - file_type = credit_purchase_proof
  - owner_user_id = business owner id
  - storage privado
- Response:
  - purchase id
  - status
  - package_code
  - credits_amount
  - price_usd
  - proof metadata sin `storage_path`
- Audit:
  - credit_purchase_created
  - manual_credit_payment_submitted
- No acredita creditos.

### POST /api/v1/business/credits/base-payment

- Auth: business_owner.
- Scope: negocio propio aprobado con acceso activo.
- Idempotency-Key: obligatorio.
- Body:
  - package_code: starter | pro | business | enterprise
  - token: `USDC`
- Crea `credit_purchases.status = pending_payment`.
- Crea compra on-chain con:
  - payment_method = `base_usdc_onchain`
  - network = `base_mainnet`
  - chain_id = `8453`
  - token_symbol = `USDC`
  - token_contract_address = `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
  - token_decimals = `6`
  - destination_wallet_address = `NODO_CREDIT_RECEIVING_WALLET_BASE`
  - expected_amount_units `numeric(78,0)` calculado sin float
  - expires_at
- EVM values in persistence and comparisons must be normalized lowercase:
  - token_contract_address
  - destination_wallet_address
  - tx_hash
  - tx_from_address
  - tx_to_address
- Response:
  - purchase id
  - package_code
  - credits_amount
  - price_usd
  - payment_method
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
- USDT Base no es aceptado en MVP.
- USDT TRC20 manual no se mezcla con este endpoint.

### GET /api/v1/business/credits/purchases/{id}

- Auth: business_owner.
- Scope: compra propia.
- Response:
  - campos seguros de la compra
  - estado on-chain
  - confirmations
  - expires_at
  - tx_hash masked cuando exista
  - capabilities
- No expone RPC keys, raw provider response, `storage_path`, `account_value`, tokens ni secretos.

### POST /api/v1/business/credits/purchases/{id}/tx-hash

- Auth: business_owner.
- Scope: compra propia.
- Idempotency-Key: obligatorio.
- Body:
  - tx_hash
- Backend verifica on-chain antes de acreditar.
- Validaciones:
  - chain Base `8453`
  - token contract USDC oficial
  - destination wallet oficial
  - amount suficiente
  - confirmations minimas
  - tx/log no usado antes
  - purchase no terminal
- Response:
  - purchase id
  - status
  - verification_status
  - confirmations
  - mensaje seguro
- Audit:
  - onchain_tx_hash_submitted
  - onchain_payment_verified o evento de fallo/review segun resultado
- No acredita por texto libre ni screenshot.

### GET /api/v1/business/referrals

- Auth: business_owner.
- Scope: negocio propio.
- Genera codigo propio idempotente si no existe.
- Response:
  - referral_code
  - status
  - cap = 20
  - earned_credits
  - remaining_bonus_credits
  - events paginados

### POST /api/v1/business/referrals/apply

- Auth: business_owner.
- Idempotency-Key: obligatorio.
- Body:
  - referral_code
- Solo permitido para negocio propio antes de usar otro codigo o recibir bonus.
- Prohibe self-referral.
- Crea `referral_events.status = pending`.
- Audit:
  - referral_code_applied

Referral qualification:

- Stripe/manual legacy purchase qualifies when `credit_purchases.status = approved`.
- Base USDC on-chain purchase qualifies when `credit_purchases.status = credited`.
- Both require exactly one `credits_ledger.type = purchase` linked by `related_credit_purchase_id`.
- On-chain statuses before `credited` do not qualify referral bonuses.

## Stripe webhook

### POST /api/v1/webhooks/stripe

- Auth de usuario: no aplica.
- Requiere Stripe signature valida.
- Requiere secreto Stripe solo en backend runtime.
- Procesa eventos de Checkout/PaymentIntent aprobados por contrato.
- No confia en redirect frontend.
- Idempotencia/doble acreditacion debe validar:
  - stripe_event_id
  - stripe_checkout_session_id
  - credit_purchases.status
  - ledger reference_type/reference_id/type
  - idempotency store si aplica
- On success:
  - `credit_purchases.status = paid` y luego `approved`
  - setea paid_at/approved_at
  - escribe `credits_ledger.type = purchase`
  - incrementa wallet available/lifetime_purchased
  - audita `stripe_payment_succeeded` y `credits_added`
- On failure/expired:
  - status failed/expired
  - audita `stripe_payment_failed`
- Duplicate event:
  - responder 200 seguro si ya fue procesado sin re-acreditar
  - usar error interno/metric `STRIPE_WEBHOOK_DUPLICATE` si se reporta como API error en tests

## Admin endpoints

### GET /api/v1/admin/credit-purchases

- Auth: admin/super_admin; support read-only si contrato admin lo permite.
- Query:
  - status
  - business_id
  - cursor
  - limit 1..50
- Response:
  - compras con datos sensibles masked
  - proof metadata sin `storage_path`

### POST /api/v1/admin/credit-purchases/{id}/approve

- Auth: admin/super_admin.
- Idempotency-Key: obligatorio.
- Body:
  - reason requerido
- Solo para `pending_manual_review`.
- Escribe `credit_purchases.status = approved`.
- Acredita wallet exactamente una vez.
- Escribe `credits_ledger.type = purchase`.
- Audit:
  - manual_credit_payment_approved
  - credits_added
- Prohibe support.

### POST /api/v1/admin/credit-purchases/{id}/reject

- Auth: admin/super_admin.
- Idempotency-Key: obligatorio.
- Body:
  - reason requerido
- Solo para `pending_manual_review`.
- Escribe `credit_purchases.status = rejected`.
- No acredita creditos.
- Audit:
  - manual_credit_payment_rejected

### GET /api/v1/admin/credit-purchases/{id}

- Auth: admin/super_admin; support read-only enmascarado si contrato admin lo permite.
- Response:
  - detalle de compra con datos sensibles masked
  - metadata on-chain segura si payment_method = `base_usdc_onchain`
  - proof metadata sin `storage_path`
- No expone RPC keys, raw provider responses, private keys, seed phrases ni signed URLs persistidas.

### POST /api/v1/admin/credit-purchases/{id}/onchain-reject

- Auth: admin/super_admin.
- Idempotency-Key: obligatorio.
- Body:
  - reason requerido
- Solo para `under_review`.
- Escribe `credit_purchases.status = rejected`.
- No acredita creditos.
- Audit:
  - onchain_payment_rejected
- Prohibe support.

### POST /api/v1/admin/credits/adjust

- Auth: admin/super_admin.
- Idempotency-Key: obligatorio.
- Body:
  - business_id
  - amount
  - direction: add | remove
  - reason requerido
  - notes opcional
- Escribe `credits_ledger.type = admin_adjustment`.
- Actualiza wallet sin permitir balances negativos.
- Audit:
  - admin_credit_adjustment

## Packages

- starter: 5 credits = 10 USD
- pro: 15 credits = 25 USD
- business: 50 credits = 75 USD
- enterprise: 200 credits = 250 USD

## Errores

- INVALID_PACKAGE
- INVALID_PAYMENT_METHOD
- PURCHASE_NOT_FOUND
- PURCHASE_STATUS_INVALID
- STRIPE_SIGNATURE_INVALID
- STRIPE_WEBHOOK_DUPLICATE
- STRIPE_SESSION_INVALID
- MANUAL_PAYMENT_PROOF_REQUIRED
- MANUAL_PAYMENT_ALREADY_REVIEWED
- ADMIN_REASON_REQUIRED
- CREDIT_ALREADY_GRANTED
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
- CREDIT_BALANCE_INSUFFICIENT
- CREDIT_WALLET_NOT_FOUND
- REFERRAL_NOT_ALLOWED
- REFERRAL_ALREADY_USED
- REFERRAL_CODE_NOT_FOUND
- REFERRAL_CAP_REACHED
- FOUNDER_ACCESS_EXPIRED
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_PAYLOAD_MISMATCH
- FORBIDDEN
- RATE_LIMITED
- VALIDATION_ERROR
- UNAUTHENTICATED

## Seguridad

- No secrets Stripe en frontend, repo, logs ni respuestas.
- No RPC keys en frontend, repo, logs ni respuestas.
- No private keys ni seed phrases para topups on-chain.
- No `storage_path` en API/frontend/logs/audit.
- Comprobantes manuales solo en storage privado y signed URL corta para admin.
- Admin actions requieren reason.
- Permission errors no filtran existencia privada.
