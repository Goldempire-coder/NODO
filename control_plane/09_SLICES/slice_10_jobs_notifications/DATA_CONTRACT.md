# DATA_CONTRACT.md

## Campos requeridos en orders

- payment_report_deadline_at
- payment_report_extension_used_at
- business_response_warning_at
- business_response_deadline_at
- delivery_warning_at
- delivery_deadline_at
- auto_complete_warning_12h_at
- auto_complete_warning_23h_at
- auto_complete_at
- cancel_reason
- dispute_reason

## Tablas requeridas o equivalentes

- notification_jobs
- job_runs
- audit_logs

## job_runs

Columnas canonicas:

- id
- job_type
- status
- started_at
- finished_at
- duration_ms
- lock_key
- lock_acquired
- processed_count
- changed_count
- skipped_count
- failed_count
- error_code
- error_message_safe
- metadata_json
- created_at
- updated_at

Reglas:

- `job_type` es canonico; `job_name` esta prohibido/no valido como columna activa.
- `job_type` inicial: `expire_and_escalate_orders`.
- `status` usa enum oficial:
  - started
  - finished
  - failed
  - skipped
  - lock_not_acquired
- `duration_ms` nullable y `>= 0`.
- Contadores `processed_count`, `changed_count`, `skipped_count` y
  `failed_count` deben ser `>= 0`.
- `error_message_safe` no contiene stack traces, SQL, tokens, secretos,
  `storage_path`, `account_value` ni instrucciones completas.
- `lock_key` no contiene secretos.

## notification_jobs

Columnas canonicas:

- id
- notification_type
- recipient_user_id nullable
- recipient_role nullable
- order_id nullable
- business_id nullable
- dispute_id nullable
- status
- scheduled_for
- sent_at
- failed_at
- attempts
- max_attempts
- last_error_code
- dedupe_key
- metadata_json
- created_at
- updated_at

Reglas:

- `notification_type` es canonico; `event_type` es legacy/no valido para nuevas
  migraciones de notification jobs.
- `status` usa enum oficial:
  - pending
  - sent
  - failed
  - skipped
  - cancelled
- `attempts >= 0`.
- `max_attempts > 0`.
- `dedupe_key` unique por recurso, tipo de notificacion y ventana de tiempo.
- Si `recipient_user_id` es null, `recipient_role` debe estar presente.
- `metadata_json` es privado/enmascarado y no contiene `storage_path`,
  `account_value`, instrucciones completas, signed URLs, tokens, secretos,
  evidencia privada ni promesas de fondos.

## Indices requeridos

- orders(status, payment_report_deadline_at)
- orders(status, business_response_warning_at)
- orders(status, business_response_deadline_at)
- orders(status, delivery_warning_at)
- orders(status, delivery_deadline_at)
- orders(status, auto_complete_at)
- notification_jobs(status, scheduled_for asc)
- notification_jobs(notification_type, status, scheduled_for asc)
- notification_jobs(dedupe_key) unique
- job_runs(job_type, status, created_at desc)
- job_runs(job_type, started_at desc)
- job_runs(lock_key) parcial cuando lock_key no sea null

## Regla transaccional

Cada transicion automatica debe ejecutarse en transaccion DB y debe llamar el mismo state machine/credit service que usaria una accion manual.

## Locks e idempotencia

- Redis lock key canonica: `jobs:expire_and_escalate_orders`.
- TTL canonico: 5 minutos; debe renovarse o liberarse con seguridad si el job
  tarda mas que el TTL.
- Si no se obtiene lock, registrar `job_runs.status = lock_not_acquired`,
  `lock_acquired = false` y error seguro `JOB_LOCK_NOT_ACQUIRED`.
- La ejecucion con lock usa `lock_acquired = true`.
- Notificaciones son idempotentes por `dedupe_key`.
- Transiciones automaticas son idempotentes por estado actual, deadline y
  existencia de dispute/event/audit previo.
