# BUILDER_REPORT - slice_19_base_usdc_usdt_credit_topups

## Estado final

READY_FOR_OWNER_REVIEW_AFTER_AUDIT_FIX

No se declara READY_FOR_REAL_USE.

## Resumen construido

- Backend de compra de creditos con Base USDC.
- Migracion reversible `0017_slice_19_base_usdc_credit_topups`.
- Endpoint `POST /api/v1/business/credits/base-payment`.
- Endpoint `GET /api/v1/business/credits/purchases/{id}`.
- Endpoint `POST /api/v1/business/credits/purchases/{id}/tx-hash`.
- Admin detail/reject para compras on-chain en `under_review`.
- Verificador Base USDC por JSON-RPC backend-only.
- Watcher interno `verify_base_usdc_credit_purchases`.
- UI negocio para iniciar compra Base USDC, ver estado pending/on-chain, enviar tx hash y consultar ledger/status.

## Owner audit fixes aplicados

- Postgres on-chain verification usa insert atomico `on conflict (chain_id, tx_hash, tx_log_index) do nothing`.
- Si el tx/log ya existe para otra compra, aborta con `ONCHAIN_TX_ALREADY_USED` antes de tocar wallet/ledger.
- El verifier valida `eth_getTransactionReceipt.status == 0x1`; receipt `0x0` o invalido no acredita.
- Constraint de migracion corregida: `tx_amount_units > 0`.
- Audit metadata usa `tx_hash_masked`; no guarda tx hash completo.
- API devuelve `tx_hash_masked`, no `tx_hash` completo.
- UI negocio oculta Stripe/Zelle/USDT manual por defecto; Base USDC queda como flujo visible principal.

## Archivos modificados

- `apps/api/app/core/config.py`
- `apps/api/app/main.py`
- `apps/api/app/modules/credits/admin_actions.py`
- `apps/api/app/modules/credits/business_purchases.py`
- `apps/api/app/modules/credits/memory_purchases.py`
- `apps/api/app/modules/credits/memory_repository.py`
- `apps/api/app/modules/credits/models.py`
- `apps/api/app/modules/credits/onchain.py`
- `apps/api/app/modules/credits/postgres_onchain.py`
- `apps/api/app/modules/credits/postgres_purchase_review.py`
- `apps/api/app/modules/credits/postgres_purchases.py`
- `apps/api/app/modules/credits/postgres_repository.py`
- `apps/api/app/modules/credits/routes.py`
- `apps/api/app/modules/credits/row_mappers.py`
- `apps/api/app/modules/credits/schemas.py`
- `apps/api/app/modules/credits/serializers.py`
- `apps/api/app/modules/credits/service.py`
- `apps/api/app/modules/credits/watcher.py`
- `apps/api/tests/test_credits_referrals.py`
- `apps/web/src/api/credits.ts`
- `apps/web/src/hooks/business-mini-app/helpers.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts`
- `apps/web/src/screens/business-app/BusinessCreditsScreens.tsx`
- `apps/web/src/types/credits.ts`
- `database/migrations/0017_slice_19_base_usdc_credit_topups.up.sql`
- `database/migrations/0017_slice_19_base_usdc_credit_topups.down.sql`
- `governance/builder_reports/slice_19_base_usdc_usdt_credit_topups_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_19_base_usdc_usdt_credit_topups_evidence.md`
- `evidence/slice_runs/slice_19_base_usdc_usdt_credit_topups_test_results.json`

## Migraciones

Creada migracion reversible:

- `database/migrations/0017_slice_19_base_usdc_credit_topups.up.sql`
- `database/migrations/0017_slice_19_base_usdc_credit_topups.down.sql`

Incluye:

- Extension de `credit_purchases` para campos on-chain.
- Nueva tabla `credit_purchase_onchain_payments`.
- `expected_amount_units numeric(78,0)`.
- `tx_amount_units numeric(78,0)`.
- Constraint `tx_amount_units > 0`.
- Indice unico `credit_purchase_onchain_tx_log_unique_idx` por `chain_id, tx_hash, tx_log_index`.
- Checks de Base mainnet, USDC, minor units y normalizacion lower-case de valores EVM.

## Endpoints construidos

- `POST /api/v1/business/credits/base-payment`
- `GET /api/v1/business/credits/purchases/{id}`
- `POST /api/v1/business/credits/purchases/{id}/tx-hash`
- `GET /api/v1/admin/credit-purchases/{id}`
- `POST /api/v1/admin/credit-purchases/{id}/reject` actualizado para `under_review` on-chain

## Reglas preservadas

- Base mainnet only: `chain_id = 8453`.
- USDC nativo Base only: `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913`.
- USDT Base no fue construido.
- No hay signing backend.
- No hay private keys, seed phrases, mnemonics ni signing keys.
- RPC config queda backend-only.
- Ledger/wallet se actualizan una sola vez.
- Referral bonus Base solo se gatilla cuando la compra queda `credited` y hay ledger `purchase`.
- Stripe/manual existentes no se eliminaron, pero quedaron ocultos de la pantalla de compra por defecto.

## Que NO se construyo

- USDT Base.
- Reembolsos automaticos.
- Custodia/escrow/garantia de fondos.
- Signing backend.
- Deploy.
- Cambios a ordenes, anuncios, disputas, pagos de remesas o bots.
- READY_FOR_REAL_USE.

## Validaciones ejecutadas

- `python -m pytest apps\api\tests\test_credits_referrals.py -q --tb=short`: 15 passed, 1 warning.
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 180 passed, 1 warning.
- `python -m ruff check apps\api scripts`: All checks passed.
- `python -m compileall apps\api apps\web\src scripts`: passed.
- `corepack pnpm --filter @nodo/web build`: passed.
- UI source scan for visible legacy fallback controls: no matches.
- Frontend source/build scan for secrets, RPC keys, private keys, seed phrases, `storage_path`, `account_value` and prohibited claims: no matches.
- Source scan for `tx_amount_units >= 0` and unsafe Postgres `do update` on duplicate tx/log path: no matches.
- Source scan for full `tx_hash` in credit audit metadata: no matches.

## Riesgos residuales

- El verificador JSON-RPC requiere configurar `BASE_RPC_URL` y `NODO_CREDIT_RECEIVING_WALLET_BASE` en entorno real antes de operar.
- El watcher quedo como worker interno invocable por runtime/scheduler; no se agrego endpoint admin de job para no ampliar scope.
- No se ejecuto contra Base mainnet ni staging real en este slice.

## Confirmaciones

- No hice deploy.
- No declare READY_FOR_REAL_USE.
- No construi USDT Base.
- No agregue dependencias.
- No guarde ni use private keys/seed phrases.
- No expuse `storage_path`, `account_value`, secretos ni RPC keys en frontend.
