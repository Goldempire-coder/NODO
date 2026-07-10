# BUILDER_REPORT - slice_17D_staging_migration_ledger_reconciliation

## Estado final

READY_FOR_OWNER_REVIEW

## Fix owner-audit

Se corrigieron checks incorrectos detectados por dry-run real:

- `notification_jobs.job_type` era incorrecto; la columna canonica es `notification_jobs.notification_type`.
- `notification_jobs.scheduled_at` era incorrecto; la columna canonica es `notification_jobs.scheduled_for`.
- `orders_active_created_idx` se mantiene como check requerido porque pertenece a `0016_query_performance_indexes.up.sql`.

## Objetivo

Construir tooling seguro para reconciliar `nodo_schema_migrations` en staging cuando el schema ya existe pero el ledger no existe o no esta poblado.

## Que construi

- Nuevo script `scripts/reconcile_staging_migration_ledger.py`.
- Pruebas especificas en `apps/api/tests/test_staging_validation_tooling.py`.
- Artefactos de evidencia para esta fase.

## Reglas implementadas

- `--env-file` obligatorio.
- `--run-id` obligatorio.
- `--output` obligatorio.
- Dry-run por defecto.
- Escritura solo con `--apply --confirm-staging` y guardrails mutantes.
- Usa `staging_guardrails.py`.
- Usa advisory lock PostgreSQL.
- No ejecuta archivos `.up.sql`.
- No aplica migraciones.
- No borra datos.
- No hace drop/reset/truncate.
- Crea `nodo_schema_migrations` solo en apply confirmado.
- Calcula checksums desde `database/migrations/*.up.sql`.
- Verifica schema antes de insertar ledger.
- Inserta ledger solo para migraciones verificadas.
- Bloquea si falta tabla/columna/indice/constraint o si hay checksum mismatch.
- Output JSON usa guardrails con secretos redactados.

## Checks de schema incluidos

- Tablas requeridas desde `validate_local_schema.py`.
- Columnas principales ampliadas para ordenes, anuncios, creditos, chat, disputas, compras, jobs e intake.
- `notification_jobs` usa los nombres canonicos `notification_type` y `scheduled_for`.
- Indices requeridos desde `validate_local_schema.py` mas indices criticos de ordenes, pagos, chat, disputas, creditos e intake.
- `orders_active_created_idx` sigue siendo requerido.
- Constraints/FKs criticas, incluyendo `ads_credit_hold_ledger_fk`.
- Ledger ausente, vacio o parcial compatible.
- Checksum mismatch bloqueante.
- Entradas desconocidas en ledger bloqueantes.

## Archivos modificados

- `scripts/reconcile_staging_migration_ledger.py`
- `apps/api/tests/test_staging_validation_tooling.py`

## Artefactos creados

- `governance/builder_reports/slice_17D_staging_migration_ledger_reconciliation_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_17D_staging_migration_ledger_reconciliation_evidence.md`
- `evidence/slice_runs/slice_17D_staging_migration_ledger_reconciliation_test_results.json`

## Validaciones ejecutadas

- `python -m pytest apps\api\tests\test_staging_validation_tooling.py -q --tb=short`
  - Resultado: `22 passed, 1 warning`
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`
  - Resultado: `160 passed, 1 warning`
- `python -m ruff check apps\api scripts`
  - Resultado: `All checks passed!`
- `python -m compileall apps\api apps\web\src scripts`
  - Resultado: OK
- `corepack pnpm --filter @nodo/web build`
  - Resultado: OK

## Que NO hice

- No escribi en Supabase.
- No corri apply real.
- No corri servicios reales.
- No hice deploy.
- No imprimi secretos.
- No modifique backend de producto.
- No modifique frontend de producto.
- No modifique migraciones existentes.
- No declare `READY_FOR_REAL_USE`.

## Riesgos residuales

- El script aun debe ejecutarse en dry-run contra staging real antes de permitir apply.
- Si el dry-run detecta schema drift, el siguiente estado debe ser `BLOCKED_BY_SCHEMA_DRIFT`.
- El apply contra staging requiere aprobacion explicita del owner y `STAGING_VALIDATION_ACK` igual al `--run-id`.
