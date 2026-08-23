# QA.md

## Pruebas 52C1

- body con `amount` devuelve `422`, sin compra ni firma;
- body con token/chain/treasury/contract/version/expiry/ref devuelve `422`;
- body legacy devuelve `422` cuando existe configuracion contractual, incluso
  si el flag legacy esta activo o inactivo;
- body legacy conserva compatibilidad solo sin configuracion 52C y con flag
  legacy activo;
- backend deriva `business_id` desde sesion, no desde body;
- negocio bloqueado, no aprobado o sin access link activo no crea compra;
- paquete invalido devuelve `422 VALIDATION_ERROR`;
- monto oficial se calcula desde catalogo, sin float;
- `payer_wallet_address` debe ser EVM valido y normalizado;
- `purchase_ref` es bytes32 aleatorio y unique;
- replay idempotente devuelve misma compra/ref/firma;
- misma idempotency key con payload distinto falla;
- signer ausente falla cerrado y no crea compra pagable;
- contrato pausado/configuracion divergente falla cerrado;
- firma no acredita wallet ni ledger;
- expiracion estricta: `now >= validUntil` no es pagable;
- rate limit backend existente por accion y negocio.

## Gates Diferidos Antes De Habilitar El Metodo

- reemision controlada mantiene snapshot y ref;
- 5 creaciones/reemisiones por usuario y por negocio cada 10 minutos;
- 20 creaciones/reemisiones por IP hasheada cada 10 minutos;
- maximo 3 compras contractuales no terminales por negocio;
- fallo cerrado si el limitador compartido no esta disponible en
  staging/produccion;
- detalle propio reanuda una autorizacion vigente sin firmar de nuevo;
- autorizacion vencida o signer/config divergente no devuelve firma pagable;
- `tx-hash` sobre `base_usdc_contract` devuelve
  `CRYPTO_PAYMENT_TX_HASH_NOT_ACCEPTED` sin persistir ni acreditar;
- frontend normal no contiene wallet directa ni campo de `tx_hash`.

## Pruebas 52C2

- App Negocio envia solo `package_code` y `payer_wallet_address`;
- recargar reanuda la misma compra/ref/firma vigente bajo demanda;
- reanudacion no agrega polling;
- limites por usuario, negocio, IP y compras pendientes se aplican en backend;
- Redis/limitador caido falla cerrado para crear/reemitir;
- evento de contrato falso no acredita;
- evento sin `NodoCreditPaymentReceived` no acredita;
- Transfer directo a wallet no auto-acredita;
- purchase_ref incorrecto no acredita;
- payer incorrecto no acredita;
- amount incorrecto no acredita;
- token incorrecto no acredita;
- treasury incorrecto no acredita;
- chain incorrecta no acredita;
- contrato/version incorrectos no acreditan;
- confirmaciones insuficientes no acreditan;
- evento duplicado no duplica ledger;
- concurrencia PostgreSQL acredita una sola vez.
- transferencia directa y hash publico solo pueden ir a fallback manual y nunca
  auto-acreditan con trafico real controlado.

## Validacion

- Pytest dirigido creditos/signature.
- PostgreSQL desechable con migracion 0057 desde cero.
- PostgreSQL concurrencia exact-once.
- 0057 down/up funciona sin compras contractuales.
- 0057 down falla de forma explicita antes de mutar si existen compras
  `base_usdc_contract`.
- Ruff.
- Compileall.
- Next build cuando 52C2 toque frontend.
- `git diff --check`.
- Secret Guard.
- Smoke testnet/staging solo con aprobacion Owner, wallet temporal y monto
  pequeno.

## No Evidencia Suficiente

No declarar `READY_FOR_REAL_USE` hasta tener:

- contrato deployado/verificado en testnet;
- backend signer validado sin secretos impresos;
- watcher validado contra eventos reales;
- exact-once PostgreSQL;
- alertas Admin;
- rollback;
- aprobacion Owner para treasury/signer/owner.
