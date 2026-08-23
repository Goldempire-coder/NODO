# API_CONTRACT.md

## Objetivo

Actualizar el flujo on-chain para que el backend devuelva datos de pago por
contrato, no solo una wallet destino.

## Metodo De Pago Nuevo

Nombre de trabajo:

```txt
base_usdc_contract
```

Decision 52C: `base_usdc_contract` es el flujo recomendado para fondos reales.
`base_usdc_onchain` directo a wallet queda legacy/fallback manual o staging
hasta retiro gobernado. No deben acreditarse ambos caminos para la misma compra.

Autoridad: para la API business, `control_plane/06_API_CONTRACTS/CREDITS_API.md`
y el API contract de 52C son normativos. Este documento define la integracion
con el contrato y no habilita por si solo ningun flujo runtime.

## POST /api/v1/business/credits/base-payment

Input legacy/directo, solo compatibilidad local/staging o manual gobernada:

- `package_code`
- `token_symbol = USDC`
- `Idempotency-Key`

Input contractual 52C:

- `package_code`
- `payer_wallet_address`
- `Idempotency-Key`

El frontend no envia `token_symbol` en 52C. Token, red, contrato, treasury,
monto, version, expiracion y ref son decisiones backend.

La App Negocio normal usa exclusivamente el input contractual. No muestra
wallet directa ni permite pegar `tx_hash`.

`payer_wallet_address` debe venir de la wallet conectada por el negocio. El
backend valida formato EVM, normaliza lowercase y firma solo ese payer. El
frontend no puede imponer red, token, contrato, treasury, monto ni expiracion.

Output nuevo en `payment`:

- `network`
- `chain_id`
- `token_symbol`
- `token_contract_address`
- `token_decimals`
- `expected_amount_units`
- `expected_amount_display`
- `contract_address`
- `purchase_ref`
- `contract_version`
- `payment_authorization`
- `authorization_signature`
- `authorization_typed_data`
- `min_confirmations`
- `expires_at`

Output removido o legacy:

- `destination_wallet_address` no debe ser la instruccion principal cuando el
  metodo por contrato este activo.

## POST /api/v1/business/credits/purchases/{purchase_id}/tx-hash

Esta ruta no acepta evidencia para compras `base_usdc_contract`. Debe responder:

```txt
409 CRYPTO_PAYMENT_TX_HASH_NOT_ACCEPTED
```

La respuesta no guarda el hash, no cambia estado, no acredita y no crea ledger.
El watcher contractual encuentra el evento oficial por `purchase_ref`; el
frontend normal no pide `tx_hash`.

Para una compra legacy `base_usdc_onchain`, el hash puede conservarse solo como
entrada local/staging o ayuda manual/Admin. Antes de registrar una revision, el
verifier debe buscar:

- receipt exitoso;
- chain y token iguales al snapshot legacy;
- destino igual al snapshot backend de la compra;
- monto suficiente segun el snapshot, salvo politica explicita de revision
  manual;
- confirmaciones minimas;
- tx/log no usado antes.
- log ERC20 `Transfer` del token oficial hacia el destino esperado.

La ausencia del evento `NodoCreditPaymentReceived` y del `purchase_ref` ligado
a la compra demuestra que la transferencia directa no pertenece al flujo
contractual. Nunca auto-acredita. Puede responder error seguro o dejar el caso
`under_review` para revision Admin explicita:

```txt
ONCHAIN_PAYMENT_NOT_CONTRACT_BOUND
```

Un hash publico no prueba propiedad ni intencion comercial.

## GET /api/v1/business/credits/purchases/{purchase_id}

Es la lectura de reanudacion de una compra contractual propia:

- no firma, no reemite y no consulta blockchain;
- si la autorizacion durable sigue vigente, devuelve el snapshot contractual,
  typed data y firma originales con `authorization_status = valid`;
- si vencio o signer/configuracion divergen, devuelve
  `authorization_status = expired | reissue_required`, sin firma pagable;
- usa `Cache-Control: private, no-store`;
- se carga solo al abrir/continuar la compra o por refresh manual, sin polling.

## Watcher

Job nuevo de trabajo:

```txt
verify_base_usdc_contract_credit_purchases
```

Debe consultar eventos del contrato oficial y no barrer transferencias ERC20
genericas hacia la wallet.

## Datos Nuevos

Agregar o reutilizar campos segun el modelo actual:

- `credit_purchases.onchain_purchase_ref`
- `credit_purchases.onchain_payer_address`
- `credit_purchases.payment_contract_address`
- `credit_purchases.payment_contract_version`
- `credit_purchases.payment_authorization_expires_at`
- `credit_purchase_onchain_payments.payment_contract_address`
- `credit_purchase_onchain_payments.purchase_ref`
- `credit_purchase_onchain_payments.payer_address`
- identidad canonica del evento: `chain_id + tx_hash + tx_log_index`

Todos normalizados:

- direcciones EVM en lowercase;
- tx hash lowercase;
- `purchase_ref` como bytes32 hex canonical `0x` + 64 hex.

## Errores Nuevos

- `CRYPTO_PAYMENT_TX_HASH_NOT_ACCEPTED`
- `CRYPTO_PAYMENT_PENDING_LIMIT_REACHED`
- `CRYPTO_PAYMENT_RATE_LIMIT_UNAVAILABLE`
- `ONCHAIN_PAYMENT_NOT_CONTRACT_BOUND`
- `ONCHAIN_PAYMENT_REF_MISMATCH`
- `ONCHAIN_PAYMENT_PAYER_MISMATCH`
- `ONCHAIN_PAYMENT_CONTRACT_NOT_ALLOWED`
- `ONCHAIN_PAYMENT_TOKEN_NOT_ALLOWED`
- `ONCHAIN_PAYMENT_TREASURY_MISMATCH`
- `ONCHAIN_PURCHASE_REF_ALREADY_USED`
- `ONCHAIN_PAYMENT_AUTHORIZATION_EXPIRED`
- `ONCHAIN_PAYMENT_SIGNATURE_INVALID`

Mensajes publicos: neutrales, sin raw RPC response, sin stack trace, sin
wallet completa y sin tx hash completo.

## Audit Events

- `onchain_contract_purchase_created`
- `onchain_contract_authorization_signed`
- `onchain_contract_payment_detected`
- `onchain_contract_payment_verified`
- `onchain_contract_payment_credited`
- `onchain_contract_payment_rejected`
- `onchain_contract_payment_under_review`
- `onchain_contract_payment_verification_failed`
- `onchain_contract_configuration_invalid`

## Compatibilidad Legacy

Decision cerrada:

- `base_usdc_contract` es el unico flujo normal futuro;
- `base_usdc_onchain` directo queda solo local/staging o fallback manual/Admin;
- una transferencia directa nunca auto-acredita con trafico real controlado;
- el frontend normal no crea compras directas ni solicita hashes;
- retirar definitivamente el legacy requiere confirmar cero consumidores y
  resolver compras pendientes en un slice de deprecacion posterior.

El endpoint de tx hash puede permanecer para el metodo legacy, pero el hash no
es prueba de propiedad ni autoridad de acreditacion. Sin evento del contrato
oficial y `purchase_ref` esperado, solo puede crear un caso manual
`under_review`; nunca auto-credito.

## Error De Fuente De Token

No se crea metodo BSC ni enum de token hasta confirmar direccion por fuente
oficial del emisor. La falta de fuente es un gate de diseno, no un error runtime.
