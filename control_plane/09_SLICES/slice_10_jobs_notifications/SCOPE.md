# SCOPE.md

## Incluye

- Worker `expire_and_escalate_orders`.
- Scheduler cada pocos minutos.
- Locks Redis con TTL.
- Recordatorios Telegram.
- Escalaciones automaticas a disputa.
- Cancelacion automatica de `waiting_payment` vencida.
- Auto-complete de `delivered` a las 24h si no hay disputa.
- Expiracion de anuncios.
- Expiracion de founder access.
- Registro de job runs y fallos.
- Endpoints admin/ops protegidos para observar `job_runs` y ejecutar dry-run
  sin mutaciones reales:
  - `GET /api/v1/admin/jobs/runs`
  - `GET /api/v1/admin/jobs/runs/{id}`
  - `POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run`

## No incluye

- Cambiar reglas de estados.
- Crear nuevos estados.
- Resolver disputas.
- Aprobar pagos.
- Consumir/liberar creditos fuera de las reglas de dominio.
- Enviar spam de recordatorios.
- Deploy.
- Servicios reales o credenciales reales.
- Declarar `READY_FOR_REAL_USE`.
- Confirmacion manual del remitente en `R-10_CONFIRM_RECEIVED`.
- Pagos reales, escrow o garantias de fondos.
- Procesamiento automatico de Zelle.

## job_runs

- Usar `job_type`, no `job_name`.
- `job_type` inicial: `expire_and_escalate_orders`.
- `job_name` queda prohibido/no valido como columna activa.

## Bloqueo

Si falta state machine o credit service transaccional, reportar `BLOCKED_BY_MISSING_CONTRACT`.
