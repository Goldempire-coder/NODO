# BUILDER_REPORT - slice_10_jobs_notifications

## Estado final

READY_FOR_OWNER_REVIEW

No se declara READY_FOR_REAL_USE.

## Resumen exacto

Se construyo `slice_10_jobs_notifications` con worker interno `expire_and_escalate_orders`, locks de ejecucion, registro en `job_runs`, cola deduplicada `notification_jobs`, dry-run admin no mutante, endpoints admin/ops read-only/dry-run, migracion reversible, runner de pruebas y evidencia.

## Archivos modificados o creados

- `apps/api/app/main.py`: integra repositorio de jobs, lock manager, worker y router.
- `apps/api/app/core/errors.py`: agrega errores seguros de jobs/notificaciones.
- `apps/api/app/modules/jobs/models.py`: modelos `JobRunRecord`, `NotificationJobRecord` y masking de metadata.
- `apps/api/app/modules/jobs/repository.py`: repositorios in-memory/Postgres para `job_runs` y `notification_jobs`.
- `apps/api/app/modules/jobs/lock.py`: locks in-memory y Redis.
- `apps/api/app/modules/jobs/worker.py`: worker `expire_and_escalate_orders`.
- `apps/api/app/modules/jobs/service.py`: RBAC/rate-limit/idempotencia para admin/ops jobs.
- `apps/api/app/modules/jobs/routes.py`: endpoints `/api/v1/admin/jobs/*`.
- `apps/api/app/modules/jobs/scheduler.py`: runner interno invocable por scheduler futuro.
- `apps/api/app/modules/orders/repository.py`: lectura `list_job_candidate_orders`.
- `apps/api/app/modules/ads/repository.py`: lectura `list_expirable_ads`.
- `apps/api/app/modules/businesses/repository.py`: founder expiration list/update.
- `database/migrations/0011_slice_10_jobs_notifications.up.sql`: migracion slice 10.
- `database/migrations/0011_slice_10_jobs_notifications.down.sql`: rollback slice 10.
- `apps/api/tests/test_jobs_notifications.py`: tests backend slice 10.
- `scripts/run_slice_10_tests.py`: runner oficial slice 10.
- `evidence/slice_runs/slice_10_jobs_notifications_test_results.json`: resultados JSON.
- `evidence/slice_runs/slice_10_jobs_notifications_evidence.md`: evidencia humana.
- `governance/builder_reports/slice_10_jobs_notifications_BUILDER_REPORT.md`: este reporte.

## Lineas relevantes

- `apps/api/app/modules/jobs/worker.py:24`: clase `ExpireAndEscalateOrdersWorker`.
- `apps/api/app/modules/jobs/worker.py:44`: ejecucion lock-protected con `dry_run`.
- `apps/api/app/modules/jobs/worker.py:126`: cancelacion de `waiting_payment` vencida.
- `apps/api/app/modules/jobs/worker.py:159`: escalacion `payment_reported` a disputa por deadline.
- `apps/api/app/modules/jobs/worker.py:188`: escalacion `payment_confirmed` a disputa por delivery deadline.
- `apps/api/app/modules/jobs/worker.py:215`: reminders y auto-complete de `delivered`.
- `apps/api/app/modules/jobs/worker.py:268`: expiracion de ads activos/pausados.
- `apps/api/app/modules/jobs/worker.py:287`: expiracion founder access.
- `apps/api/app/modules/jobs/routes.py:11`: router `/admin/jobs`.
- `apps/api/app/modules/jobs/service.py:21`: listado admin/support de job runs.
- `apps/api/app/modules/jobs/service.py:57`: dry-run admin/super_admin con idempotencia.
- `database/migrations/0011_slice_10_jobs_notifications.up.sql:1`: extension de `job_runs`.
- `database/migrations/0011_slice_10_jobs_notifications.up.sql:29`: tabla `notification_jobs`.
- `apps/api/tests/test_jobs_notifications.py:216`: dry-run no mutante y cancelacion vencida.
- `apps/api/tests/test_jobs_notifications.py:253`: `payment_reported` -> disputed.
- `apps/api/tests/test_jobs_notifications.py:273`: `payment_confirmed` -> disputed.
- `apps/api/tests/test_jobs_notifications.py:295`: reminders/autocomplete.
- `apps/api/tests/test_jobs_notifications.py:342`: ad/founder/admin endpoints/lock/RBAC.

## Endpoints construidos

- `GET /api/v1/admin/jobs/runs`
- `GET /api/v1/admin/jobs/runs/{id}`
- `POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run`

## Migraciones creadas

- `0011_slice_10_jobs_notifications.up.sql`
- `0011_slice_10_jobs_notifications.down.sql`

Incluye:

- `job_runs.duration_ms`
- `job_runs.lock_acquired`
- contadores `processed_count`, `changed_count`, `skipped_count`, `failed_count`
- checks de `job_type` y `status`
- tabla `notification_jobs`
- unique `notification_jobs(dedupe_key)`
- indices de deadlines de orders, ads expiration y founder expiration

## Contratos cumplidos

- `job_runs.job_type` canonico; `job_name` no se construyo.
- `job_runs.status` usa `started`, `finished`, `failed`, `skipped`, `lock_not_acquired`.
- `notification_jobs.notification_type` y `dedupe_key` canonicos.
- Dry-run no muta estados/creditos/anuncios/notificaciones.
- Locks con TTL: Redis en runtime normal; in-memory en `APP_ENV=test`.
- Waiting payment vencida cancela orden, libera hold y devuelve/expira anuncio segun deadline.
- `payment_reported` no se autocancela ni libera creditos; escala a disputa.
- `payment_confirmed` escala a disputa sin cambiar consumo ya realizado.
- `delivered` agenda reminders y auto-completa a 24h solo si no hay disputa abierta.
- Ads activos/pausados vencidos expiran y liberan hold si aplica.
- Founder access vencido pasa a `expired`.
- Metadata y respuestas admin no exponen datos privados.

## Comandos ejecutados

- `corepack pnpm --filter @nodo/web build`
- `python scripts\run_slice_00_tests.py`
- `python scripts\run_slice_01_tests.py`
- `python scripts\run_slice_02_tests.py`
- `python scripts\run_slice_03_tests.py`
- `python scripts\run_slice_04_tests.py`
- `python scripts\run_slice_05_tests.py`
- `python scripts\run_slice_06_tests.py`
- `python scripts\run_slice_07_tests.py`
- `python scripts\run_slice_08_tests.py`
- `python scripts\run_slice_09_tests.py`
- `python scripts\run_slice_10_tests.py`
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`
- `python -m ruff check apps\api scripts`
- `python -m compileall apps scripts`

## Resultados exactos

- Frontend build: OK.
- Slice 00 runner: OK, 6 passed.
- Slice 01 runner: OK, 6 passed.
- Slice 02 runner: OK.
- Slice 03 runner: OK.
- Slice 04 runner: OK.
- Slice 05 runner: OK.
- Slice 06 runner: OK.
- Slice 07 runner: OK.
- Slice 08 runner: OK.
- Slice 09 runner: OK.
- Slice 10 runner: OK.
- Pytest acumulado: 83 passed, 1 accepted Starlette/httpx warning.
- Ruff: OK.
- Compileall: OK.
- Frontend secret/private-data/scope scan: OK, hits `[]`.

## Tests no ejecutados

- Migraciones reales contra PostgreSQL/Supabase: no ejecutadas por falta de credenciales/servicio real, riesgo residual heredado aceptado.
- Redis real lock runtime: no ejecutado por falta de Redis real, cubierto por adapter in-memory en test.
- Envio real Telegram: no construido ni ejecutado en este slice; `notification_jobs` queda como cola interna.

## Evidencia creada

- `evidence/slice_runs/slice_10_jobs_notifications_test_results.json`
- `evidence/slice_runs/slice_10_jobs_notifications_evidence.md`

## Riesgos residuales

- Migraciones reales contra PostgreSQL/Supabase pendientes.
- Redis real pendiente para validacion runtime de locks/rate/idempotencia.
- Smoke manual Telegram real pendiente.
- Warning Starlette/httpx aceptado temporalmente.
- Scheduler externo real/deploy queda fuera del slice; se dejo runner interno invocable.

## Scope NO construido

- No deploy.
- No slice 11.
- No pantalla final `R-10_CONFIRM_RECEIVED`.
- No confirmacion manual de recibido por remitente.
- No admin dispute resolution nueva.
- No pagos reales, escrow, garantias ni procesamiento automatico de Zelle.
- No credenciales reales.
- No dependencias nuevas.
- No READY_FOR_REAL_USE.
