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
- rate limit dedicado: 5 por usuario, 5 por negocio y 20 por IP hasheada cada
  10 minutos;
- la cuarta compra no terminal devuelve
  `409 CRYPTO_PAYMENT_PENDING_LIMIT_REACHED` antes de firmar;
- compras terminales no cuentan y el replay idempotente no agrega cupo;
- staging/produccion devuelve
  `503 CRYPTO_PAYMENT_RATE_LIMIT_UNAVAILABLE` si el limitador compartido falla,
  sin compra, firma, ledger o cambio de saldo;
- Memory y PostgreSQL mantienen paridad; PostgreSQL serializa la creacion por
  negocio para impedir que concurrencia exceda tres compras pendientes.
- `base_sepolia` persiste chain `84532` y USDC de testnet en Memory/PostgreSQL;
- `base_mainnet` conserva chain/token propios y no reutiliza valores testnet;
- perfil ausente o desconocido falla cerrado sin compra, ledger ni saldo;
- handoff, challenge, firma EIP-712 y compra usan el mismo perfil configurado.

## Gates Diferidos Antes De Habilitar El Metodo

- reemision controlada mantiene snapshot y ref;
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
- PostgreSQL 16 desechable con 58 migraciones desde cero, incluida 0058.
- 0058 acepta las tuplas canonicas Base mainnet y Base Sepolia y rechaza toda
  mezcla de chain, network o token, contrato faltante y version invalida.
- 0058 down/up funciona sin compras Sepolia; el down falla de forma controlada
  antes de cambiar constraints cuando existe una compra Sepolia.
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

## 52C2C-S1

- handoff Telegram -> MetaMask usa fragmento, limpia URL y no transporta auth;
- handoff vencido, red incorrecta y firma incorrecta fallan neutralmente;
- otro negocio no recupera el estado del handoff;
- replay identico prepara una compra y claim no crea ledger ni saldo;
- Redis/store o rate limit compartido caido falla cerrado;
- no hay polling, `approve`, `pay`, watcher ni movimiento de fondos;
- smoke Telegram iPhone/Android + MetaMask es obligatorio antes de uso real.

## 52C2D-S0

- UI y probe muestran Base Sepolia y no ofrecen selector de red;
- challenge backend entrega `network`, `chain_id`, nombre e `is_testnet`;
- frontend solo firma si recibe `base_sepolia`, `84532` e `is_testnet = true`;
- cambio de cuenta/red invalida el estado local preparado;
- no hay polling, `approve`, `pay`, watcher, ledger, acreditacion ni fondos.

## 52C2E-S0

- watcher lista compras `base_usdc_contract` pendientes solo con snapshot
  completo;
- `eth_getLogs` usa contrato allowlisted, filtros agrupados de `purchase_ref` y
  lookback acotado;
- evento contractual debe coincidir con receipt, token, treasury, payer,
  amount, chain, version y expiracion;
- receipt debe incluir `Transfer` ERC20 exacto de payer hacia treasury;
- confirmaciones insuficientes dejan la compra pendiente;
- pago contractual detectado despues del vencimiento local se acredita si el
  contrato ya emitio el evento valido;
- amount incorrecto falla sin ledger ni credito;
- PostgreSQL guarda evidencia contractual Base Sepolia y acredita exact-once;
- 0059 acepta evidencia Base mainnet/Sepolia canonica, rechaza mezclas y bloquea
  rollback si ya existe evidencia no-mainnet;
- no hay frontend `pay`, `approve`, polling, testnet real, wallet real ni
  fondos reales.

## 52C Admin Credit Contract Reconciliation

- listado Admin sigue sin ledger, reconciliacion ni evidencia pesada;
- detalle `base_usdc_contract` acreditado devuelve evidencia enmascarada y el
  ledger por `related_credit_purchase_id`;
- hash, pagador, treasury, contrato y `purchase_ref` completos no aparecen en
  el payload Admin;
- compra acreditada sin ledger usa `CREDITED_WITHOUT_LEDGER`;
- `under_review`, `verification_failed` y `expired` conservan diagnostico
  neutral y no mutan estado;
- `base_usdc_onchain` mantiene su contrato anterior.
