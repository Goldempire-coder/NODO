# BUILDER_REPORT - slice_27A_base_usdc_cost_hardening

## Estado final

READY_FOR_OWNER_REVIEW

## Objetivo

Reducir costo operativo evitable del flujo Base USDC sin cambiar precios, reglas de credito, acreditacion exact-once, UI, infraestructura ni deploy.

## Cambios realizados

- `apps/api/app/modules/credits/onchain.py`
  - `JsonRpcBaseUsdcVerifier` ahora cachea `eth_chainId` por instancia.
  - Agrega `latest_block_number()` para que jobs puedan leer `eth_blockNumber` una vez y reutilizarlo.
  - Agrega `rpc_call_count` para medir llamadas RPC por corrida.
  - `verify(...)` acepta `latest_block_number` opcional.

- `apps/api/app/modules/credits/watcher.py`
  - Filtra compras elegibles antes de verificar.
  - Reutiliza `latest_block_number` por corrida cuando el verifier lo soporta.
  - Devuelve contadores: `eligible`, `skipped_missing_tx`, `verified_attempts`, `rpc_calls`, `latest_block_prefetched`.

- `apps/api/app/modules/credits/postgres_onchain.py`
  - `list_onchain_pending_purchases_pg` ahora trae solo compras on-chain con `tx_hash`, `expected_amount_units` y `destination_wallet_address`.

- `apps/api/app/modules/credits/memory_purchases.py`
  - Alinea el filtro in-memory del watcher con Postgres.

- `apps/api/tests/test_credits_referrals.py`
  - Prueba que `eth_chainId` se cachea y `eth_blockNumber` se reutiliza.
  - Prueba que el watcher solo escanea compras listas para verificar y reporta contadores de costo.

## Impacto esperado

- Antes: cada verificacion podia llamar `eth_chainId`, `eth_getTransactionReceipt` y `eth_blockNumber`.
- Despues:
  - `eth_chainId` se reutiliza por instancia.
  - El watcher puede hacer un solo `eth_blockNumber` por lote.
  - Cada compra elegible normalmente requiere solo `eth_getTransactionReceipt`.
  - Compras sin `tx_hash` ya no consumen espacio del batch del watcher.

## Que NO cambie

- No cambie precios ni paquetes.
- No cambie acreditacion de creditos.
- No cambie ledger/audit exact-once.
- No cambie frontend.
- No cambie migraciones.
- No cambie infraestructura.
- No hice deploy.
- No ejecute servicios reales.
- No declare READY_FOR_REAL_USE.

## Validaciones

- `python -m pytest apps\api\tests\test_credits_referrals.py -q --tb=short`: 17 passed, 1 warning.
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 247 passed, 1 warning.
- `python -m ruff check apps\api scripts`: All checks passed.
- `python -m compileall apps\api apps\web\src scripts`: OK.
- `corepack pnpm --filter @nodo/web build`: OK.

## Riesgos residuales

- No se corrio watcher contra Base mainnet real en staging.
- Falta medir costo real del proveedor RPC con billing/export del proveedor.
- Si se corren muchos workers del watcher sin coordinacion externa, cada proceso podria tener su propio cache de `chainId`; esto reduce llamadas por proceso, no entre procesos.
