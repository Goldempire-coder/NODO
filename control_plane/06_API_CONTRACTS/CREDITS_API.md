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
- Flujo normal futuro: `base_usdc_contract`.
- Body contractual unico para la App Negocio normal:
  - package_code: starter | pro | business | enterprise
  - payer_wallet_address: direccion EVM conectada por el negocio
- Cualquier otro campo se rechaza con `422 VALIDATION_ERROR`, incluyendo:
  `amount`, `price`, `credits_amount`, `token`, `token_symbol`, `chain_id`,
  `network`, `treasury`, `destination_wallet_address`, `contract_address`,
  `contract_version`, `valid_until`, `expires_at`, `purchase_ref`,
  `authorization` y `signature`.
- Crea `credit_purchases.status = pending_payment`.
- El body contractual crea compra con `payment_method = base_usdc_contract`.
- Backend deriva desde sesion/configuracion/catalogo: negocio, paquete, precio,
  creditos, token, chain, contrato, treasury, version, expiracion y
  `purchase_ref`.
- La autoridad de red contractual es `NODO_CREDIT_PAYMENT_NETWORK`. Solo admite
  los perfiles cerrados `base_sepolia` y `base_mainnet`; valor ausente o
  desconocido falla cerrado con `503 CRYPTO_CONTRACT_PAYMENT_NOT_CONFIGURED`.
- Cada perfil fija como unidad inseparable `network`, `chain_id`, simbolo,
  contrato y decimales del token. Runtime no combina valores entre perfiles.
- 52C2D-S0 habilita frontend solo para `base_sepolia`: chain `84532`, USDC de
  testnet `0x036CbD53842c5426634e7929541eC2318f3dCF7e`. Esos tokens no tienen valor
  financiero. Mainnet queda definida pero no seleccionable desde frontend.
- Crear o firmar la compra no acredita creditos, no crea ledger y no mueve
  fondos.

Compatibilidad legacy durante la migracion:

- El body `{package_code, token_symbol: "USDC"}` no pertenece al frontend
  normal futuro.
- Solo puede aceptarse cuando no existe configuracion 52C, el entorno es
  local/staging o un flujo manual gobernado, y
  `LEGACY_CREDIT_PAYMENT_METHODS_ENABLED = true`.
- En cuanto exista cualquier configuracion 52C, el body legacy devuelve
  `422 VALIDATION_ERROR`, aunque el flag legacy este activo.
- La compra legacy usa:
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
- Response contractual inicial:
  - purchase id
  - package_code
  - credits_amount
  - price_usd
  - payment_method
  - status
  - network
  - chain_id
  - network_display_name
  - is_testnet
  - token_symbol
  - token_contract_address
  - token_decimals
  - expected_amount_units
  - expected_amount_display
  - contract_address y contract_version
  - purchase_ref
  - payer_wallet_address
  - authorization_valid_until
  - authorization_typed_data
  - authorization_signature
  - min_confirmations
  - disclaimer
- Audit contractual:
  - onchain_contract_purchase_created
  - onchain_contract_authorization_signed
- No acredita creditos.
- USDT Base no es aceptado en MVP.
- USDT TRC20 manual no se mezcla con este endpoint.
- Antes de habilitar 52C, la App Negocio debe migrarse al body contractual y
  dejar de mostrar wallet directa o pedir `tx_hash`.

Modo contractual 52C:

- payment_method = `base_usdc_contract`;
- backend deriva negocio desde sesion;
- backend resuelve paquete, monto, token, chain, contrato, treasury, version y
  expiracion;
- backend genera `purchase_ref` bytes32 aleatorio;
- backend guarda snapshot durable;
- backend firma autorizacion EIP-712 solo sobre ese snapshot;
- crear/firmar compra no acredita creditos.

Limites obligatorios antes de habilitar 52C fuera de pruebas:

- crear o reemitir: maximo 5 requests por usuario y 5 por negocio cada 10
  minutos;
- respaldo por IP hasheada: maximo 20 requests cada 10 minutos;
- maximo 3 compras contractuales no terminales por negocio, contando
  `pending_payment`, `pending_onchain_confirmation`, `detected` y
  `under_review`;
- un replay con la misma `Idempotency-Key` no crea otra compra y no consume otro
  cupo pendiente;
- al superar limites: `429 RATE_LIMITED` o
  `409 CRYPTO_PAYMENT_PENDING_LIMIT_REACHED` segun corresponda;
- en staging/produccion los contadores de mutacion son compartidos. Si el
  limitador compartido no esta disponible, crear/reemitir falla cerrado con
  `503 CRYPTO_PAYMENT_RATE_LIMIT_UNAVAILABLE`.

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
- Para una compra propia `base_usdc_contract`, este GET es tambien la respuesta
  de reanudacion tras recarga. No firma, no reemite y no consulta blockchain.
- Si la autorizacion durable sigue vigente y la configuracion/signer coinciden,
  incluye `payment` con:
  - `authorization_status = valid`
  - network, chain_id, token y monto esperado
  - contract_address y contract_version
  - purchase_ref y payer_wallet_address
  - authorization_valid_until
  - authorization_typed_data y authorization_signature originales
- Si vencio o la configuracion/signer ya no coincide, devuelve la compra con
  `authorization_status = expired | reissue_required`, omite una firma pagable
  y expone `capabilities.can_pay = false`.
- La respuesta es `Cache-Control: private, no-store`. No debe usarse polling;
  se carga al abrir/continuar la compra o por accion manual `Actualizar`.

### POST /api/v1/business/credits/purchases/{id}/tx-hash

- Auth: business_owner.
- Scope: compra propia.
- Idempotency-Key: obligatorio.
- Body:
  - tx_hash
- Esta ruta es solo compatibilidad de `base_usdc_onchain` y no forma parte del
  flujo normal `base_usdc_contract`.
- Para `base_usdc_contract` devuelve
  `409 CRYPTO_PAYMENT_TX_HASH_NOT_ACCEPTED`, sin guardar evidencia, cambiar
  estado, acreditar o crear ledger. El watcher contractual descubre el evento
  oficial por `purchase_ref`.
- Para transferencias directas legacy en local/staging o fallback manual, el
  hash solo puede abrir/actualizar revision `under_review`; nunca auto-acredita
  con trafico real controlado.
- El hash publico no demuestra propiedad ni intencion comercial.
- El frontend normal no muestra un campo para pegar `tx_hash`.
- El backend legacy valida on-chain antes de registrar evidencia para revision.
- La wallet destino se toma del snapshot backend de la compra; el cliente no
  puede enviarla ni reemplazarla.
- Validaciones:
  - chain Base `8453`
  - token contract USDC oficial
  - destination wallet oficial
  - amount suficiente
  - confirmations minimas
  - tx/log no usado antes
  - purchase no terminal
- Una respuesta del proveedor marcada `verified` se revalida contra el snapshot
  durable de chain, token, destino, monto, confirmaciones, tx hash y log index.
- Una compra vencida con pago verificable pasa a `under_review`; no acredita
  automaticamente.
- Response:
  - purchase id
  - status
  - verification_status
  - confirmations
  - mensaje seguro
- Audit legacy/manual:
  - onchain_tx_hash_submitted
  - evento de fallo/review segun resultado
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

- Compatibilidad legacy; la App Negocio no usa esta ruta para negocios aprobados.
- La entrada canonica es `referral_code` en Telegram Business Intake.
- Un negocio aprobado recibe `409 REFERRAL_NOT_ALLOWED`.

Referral qualification:

- Admin approval of the referred business awards the referrer up to 5 credits.
- The referred business receives 0 referral credits.
- Total referral credits per referrer cannot exceed 20.
- Credit purchases never qualify or duplicate referral bonuses.
- Event, wallet, ledger and `referral_credits_earned` update exact-once in the
  PostgreSQL approval transaction.
- A legacy `pending` referral event is finalized by Admin approval when eligible;
  terminal `rewarded` or `rejected` events are never reopened or credited again.

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
- Response de lista liviana:
  - id
  - business_id
  - package_code
  - credits_amount
  - price_usd
  - payment_method
  - status
  - verification_status opcional
  - has_reported_tx
  - created_at
  - updated_at
  - next_cursor
- El listado no incluye ledger, proof metadata, direcciones, hashes completos ni
  metadata on-chain amplia.
- El listado devuelve una sola pagina; default 20 y maximo 50.
- El detalle y la reconciliacion no se precargan.

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
- Aplica a:
  - compra manual en `pending_manual_review`
  - compra `base_usdc_onchain` en `under_review`
- Escribe `credit_purchases.status = rejected`.
- No acredita creditos.
- Audit:
  - `manual_credit_payment_rejected` para compra manual
  - `onchain_credit_purchase_rejected` para compra on-chain
- Prohibe support.
- Es la unica ruta Admin oficial para rechazo/revision manual de compras de
  creditos. No existe un endpoint separado de rechazo on-chain en este contrato.

### GET /api/v1/admin/credit-purchases/{id}

- Auth: admin/super_admin; support read-only enmascarado si contrato admin lo permite.
- Se carga solo cuando Admin abre `Detalle`; no se precarga desde el listado y no
  agrega polling.
- Response:
  - `purchase`: detalle operativo de la compra
  - `onchain_evidence`: metadata segura si `payment_method` es
    `base_usdc_onchain` o `base_usdc_contract`
  - `ledger`: movimiento relacionado por `related_credit_purchase_id`, o null
  - `reconciliation`: estado y warnings calculados por backend
- `onchain_evidence` puede incluir:
  - chain_id
  - network
  - token_symbol
  - expected_amount_units
  - tx_amount_units
  - destination_wallet_masked
  - payer_wallet_masked
  - payment_contract_masked
  - payment_contract_version
  - purchase_ref_masked
  - tx_hash_masked
  - tx_from_address_masked
  - tx_to_address_masked
  - tx_block_number
  - tx_log_index
  - confirmations
  - verification_status
  - detected_at
  - verified_at
  - credited_at
  - expires_at
  - comparaciones booleanas de pagador, destino y monto calculadas por backend,
    sin exponer direcciones completas
- Para `base_usdc_contract`, el detalle reutiliza el snapshot y la evidencia
  persistida por el watcher. El endpoint Admin no consulta la blockchain.
- `ledger` puede incluir:
  - id
  - type
  - amount
  - balance_available_before
  - balance_available_after
  - balance_blocked_before
  - balance_blocked_after
  - balance_consumed_before
  - balance_consumed_after
  - reason
  - source
  - reference_type
  - reference_id
  - related_credit_purchase_id
  - created_at
- `reconciliation.state` usa valores de lectura Admin:
  - matched
  - pending
  - warning
  - failed
- `reconciliation.warning_codes` es una lista de codigos operativos neutrales.
- Una compra acreditada sin ledger relacionado debe usar state `warning` y warning
  `CREDITED_WITHOUT_LEDGER`. Esto no muta compra, wallet ni ledger.
- `under_review`, `verification_failed` y `expired` deben producir un estado
  operacional claro sin acreditar ni reintentar desde el endpoint de lectura.
- No expone RPC keys, raw provider responses, private keys, seed phrases ni signed URLs persistidas.
- No expone hashes, wallets ni direcciones completas. Una revelacion futura exige
  otro contrato con razon obligatoria y auditoria.

## Admin credit reconciliation cost policy

- Entrar a Admin no carga compras de creditos.
- Entrar a `Creditos` carga solo la primera pagina del filtro seleccionado.
- `Cargar mas` usa `next_cursor`, conserva filtros y evita duplicados.
- El detalle, la evidencia on-chain, el ledger relacionado y la reconciliacion se
  cargan solo por accion explicita `Detalle`.
- No se agrega polling para compras, evidencia, ledger ni reconciliacion.
- El ledger general usa limite 1..50 y debe paginar con cursor estable
  `(created_at, id)`.
- La relacion compra-ledger usa `related_credit_purchase_id` y una consulta acotada;
  no recorre el ledger completo.

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
- ONCHAIN_WRONG_CHAIN
- ONCHAIN_TOKEN_NOT_ALLOWED
- ONCHAIN_WRONG_TOKEN_OR_WALLET
- ONCHAIN_TX_NOT_FOUND
- ONCHAIN_TX_ALREADY_USED
- ONCHAIN_TX_INVALID
- ONCHAIN_PURCHASE_EXPIRED
- PURCHASE_STATUS_INVALID
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
- No private keys ni seed phrases de treasury/owner para topups on-chain.
- El signer 52C es secreto operacional separado: no frontend, no repo, no logs,
  no audit metadata y no respuestas API. Produccion no debe usar una private key
  plana en Railway/env como custodia final.
- No `storage_path` en API/frontend/logs/audit.
- Comprobantes manuales solo en storage privado y signed URL corta para admin.
- Admin actions requieren reason.
- Permission errors no filtran existencia privada.

## 52C2C Wallet Handoff

### POST /api/v1/business/credits/handoffs

- Auth: negocio owner activo con terminos y PIN operativo desbloqueado.
- Body estricto: `{ "package_code": "starter|pro|business|enterprise" }`.
- Crea una capacidad efimera de cinco minutos; no crea credito, ledger,
  movimiento de saldo ni transaccion blockchain.
- Backend liga el handoff a usuario, negocio y paquete derivados de la sesion.
  Rechaza `business_id`, wallet, monto, precio, token, red y contrato enviados
  por cliente.
- Responde una vez con `handoff.id`, token opaco, `expires_at` y el perfil
  publico `network`, `chain_id`, `network_display_name`, `is_testnet`. El token viaja
  a `/business/credit-payment` solo en fragment URL y backend persiste solo su
  SHA-256 en store efimero.
- Rate limit por usuario, negocio e IP. Redis compartido es obligatorio en
  staging/produccion y el flujo falla cerrado si no esta disponible.

### POST /api/v1/business/credits/handoffs/challenge

- Publico por capacidad efimera; sin JWT, cookie, PIN ni Telegram `initData`.
- Body: `{ "handoff_token": "opaque" }`.
- Devuelve challenge legible, expiracion y el mismo perfil de red ligado al
  handoff. Para 52C2D-S0: `network = base_sepolia`, `chain_id = 84532` e
  `is_testnet = true`.
- Solo un handoff activo y no vencido puede obtener challenge.
- Rate limit por IP y hash de handoff; respuesta `private, no-store`.

### POST /api/v1/business/credits/handoffs/claim

- Body estricto: `handoff_token`, `wallet_address`, `chain_id`, `signature`.
- Requiere el `chain_id` exacto ligado al handoff y recupera el signer EIP-191 de `personal_sign` sobre el
  challenge exacto emitido por backend.
- Si la configuracion cambia entre create/challenge/claim o mezcla perfil de
  mainnet y testnet, falla cerrado sin firma contractual, compra, ledger ni saldo.
- Revalida usuario, negocio, vinculo owner y PIN antes de preparar la compra.
- Claim atomico y replay identico son idempotentes; otro signer o handoff
  vencido/usado falla neutralmente.
- Reutiliza `base_usdc_contract` con idempotencia interna. Solo crea
  compra/autorizacion: no acredita, no crea ledger, no hace `approve`, no hace
  `pay`, no acepta `tx_hash` y no mueve fondos.
- Al quedar `prepared`, devuelve tambien `purchase` y `payment` con el snapshot
  contractual pagable. La respuesta no incluye sesion Telegram, token de
  handoff, secretos ni autoridad elegida por frontend.
- En modo `base_sepolia`, la pagina MetaMask puede usar ese snapshot para leer
  allowance bajo demanda, solicitar `approve` por el monto exacto y llamar
  `pay`. Estas acciones ocurren en la wallet; el claim por si solo no las
  ejecuta.

### GET /api/v1/business/credits/handoffs/{handoff_id}

- Auth: mismo negocio owner activo.
- Recuperacion manual desde Telegram; no polling.
- Devuelve `active|claiming|prepared|expired`, wallet enmascarada y, solo al
  quedar preparado, el detalle contractual de la compra propia. Tambien devuelve
  el perfil publico de red ligado al handoff.
- Puede recordarse el `handoff_id`; el token nunca se persiste en storage web.

## 52C2F-S1 Pago Testnet En MetaMask

- Solo habilitado por la UI cuando el snapshot backend declara
  `network = base_sepolia`, `chain_id = 84532`, `is_testnet = true`,
  `authorization_status = valid` y `capabilities.can_pay = true`.
- La wallet conectada debe coincidir con `payer_wallet_address`; cualquier
  cambio de cuenta o red elimina el snapshot pagable de memoria.
- La lectura de allowance es una llamada puntual `eth_call`, iniciada al
  preparar la compra. No hay polling ni timers.
- Si falta allowance, la UI solicita `approve(vault, expected_amount_units)`.
  Nunca solicita allowance ilimitado.
- `pay` usa exclusivamente `purchase_ref`, payer, amount, validUntil, chainId,
  verifyingContract, contractVersion y firma devueltos por backend.
- `now >= validUntil` bloquea `approve` y `pay`.
- La UI no acepta ni envia `tx_hash`. Enviar la transaccion no acredita; solo el
  watcher contractual puede verificar el evento y acreditar exact-once.
- Telegram conserva carga manual mediante `Actualizar`; no consulta blockchain
  ni necesita provider de wallet.
