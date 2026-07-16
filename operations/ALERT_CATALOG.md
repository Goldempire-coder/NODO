# ALERT_CATALOG

Estado: REQUIRED, NOT IMPLEMENTED AS PROVIDER CONFIG
Ultima actualizacion: 2026-07-11

Las alertas siguientes son necesarias. Este archivo no prueba que ya existan en Railway, Supabase, Upstash o Cloudflare.

| Alert ID | Condicion | Severidad | Impacto | Runbook |
|---|---|---:|---|---|
| API_READY_503 | `/ready` devuelve 503 durante 2 minutos | SEV-1/2 | API no lista, DB o Redis fallando | `runbooks/API_5XX_RUNBOOK.md` o `DATABASE_UNAVAILABLE_RUNBOOK.md` |
| API_5XX_RATE | 5xx sostenido por encima de umbral definido | SEV-1/2 | Falla backend | `runbooks/API_5XX_RUNBOOK.md` |
| API_LATENCY_P95 | p95 mayor al umbral definido por 5 min | SEV-2 | Degradacion | `runbooks/API_LATENCY_RUNBOOK.md` |
| DB_CONNECTIONS_HIGH | conexiones Postgres cerca del limite | SEV-1/2 | riesgo de caida DB/API | `runbooks/DB_POOL_SATURATION_RUNBOOK.md` |
| REDIS_UNAVAILABLE | readiness Redis falla | SEV-1/2 | idempotencia/rate/locks en riesgo | `runbooks/API_5XX_RUNBOOK.md` |
| TELEGRAM_NO_RESPONSE | bot no responde o webhook falla | SEV-2 | clientes/negocios no inician flujo | `runbooks/TELEGRAM_BOT_NO_RESPONSE_RUNBOOK.md` |
| ONCHAIN_CREDIT_ERRORS | watcher reporta errores o under_review alto | SEV-1/2 | creditos no se acreditan o riesgo financiero | `runbooks/CREDITS_NOT_APPEARING_RUNBOOK.md` |
| DUPLICATE_CREDIT_SIGNAL | tx/hash/ledger duplicado detectado | SEV-1 | riesgo financiero | `runbooks/DUPLICATE_CREDITS_RUNBOOK.md` |
| STORAGE_PRIVATE_FAIL | storage smoke falla | SEV-2 | evidencia/adjuntos no disponibles | `runbooks/STORAGE_UPLOAD_FAILURE_RUNBOOK.md` |
| UNAUTHORIZED_ACCESS | acceso a datos ajenos o escalamiento | SEV-1 | privacidad/seguridad | `runbooks/UNAUTHORIZED_ACCESS_RUNBOOK.md` |

## Decisiones requeridas

- Umbrales numericos finales.
- Herramienta de alerting.
- Canal de notificacion.
- Rota on-call.
- Responsable primario y backup.
