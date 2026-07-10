# BUILDER_REPORT - slice_18_remote_marketplace_latency_profiling

## Estado final
READY_FOR_OWNER_REVIEW

## Resumen
Se construyo profiling seguro y opt-in para `GET /api/v1/ads/search`, acotado a staging. El endpoint solo devuelve `_profile` cuando se cumplen simultaneamente:

- `APP_ENV=staging`
- `ENABLE_STAGING_PROFILING=1`
- Header `X-NODO-Profile: 1`

En produccion no se devuelve `_profile`. No se cambiaron reglas de negocio, frontend de producto, schema DB, workers ni pool.

## Archivos modificados
- `apps/api/app/shared/profiling.py`
- `apps/api/app/auth/dependencies.py`
- `apps/api/app/shared/cache.py`
- `apps/api/app/shared/db/connection.py`
- `apps/api/app/modules/ads/routes.py`
- `apps/api/app/modules/ads/marketplace.py`
- `apps/api/app/modules/ads/postgres_repository.py`
- `apps/api/app/modules/ads/profiling.py`
- `apps/api/app/main.py`
- `scripts/capacity_real.py`
- `apps/api/tests/test_ads_marketplace.py`
- `apps/api/tests/test_staging_validation_tooling.py`

## Que construí
- Helper compartido de profiling con contextvar por request y sanitizacion de metadata.
- Gate seguro de staging para `_profile` en `GET /api/v1/ads/search`.
- Instrumentacion de etapas:
  - auth marketplace lightweight/fallback via dependency profile
  - service access
  - rate limit
  - params validation
  - cache key build
  - cache version lookup/cache local/shared/cache hit/cache set
  - lock wait
  - DB acquire
  - DB query
  - DB row mapping
  - rank
  - payload serialization
  - total route time
- `capacity_real.py --profile-marketplace` para enviar `X-NODO-Profile: 1`, capturar perfiles, limitar raw profiles a 50 y agregar `profile_summary`.
- CORS permite `X-NODO-Profile`, sin activar profiling por si solo.

## Que NO construí
- No hice deploy.
- No cambie reglas de negocio.
- No cambie lifecycle de ordenes, anuncios, creditos, pagos ni disputas.
- No cambie frontend de producto.
- No cambie DB schema.
- No cambie workers, `WEB_CONCURRENCY`, pool DB ni thread limit.
- No declare capacidad 10,000.
- No declare `READY_FOR_REAL_USE`.

## Validaciones ejecutadas
- `PYTHONPATH=apps/api python -m pytest apps\api\tests -q`: 170 passed, 1 warning.
- `python -m ruff check apps\api scripts`: All checks passed.
- `python -m compileall apps\api apps\web\src scripts`: OK.
- `corepack pnpm --filter @nodo/web build`: OK.
- Frontend source/build scan de secretos/datos privados/claims prohibidos: sin matches.
- Scan acotado de archivos tocados: matches limitados a tests/fixtures y SQL de seed/invariantes existente en `capacity_real.py`; no se persisten secretos ni datos privados en `_profile`.

## Riesgos residuales
- No se ejecuto profiling contra staging remoto en esta fase; queda preparado para que owner autorice un run real.
- La latencia real c100 aun debe diagnosticarse con evidencia remota usando `--profile-marketplace`.

## Comando sugerido para staging profiling
```powershell
python scripts\capacity_real.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --scenario marketplace-reads --run-id slice18_marketplace_profile_<timestamp> --businesses 2 --ads-per-business 8 --remitters 20 --marketplace-reads 600 --marketplace-concurrency 100 --remote-base-url https://<staging-api> --fixture-mode db_seed_api_remote --profile-marketplace --output evidence\slice_runs\slice_18_marketplace_profile_c100.json
```

Debe ejecutarse solo con guardrails/env staging reales aprobados y limpieza posterior por `run_id`.

## Confirmaciones
- No deploy.
- No cambios de reglas de negocio.
- No cambios de frontend de producto.
- No cambios de DB schema.
- No cambios de workers/pool.
- No `READY_FOR_REAL_USE`.
