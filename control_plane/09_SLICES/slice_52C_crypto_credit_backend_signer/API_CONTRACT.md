# API_CONTRACT.md

## Endpoint Canonico

52C reutiliza el endpoint existente para evitar duplicar superficies:

```txt
POST /api/v1/business/credits/base-payment
```

`base_usdc_contract` es el unico flujo normal futuro de la App Negocio. El
metodo `base_usdc_onchain` queda deprecado para uso normal y limitado a
local/staging o fallback manual/Admin sin auto-credito real.

## Body Permitido Para Flujo Contractual

```json
{
  "package_code": "starter",
  "payer_wallet_address": "0x..."
}
```

`Idempotency-Key` es obligatorio.

El backend deriva `business_id` desde la sesion autenticada. El frontend no debe
enviar `business_id`.

## Campos Prohibidos En Body

Si aparecen, el backend debe rechazar con `422 VALIDATION_ERROR` y no crear
compra ni firma:

- `amount`
- `price`
- `credits_amount`
- `token`
- `token_symbol`
- `token_contract_address`
- `chain_id`
- `network`
- `treasury`
- `destination_wallet_address`
- `contract_address`
- `contract_version`
- `valid_until`
- `expires_at`
- `purchase_ref`
- `authorization`
- `signature`

## Decisiones Backend

El backend decide exclusivamente:

- negocio real desde sesion;
- paquete valido desde catalogo;
- creditos del paquete;
- precio oficial;
- token oficial;
- chain oficial;
- contrato allowlisted;
- treasury immutable esperada por contrato;
- version contractual;
- expiracion;
- purchase ref;
- digest EIP-712;
- signer version.

## Response Exitosa

La respuesta puede incluir:

- `purchase.id`
- `status`
- `payment_method = base_usdc_contract`
- `package_code`
- `credits_amount`
- `price_usd`
- `network`
- `chain_id`
- `token_symbol`
- `token_contract_address`
- `token_decimals`
- `expected_amount_units`
- `expected_amount_display`
- `contract_address`
- `contract_version`
- `purchase_ref`
- `payer_wallet_address`
- `authorization_valid_until`
- `authorization_typed_data`
- `authorization_signature`
- `min_confirmations`
- `disclaimer`

No devuelve private keys, raw signer payloads internos, RPC keys, provider raw
responses ni datos de auditoria sensibles.

## Reanudacion Tras Recarga

```txt
GET /api/v1/business/credits/purchases/{purchase_id}
```

- Auth: business_owner activo.
- Scope: compra propia.
- `Cache-Control: private, no-store`.
- No firma, no reemite, no acredita y no consulta blockchain.
- Si la autorizacion durable sigue vigente y signer/configuracion coinciden,
  devuelve el snapshot contractual y la firma original con
  `authorization_status = valid`.
- La respuesta `payment` incluye solo lo necesario para continuar: network,
  chain, token, monto, contrato/version, purchase_ref, payer,
  authorization_valid_until, typed data y signature.
- Si la autorizacion vencio, devuelve `authorization_status = expired` y
  `capabilities.can_pay = false`, sin firma pagable.
- Si signer, contrato o version cambiaron, devuelve
  `authorization_status = reissue_required`, sin firma pagable.
- La reemision futura es una mutacion separada con idempotencia, rate limit y
  audit; nunca ocurre como efecto lateral del GET.
- La UI carga este detalle solo al abrir/continuar una compra o por refresh
  manual. No agrega polling.

## Politica De Tx Hash

```txt
POST /api/v1/business/credits/purchases/{purchase_id}/tx-hash
```

- No forma parte del flujo normal contractual y la UI 52C no lo muestra.
- Para `base_usdc_contract` devuelve
  `409 CRYPTO_PAYMENT_TX_HASH_NOT_ACCEPTED`.
- No guarda el hash, no cambia estado, no crea ledger y no acredita.
- El watcher 52C2 debe encontrar el evento oficial del contrato por
  `purchase_ref`; una transferencia directa o un hash publico nunca es
  autoridad de auto-credito.
- La ruta solo puede permanecer para `base_usdc_onchain` legacy local/staging o
  revision manual/Admin.

## Idempotencia

Misma `Idempotency-Key` + mismo payload permitido + mismo negocio:

- devuelve la misma compra;
- devuelve el mismo `purchase_ref`;
- devuelve la misma autorizacion/firma si sigue vigente y signer no roto.

Misma `Idempotency-Key` con payload distinto:

- `409 IDEMPOTENCY_PAYLOAD_MISMATCH`;
- no crea compra nueva;
- no firma.

## Errores Nuevos O Reusados

- `CRYPTO_CONTRACT_PAYMENT_NOT_CONFIGURED`
- `CRYPTO_PAYMENT_SIGNER_UNAVAILABLE`
- `CRYPTO_PAYMENT_CONTRACT_PAUSED`
- `CRYPTO_PAYMENT_PURCHASE_EXPIRED`
- `CRYPTO_PAYMENT_AUTHORIZATION_EXPIRED`
- `CRYPTO_PAYMENT_AUTHORIZATION_REISSUE_REQUIRED`
- `CRYPTO_PAYMENT_TX_HASH_NOT_ACCEPTED`
- `CRYPTO_PAYMENT_PENDING_LIMIT_REACHED`
- `CRYPTO_PAYMENT_RATE_LIMIT_UNAVAILABLE`
- `ONCHAIN_PAYMENT_NOT_CONTRACT_BOUND`
- `ONCHAIN_PAYMENT_REF_MISMATCH`
- `ONCHAIN_PAYMENT_PAYER_MISMATCH`
- `ONCHAIN_PAYMENT_CONTRACT_NOT_ALLOWED`
- `ONCHAIN_PAYMENT_TOKEN_NOT_ALLOWED`
- `ONCHAIN_PAYMENT_TREASURY_MISMATCH`

Los errores publicos deben ser neutrales y no incluir wallets completas,
signature, digest completo, RPC response, stack trace o claves. La signature
publica solo aparece en una respuesta contractual exitosa y privada
`Cache-Control: private, no-store`; nunca se registra en logs.

## Reemision Controlada

Una autorizacion puede reemitirse solo si:

- la compra sigue pendiente;
- no existe pago acreditado ni evento usado;
- el snapshot comercial no cambia;
- el signer actual es diferente o la firma anterior expiro;
- hay idempotencia y audit.

No se genera `purchase_ref` nuevo para la misma compra salvo que la compra
anterior quede expirada/cerrada y se cree otra intencion.

## Limites Antiabuso Obligatorios

Antes de habilitar 52C fuera de pruebas:

- crear/reemitir: 5 requests por usuario y 5 por negocio cada 10 minutos;
- respaldo: 20 requests por IP hasheada cada 10 minutos;
- maximo 3 compras contractuales no terminales por negocio, contando
  `pending_payment`, `pending_onchain_confirmation`, `detected` y
  `under_review`;
- replay de la misma `Idempotency-Key` devuelve la misma compra y no consume
  otro cupo pendiente;
- limite temporal excedido: `429 RATE_LIMITED`;
- cupo pendiente excedido: `409 CRYPTO_PAYMENT_PENDING_LIMIT_REACHED`;
- limitador compartido no disponible en staging/produccion:
  `503 CRYPTO_PAYMENT_RATE_LIMIT_UNAVAILABLE` y no se firma;
- no se registran IP, signer key, typed data completo ni firma completa en logs
  o audit metadata.
