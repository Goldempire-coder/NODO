# BUILDER_REPORT - slice_17E_staging_missing_index_repair

## Estado final

READY_FOR_OWNER_REVIEW

## Objetivo

Construir tooling seguro para aplicar una sola migracion staging aprobada, sin tocar `nodo_schema_migrations`.

## Que construi

- Nuevo script `scripts/apply_staging_single_migration.py`.
- Pruebas especificas en `apps/api/tests/test_staging_validation_tooling.py`.
- Artefactos de evidencia para la fase 17E.

## Reglas implementadas

- `--env-file` obligatorio.
- `--run-id` obligatorio.
- `--migration` obligatorio.
- `--output` obligatorio.
- Dry-run por defecto.
- Escritura solo con `--apply --confirm-staging`.
- Usa `staging_guardrails.py`.
- Rechaza rutas absolutas.
- Rechaza `..`.
- Rechaza subdirectorios.
- Requiere archivo `.up.sql`.
- Valida que la migracion este bajo `database/migrations`.
- No toca `nodo_schema_migrations`.
- No borra datos.
- Bloquea SQL destructivo: `drop`, `truncate`, `reset`, `delete from`.
- Output JSON usa guardrails con secretos redactados.
- Dry-run reporta archivo, checksum, statements detectados y `writes_database=false`.
- Apply ejecuta solo el archivo solicitado dentro de transaccion y advisory lock.

## Caso objetivo

`0016_query_performance_indexes.up.sql` fue verificado por tests:

- contiene `orders_active_created_idx`.
- tiene 12 statements.
- los 12 statements son `create index if not exists`.

## Archivos modificados

- `scripts/apply_staging_single_migration.py`
- `apps/api/tests/test_staging_validation_tooling.py`

## Artefactos creados

- `governance/builder_reports/slice_17E_staging_missing_index_repair_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_17E_staging_missing_index_repair_evidence.md`
- `evidence/slice_runs/slice_17E_staging_missing_index_repair_test_results.json`

## Validaciones ejecutadas

- `python -m pytest apps\api\tests\test_staging_validation_tooling.py -q --tb=short`
  - Resultado: `26 passed, 1 warning`
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`
  - Resultado: `164 passed, 1 warning`
- `python -m ruff check apps\api scripts`
  - Resultado: `All checks passed!`
- `python -m compileall apps\api apps\web\src scripts`
  - Resultado: OK
- `corepack pnpm --filter @nodo/web build`
  - Resultado: OK

## Que NO hice

- No escribi en Supabase.
- No corri apply real.
- No aplique la migracion real.
- No borre datos.
- No toque ledger.
- No hice deploy.
- No imprimi secretos.
- No declare `READY_FOR_REAL_USE`.

## Riesgos residuales

- El script debe correrse primero en dry-run contra staging real.
- El apply real de `0016_query_performance_indexes.up.sql` requiere aprobacion owner, `--apply --confirm-staging`, y `STAGING_VALIDATION_ACK` igual al `--run-id`.
- Despues del apply real, debe correrse nuevamente el dry-run del reconciliador de ledger antes de marcar ledger.

