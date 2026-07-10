# OWNER VERIFICATION - slice_10_jobs_notifications

Fecha: 2026-07-04

Estado auditado del builder: READY_FOR_OWNER_REVIEW

Estado owner verification: OWNER_ACCEPTED_FOR_NEXT_SLICE

## Resultado

El slice 10 fue auditado contra contratos, implementacion y pruebas acumuladas.

No se declara READY_FOR_REAL_USE.

## Hallazgos corregidos

1. `POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run` aceptaba ausencia de `Idempotency-Key`.
   - Corregido para devolver `IDEMPOTENCY_KEY_REQUIRED`.
   - Test agregado.

2. El worker usaba eventos audit no canonicos para jobs y algunas transiciones.
   - Agregado audit de `job_started`, `job_finished` y `job_failed`.
   - Cancelacion por no reportar pago usa `order_cancelled_payment_not_reported`.
   - Warnings usan `order_business_response_warning_sent` y `order_delivery_warning_sent`.

3. `delivered` reminders usaban `notification_type = delivered_reminder` generico.
   - Corregido a `delivered_reminder_immediate`, `delivered_reminder_12h` y `delivered_reminder_23h`.
   - Corregido dedupe para no duplicar auditoria y para avanzar a la siguiente ventana cuando la anterior ya existe.

4. Notificaciones por destinatario estaban incompletas.
   - Cancelacion por no reportar pago notifica remitente y negocio.
   - Disputa automatica notifica remitente, negocio, admin y support.
   - Auto-complete notifica remitente y negocio.
   - Expiracion de anuncio notifica negocio.

5. Migracion `0011_slice_10_jobs_notifications` no materializaba todos los constraints e indices de contratos.
   - Agregados checks de `job_runs.attempts`, terminal `finished_at`, `failed.error_code`.
   - Agregado check canonico de `notification_jobs.notification_type`.
   - Agregado check de timestamps terminales de notificacion.
   - Agregados indices de `job_runs(job_type,status,created_at)`, `job_runs(lock_key)` parcial y indices parciales de `notification_jobs` por order/business/dispute.
   - Down migration actualizada.

## Archivos tocados por owner verification

- `apps/api/app/modules/jobs/service.py`
- `apps/api/app/modules/jobs/worker.py`
- `apps/api/tests/test_jobs_notifications.py`
- `database/migrations/0011_slice_10_jobs_notifications.up.sql`
- `database/migrations/0011_slice_10_jobs_notifications.down.sql`

## Verificacion ejecutada

- `python -m ruff check apps\api scripts`: OK
- `python -m compileall apps scripts`: OK
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_jobs_notifications.py -q`: 7 passed, 1 warning
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 85 passed, 1 warning
- `corepack pnpm --filter @nodo/web build`: OK
- `foreach ($i in 0..10) { python scripts\run_slice_{0:D2}_tests.py }`: OK
- Frontend secret/private-data scan: OK, sin hits

## Riesgos residuales

- Migraciones reales contra PostgreSQL/Supabase siguen pendientes.
- Redis real sigue pendiente.
- Storage privado real sigue pendiente.
- Smoke Telegram real sigue pendiente.
- Warning Starlette/httpx sigue aceptado temporalmente.

## Decision

`slice_10_jobs_notifications` queda aceptado para continuar al siguiente corte gobernado.

No se autoriza uso real ni deploy productivo.
