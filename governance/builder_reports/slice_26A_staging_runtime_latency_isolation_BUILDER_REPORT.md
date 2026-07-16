# slice_26A_staging_runtime_latency_isolation_BUILDER_REPORT

## Estado final

`BLOCKED_BY_STAGING_ENV_OR_AUTHORIZATION`

El tooling quedó construido y validado localmente. No se ejecutó staging real porque esta fase no recibió autorización/env real explícita para correr carga contra servicios remotos.

## Qué construí

- Extendí `scripts/capacity_real.py` para aislar latencia de marketplace por request.
- Captura ahora:
  - `external_duration_ms`
  - `X-NODO-Process-Time-Ms`
  - `Server-Timing`
  - `X-Request-Id`
  - `X-Correlation-Id`
  - status
  - response size
  - `_profile` cuando se usa `--profile-marketplace`
- Agregué resumen `latency_isolation` con:
  - external p50/p95/p99
  - backend process p50/p95/p99
  - delta `external_minus_backend`
  - server timing p50/p95/p99
  - response size p50/p95/p99
  - profile summary existente
- Agregué `--auth-mode fresh-claims|fallback-db`.
- En modo remoto, `capacity_real.py` ahora exige `staging_guardrails.py` antes de inicializar fixture/app local.

## Qué NO construí

- No hice deploy.
- No subí workers.
- No cambié pool DB.
- No cambié Railway/Supabase/Upstash.
- No agregué réplicas.
- No optimicé queries.
- No cambié reglas de negocio.
- No toqué lifecycles de órdenes, créditos, ads, soporte ni disputas.
- No ejecuté staging real.
- No declaré `READY_FOR_REAL_USE`.

## Archivos modificados

- `scripts/capacity_real.py`
- `apps/api/tests/test_staging_validation_tooling.py`

## Comandos staging preparados

```powershell
python scripts\capacity_real.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --run-id slice26a_c20_<timestamp> --scenario marketplace-reads --businesses 8 --ads-per-business 4 --remitters 120 --marketplace-reads 200 --marketplace-concurrency 20 --remote-base-url https://nodo-api-production.up.railway.app --fixture-mode db_seed_api_remote --auth-mode fresh-claims --profile-marketplace --output evidence\slice_runs\slice_26A_marketplace_latency_c20.json
python scripts\capacity_real.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --run-id slice26a_c50_<timestamp> --scenario marketplace-reads --businesses 8 --ads-per-business 4 --remitters 120 --marketplace-reads 400 --marketplace-concurrency 50 --remote-base-url https://nodo-api-production.up.railway.app --fixture-mode db_seed_api_remote --auth-mode fresh-claims --profile-marketplace --output evidence\slice_runs\slice_26A_marketplace_latency_c50.json
python scripts\capacity_real.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --run-id slice26a_c100_<timestamp> --scenario marketplace-reads --businesses 8 --ads-per-business 4 --remitters 120 --marketplace-reads 600 --marketplace-concurrency 100 --remote-base-url https://nodo-api-production.up.railway.app --fixture-mode db_seed_api_remote --auth-mode fresh-claims --profile-marketplace --output evidence\slice_runs\slice_26A_marketplace_latency_c100.json
```

Para comparar fallback DB:

```powershell
python scripts\capacity_real.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --run-id slice26a_c50_fallback_<timestamp> --scenario marketplace-reads --businesses 8 --ads-per-business 4 --remitters 120 --marketplace-reads 400 --marketplace-concurrency 50 --remote-base-url https://nodo-api-production.up.railway.app --fixture-mode db_seed_api_remote --auth-mode fallback-db --profile-marketplace --output evidence\slice_runs\slice_26A_marketplace_latency_c50_fallback_db.json
```

## Pruebas ejecutadas

- `python -m pytest apps\api\tests\test_staging_validation_tooling.py -q --tb=short`
  - `33 passed, 1 warning`
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`
  - `230 passed, 1 warning`
- `python -m ruff check apps\api scripts`
  - `All checks passed!`
- `python -m compileall apps\api apps\web\src scripts`
  - OK
- `corepack pnpm --filter @nodo/web build`
  - OK

## Riesgos residuales

- Staging real sigue sin medirse en este slice.
- La conclusión final de fuente de latencia requiere ejecutar c20/c50/c100 con env staging real y cleanup posterior.
- El modo `db_seed_api_remote` sigue creando datos sintéticos por DB directa y requiere cleanup por `run_id`.
- `api_remote_only` sigue bloqueado porque el harness todavía necesita seed/invariantes por DB.

## Recomendación siguiente

Ejecutar staging con guardrails, primero `fresh-claims` c20/c50/c100. Si el delta `external_minus_backend` domina, investigar runtime/edge/harness. Si `backend_process` domina, revisar profile stages. Si `auth` domina, comparar con `fallback-db`.
