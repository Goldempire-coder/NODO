# slice_10_jobs_notifications Evidence

Estado: READY_FOR_OWNER_REVIEW

## Implementacion verificada

- Worker interno `expire_and_escalate_orders` implementado en `apps/api/app/modules/jobs/worker.py`.
- Locks de job implementados con adapter in-memory para test y Redis para runtime normal.
- `job_runs.job_type` usado como columna canonica; no se creo `job_name`.
- `notification_jobs.notification_type` y `dedupe_key` usados como contrato canonico.
- Endpoints admin/ops protegidos:
  - `GET /api/v1/admin/jobs/runs`
  - `GET /api/v1/admin/jobs/runs/{id}`
  - `POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run`
- Migracion reversible creada:
  - `database/migrations/0011_slice_10_jobs_notifications.up.sql`
  - `database/migrations/0011_slice_10_jobs_notifications.down.sql`

## Resultados de pruebas

- `corepack pnpm --filter @nodo/web build`: OK.
- `python scripts\run_slice_00_tests.py`: OK, 6 passed.
- `python scripts\run_slice_01_tests.py`: OK, 6 passed.
- `python scripts\run_slice_02_tests.py`: OK.
- `python scripts\run_slice_03_tests.py`: OK.
- `python scripts\run_slice_04_tests.py`: OK.
- `python scripts\run_slice_05_tests.py`: OK.
- `python scripts\run_slice_06_tests.py`: OK.
- `python scripts\run_slice_07_tests.py`: OK.
- `python scripts\run_slice_08_tests.py`: OK.
- `python scripts\run_slice_09_tests.py`: OK.
- `python scripts\run_slice_10_tests.py`: OK.
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 83 passed, 1 accepted Starlette/httpx warning.
- `python -m ruff check apps\api scripts`: OK.
- `python -m compileall apps scripts`: OK.

## Slice 10 runner

Archivo JSON:

- `evidence/slice_runs/slice_10_jobs_notifications_test_results.json`

Contenido relevante:

- `pytest apps/api/tests/test_jobs_notifications.py -q`: 5 passed, 1 accepted Starlette/httpx warning.
- `compileall apps/api scripts`: OK.
- `slice 10 migration contract scan`: OK, failures `[]`.
- `frontend secret/private-data/scope scan`: OK, hits `[]`.

## Seguridad / datos privados

- No se exponen `storage_path`, `account_value`, payment instructions completas, tokens ni secretos en responses de endpoints admin de jobs.
- Metadata de `job_runs` y `notification_jobs` pasa por masking antes de persistir/serializar.
- Dry-run no muta ordenes, creditos, anuncios ni notificaciones.
- Support puede ver job runs, pero no ejecutar dry-run.

## Riesgos residuales heredados

- Migraciones reales contra PostgreSQL/Supabase siguen pendientes hasta tener servicio/credenciales.
- Redis real sigue pendiente para validacion runtime real; test usa adapter in-memory.
- Storage privado real sigue pendiente para slices que lo requieren.
- Smoke manual Telegram real sigue pendiente.
- Warning Starlette/httpx aceptado temporalmente.

## Scope no construido

- No deploy.
- No credenciales reales.
- No procesamiento real de Telegram.
- No pagos reales, escrow ni garantias de fondos.
- No resolucion admin de disputas nueva.
- No pantalla final `R-10_CONFIRM_RECEIVED`.
- No slice 11.
- No `READY_FOR_REAL_USE`.
