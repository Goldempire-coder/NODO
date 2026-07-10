# STATE_CONTRACT.md

## waiting_payment

Timer: 30 minutos + extension unica de 15 minutos.

Al vencer:

```txt
order.status = cancelled
cancel_reason = payment_not_reported_in_time
ad.status = active si no vencio
credits = released
```

## payment_reported

Timer:

- 2 horas: warning al negocio.
- 6 horas: disputa.

Al vencer limite fuerte:

```txt
order.status = disputed
dispute_reason = business_no_payment_confirmation
ad.status = in_order
credits = still_blocked
```

## payment_confirmed

Timer:

- 30 minutos: warning al negocio.
- 2 horas: disputa.

Al vencer limite fuerte:

```txt
order.status = disputed
dispute_reason = business_confirmed_payment_but_not_delivered
credits = already_consumed
```

## delivered

Timer:

- recordatorio inmediato.
- recordatorio 12h.
- recordatorio 23h.
- auto complete 24h si no hay disputa.

Al vencer:

```txt
order.status = completed
completion_reason = auto_completed_after_24h
```

## Ads

- Expirar anuncios activos/pausados al cumplir 7 dias segun `AD_LIFECYCLE_MASTER`.
- Si un anuncio expira sin pago confirmado y mantiene credit hold, liberar
  creditos por la ruta oficial de credit service.
- No reactivar anuncios `in_order` o `archived` indebidamente.
- No devolver al marketplace anuncios asociados a ordenes vivas.

## Founder access

- Expirar founder access cuando `founder_expires_at <= now`.
- Setear `business.founder_status = expired`.
- Auditar `founder_access_expired`.
- No saltar verificacion de negocio, limites de riesgo ni auditoria.

## job_runs.status

- `started`: job tomo lock e inicio procesamiento.
- `finished`: job termino sin fallos bloqueantes.
- `failed`: job tuvo fallo seguro registrado.
- `skipped`: job no tenia trabajo elegible o dry-run no mutante.
- `lock_not_acquired`: otra ejecucion mantiene lock activo.

## notification_jobs.status

- `pending`: notificacion programada/no enviada.
- `sent`: enviada al canal.
- `failed`: fallo permanente o agoto reintentos.
- `skipped`: omitida por dedupe, estado ya cambiado o ventana vencida.
- `cancelled`: cancelada porque el recurso cambio de estado antes del envio.

## Prohibido

- Cancelar automaticamente `payment_reported`.
- Liberar creditos cuando existe pago reportado y negocio no responde.
- Auto-completar si hay disputa abierta.
- Construir confirmacion manual del remitente en `R-10_CONFIRM_RECEIVED`.
- Resolver disputas admin.
- Procesar pagos reales, escrow o garantias de fondos.
