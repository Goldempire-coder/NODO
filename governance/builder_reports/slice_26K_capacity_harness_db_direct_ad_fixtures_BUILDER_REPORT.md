# slice_26K_capacity_harness_db_direct_ad_fixtures - BUILDER REPORT

Estado final: READY_FOR_OWNER_REVIEW

## Objetivo

Reducir el ruido del setup del capacity harness sin tocar producto ni infraestructura. En 26J el load medido ya estaba separado del setup, pero el setup seguia usando APIs de producto para crear anuncios sinteticos. Este slice agrega un modo explicito para crear anuncios por DB directa con el hold de credito correspondiente, de forma que futuras corridas puedan medir carga sin pagar minutos de setup remoto de ads.

## Cambios implementados

- `scripts/capacity_real.py`
  - Agregado `--fixture-setup-mode {api_ads,db_direct_ads}`.
  - Default conservador: `api_ads`.
  - Nuevo camino `db_direct_ads` para insertar anuncios sinteticos por DB directa.
  - El camino DB directo:
    - calcula `required_credits` con la regla real `calculate_required_credits`;
    - bloquea el wallet con `for update`;
    - inserta `ads`;
    - mueve creditos de `available` a `blocked`;
    - inserta `credits_ledger` tipo `hold`;
    - adjunta `credit_hold_ledger_id` al anuncio;
    - registra step sintetico sin secretos;
    - invalida marketplace cache via `marketplace_cache.clear_prefix("")`.
  - El output ahora incluye `fixture_setup_mode` y `fixture_setup`.

- `apps/api/tests/test_staging_validation_tooling.py`
  - Tests para modo invalido.
  - Tests para dispatch DB-direct sin llamada API.
  - Tests para output JSON del modo DB-direct.
  - Ajuste del test existente para el nuevo `fixture_mode_detail.seed`.

## Alcance no tocado

- No modifique backend de producto.
- No modifique frontend.
- No modifique migraciones.
- No cambie reglas de ordenes, pagos, creditos, anuncios, bots, soporte ni staff.
- No cambie Railway, Supabase, Upstash, Cloudflare, pool, workers ni planes.
- No ejecute stress staging con el nuevo modo.
- No declare `READY_FOR_REAL_USE`.

## Archivos principales

- `scripts/capacity_real.py`
  - `fixture_setup_mode`: linea 174
  - resolver: linea 281
  - dispatch ad fixture: linea 393
  - DB direct ads: linea 455
  - invalidacion marketplace: linea 556
  - output JSON: linea 1284
  - CLI flag: linea 1374

- `apps/api/tests/test_staging_validation_tooling.py`
  - tests nuevos: lineas 761, 781, 823

## Validaciones

- `python -m pytest apps\api\tests\test_staging_validation_tooling.py -q --tb=short`
  - Resultado: `48 passed, 1 warning`
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`
  - Resultado: `245 passed, 1 warning`
- `python -m ruff check apps\api scripts`
  - Resultado: `All checks passed!`
- `python -m compileall apps\api scripts`
  - Resultado: OK
- `corepack pnpm --filter @nodo/web build`
  - Resultado: OK
- `python scripts\capacity_real.py --help`
  - Resultado: muestra `--fixture-setup-mode {api_ads,db_direct_ads}`

## Riesgos residuales

- El nuevo modo todavia no fue ejecutado contra staging real.
- `payment_order_setup` sigue usando API de producto; se mantuvo asi para no recrear por DB directa reglas de lifecycle de ordenes/pagos.
- La invalidacion cache depende de que el env del harness apunte al mismo Redis compartido que staging.

## Proximo paso recomendado

Ejecutar una segunda corrida focal si se quiere aislar el setup restante de usuarios/sesiones. No subir infraestructura: 26K redujo setup, pero el p95 de carga medida sigue dominado por `external_minus_backend`.

## Corrida staging posterior

Se ejecuto una corrida staging autorizada con:

```powershell
python scripts\capacity_real.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --scenario all --remote-base-url https://nodo-api-production.up.railway.app --fixture-mode db_seed_api_remote --fixture-setup-mode db_direct_ads --businesses 20 --ads-per-business 4 --remitters 120 --marketplace-reads 250 --marketplace-concurrency 50 --order-creates 25 --same-ad-race-requests 50 --payment-confirms 10 --profile-marketplace --auth-mode fresh-claims --max-connections 50 --run-id slice26k_mixed_c50_dbads_20260711154050 --output evidence\slice_runs\slice26k_mixed_c50_dbads_20260711154050.json
```

Resultado:

- `exit_code: 0`
- `setup_seconds: 330.1347`
- `measured_load_seconds: 238.0388`
- `direct_ads_created: 91`
- `marketplace_cache_invalidated: true`
- `request_error_summary.total: 0`
- `invariant_violations`: todos `0`

Comparacion contra 26J conn50:

- 26J setup: `473.7036s`
- 26K setup: `330.1347s`
- mejora: `143.5689s`
- reduccion: `30.31%`

Cleanup ejecutado:

```powershell
python scripts\staging_cleanup_synthetic_run.py --env-file .local\staging_validation_17C_cleanup_26K_LOCAL_ONLY.env --run-id slice26k_mixed_c50_dbads_20260711154050 --apply --confirm-staging --output evidence\slice_runs\cleanup_slice26k_mixed_c50_dbads_20260711154050.json
```

Cleanup resultado:

- `exit_code: 0`
- negocios borrados: `20`
- ads borrados: `91`
- credits_ledger borrados: `102`
- orders borradas: `38`
- payment_reports borrados: `11`
- audit logs retenidos por diseño: `120`

Evidencia adicional:

- `evidence/slice_runs/slice26k_mixed_c50_dbads_20260711154050.json`
- `evidence/slice_runs/cleanup_slice26k_mixed_c50_dbads_20260711154050.json`
- `evidence/slice_runs/slice_26K_db_direct_ads_staging_comparison_summary.json`
