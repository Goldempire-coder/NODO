# slice_10_jobs_notifications

Construye workers, timers y notificaciones. No construir fuera del scope aprobado.

Job obligatorio:

```txt
expire_and_escalate_orders
```

Este job revisa cada pocos minutos:

- ordenes `waiting_payment` vencidas.
- ordenes `payment_reported` que necesitan warning o disputa.
- ordenes `payment_confirmed` que necesitan warning o disputa.
- ordenes `delivered` que necesitan recordatorios o auto-complete.
- anuncios expirados.
- Founder: solo historial, sin nuevas expiraciones ni avisos desde la decision Owner 2026-09-29.

El job debe ser idempotente, usar locks Redis con TTL y escribir audit logs.
