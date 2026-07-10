# QA.md

Pruebas obligatorias:

- waiting_payment vence a 30 min sin extension -> cancelled, creditos liberados.
- waiting_payment con extension -> vence maximo a 45 min.
- payment_reported a 2h -> warning negocio.
- payment_reported a 6h -> disputed, creditos siguen bloqueados.
- payment_confirmed a 30 min -> warning negocio.
- payment_confirmed a 2h -> disputed, creditos ya consumidos.
- delivered -> recordatorio inmediato, 12h, 23h.
- delivered a 24h sin disputa -> completed auto_completed_after_24h.
- delivered con disputa abierta -> no auto-complete.
- job repetido no duplica notificaciones.
- job repetido no duplica transiciones.
- lock Redis evita doble procesamiento concurrente.
- fallo de Telegram reintenta con backoff sin duplicar estado.
- `job_runs.job_type` usa `expire_and_escalate_orders`; no existe `job_name`
  activo.
- `job_runs.status` solo usa `started`, `finished`, `failed`, `skipped` o
  `lock_not_acquired`.
- `notification_jobs.status` solo usa `pending`, `sent`, `failed`, `skipped` o
  `cancelled`.
- `notification_jobs.dedupe_key` evita duplicar recordatorios por recurso,
  tipo y ventana.
- `GET /api/v1/admin/jobs/runs` es admin/super_admin/support read-only.
- `POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run` exige
  admin/super_admin, rate limit e idempotency key, y no muta datos.
- errores de job existen en `ERROR_CONTRACT.md` y se devuelven con copy seguro
  solo a admin/ops autorizado.
- R-10 confirmacion manual no se construye en slice 10.
- metadata de jobs/notificaciones no expone `storage_path`, `account_value`,
  instrucciones completas, tokens, secretos ni evidencia privada.
