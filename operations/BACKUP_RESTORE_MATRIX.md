# BACKUP_RESTORE_MATRIX

Estado: OFFICIAL - OWNER DECISIONS REQUIRED
Ultima actualizacion: 2026-09-09

## RTO/RPO por Tier

Propuesta tecnica pendiente de aprobacion owner.

| Tier | Componentes | RTO propuesto | RPO propuesto | Estado |
|---|---|---:|---:|---|
| Tier 0 | dinero, creditos, auth, permisos, audit, datos privados | 4 horas | 15 minutos | DECISION REQUIRED |
| Tier 1 | ordenes operativas, soporte, bots, ads, intake | 8 horas | 1 hora | DECISION REQUIRED |
| Tier 2 | cache, dashboards, tooling, evidencia sintetica | 24 horas | 24 horas | DECISION REQUIRED |
| Tier 3 | outputs regenerables, artefactos no criticos | 72 horas | best effort | DECISION REQUIRED |

## Ownership

Owner primario de piloto: Carlos.

Backup operativo/persona alterna: NOT DEFINED -- RELEASE RISK.

Hasta definir backup humano y permisos por proveedor, cualquier incidente Tier 0 depende del Owner.

## Matriz por componente

| Componente | Datos | Tier | Backup status | Restore status | RTO/RPO | Owner tecnico | Owner operativo | Backup owner | Escalamiento |
|---|---|---:|---|---|---|---|---|---|---|
| Supabase PostgreSQL | users, sessions, businesses, access links, ads, orders, payment reports, credits, support, staff, audit, jobs, intake | 0 | PROVIDER_ACCESS_REQUIRED | NOT VALIDATED | DECISION REQUIRED | OWNERSHIP NOT DEFINED -- RELEASE RISK | OWNERSHIP NOT DEFINED -- RELEASE RISK | OWNERSHIP NOT DEFINED -- RELEASE RISK | Owner + DB reliability |
| Supabase Storage privado | file assets backing documents/evidence/support/intake | 0/1 | PROVIDER_ACCESS_REQUIRED | NOT VALIDATED | DECISION REQUIRED | OWNERSHIP NOT DEFINED -- RELEASE RISK | OWNERSHIP NOT DEFINED -- RELEASE RISK | OWNERSHIP NOT DEFINED -- RELEASE RISK | Owner + storage provider |
| Redis/Upstash | rate limit, locks, idempotency windows, cache | 0/1 | UNKNOWN | NOT VALIDATED | DECISION REQUIRED | OWNERSHIP NOT DEFINED -- RELEASE RISK | OWNERSHIP NOT DEFINED -- RELEASE RISK | OWNERSHIP NOT DEFINED -- RELEASE RISK | Owner + runtime |
| Railway backend | API image, env, runtime config | 0/1 | Provider deploy history AVAILABLE IN RAILWAY, not exported to repo | Native provider rollback NOT VALIDATED; redeploy SHA rollback documented for staging | DECISION REQUIRED | Carlos | BACKUP NOT DEFINED -- RELEASE RISK | BACKUP NOT DEFINED -- RELEASE RISK | Owner + release manager |
| Cloudflare frontend | static export, public env, deploy history | 1 | Provider deploy history AVAILABLE IN CLOUDFLARE, not exported to repo | Native provider rollback NOT VALIDATED; redeploy SHA rollback documented for staging | DECISION REQUIRED | Carlos | BACKUP NOT DEFINED -- RELEASE RISK | BACKUP NOT DEFINED -- RELEASE RISK | Owner + release manager |
| Secrets/env vars | Railway secrets, Cloudflare public env, Telegram, Supabase, Upstash, Base RPC | 0 | UNKNOWN | NOT VALIDATED | DECISION REQUIRED | OWNERSHIP NOT DEFINED -- RELEASE RISK | OWNERSHIP NOT DEFINED -- RELEASE RISK | OWNERSHIP NOT DEFINED -- RELEASE RISK | Owner only |
| Telegram bots/webhooks | BOT_TOKEN, BUSINESS_INTAKE_BOT_TOKEN, webhook config | 1 | PROVIDER_ACCESS_REQUIRED | NOT VALIDATED | DECISION REQUIRED | OWNERSHIP NOT DEFINED -- RELEASE RISK | OWNERSHIP NOT DEFINED -- RELEASE RISK | OWNERSHIP NOT DEFINED -- RELEASE RISK | Owner + bot operator |
| Base RPC/on-chain watcher | RPC URL/key, destination wallet public config, network profile, watcher state in DB | 0 | DB backup dependent, RPC provider UNKNOWN | NOT VALIDATED | DECISION REQUIRED | Carlos | BACKUP NOT DEFINED -- RELEASE RISK | BACKUP NOT DEFINED -- RELEASE RISK | Owner + credits operator |
| Audit logs | audit_logs append-only | 0 | DB backup dependent | NOT VALIDATED | DECISION REQUIRED | OWNERSHIP NOT DEFINED -- RELEASE RISK | OWNERSHIP NOT DEFINED -- RELEASE RISK | OWNERSHIP NOT DEFINED -- RELEASE RISK | Owner + security |
| file_assets | DB metadata for private files | 0/1 | DB backup dependent | NOT VALIDATED with storage | DECISION REQUIRED | OWNERSHIP NOT DEFINED -- RELEASE RISK | OWNERSHIP NOT DEFINED -- RELEASE RISK | OWNERSHIP NOT DEFINED -- RELEASE RISK | Owner + storage |
| notification_jobs | pending/sent notification state | 1/2 | DB backup dependent | NOT VALIDATED | DECISION REQUIRED | OWNERSHIP NOT DEFINED -- RELEASE RISK | OWNERSHIP NOT DEFINED -- RELEASE RISK | OWNERSHIP NOT DEFINED -- RELEASE RISK | Owner + operations |

## Componentes que requieren restore drill obligatorio

- Supabase PostgreSQL.
- Supabase Storage privado.
- DB + storage consistency.
- Secrets/env recovery.
- Railway/Cloudflare rollback.

Para piloto controlado sin USDC real, el riesgo de creditos on-chain puede mitigarse manteniendo compras crypto desactivadas y asignando creditos manualmente por Owner. Esto no elimina la necesidad de backup/restore antes de produccion abierta.

## Componentes que no deben restaurarse como fuente canonica

- Redis cache marketplace.
- Redis transient rate windows.
- Redis locks.

Para Redis, el contrato debe definir comportamiento ante perdida: fail closed donde proteja dinero/idempotencia, fail open solo para cache publica segura.
