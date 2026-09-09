# SERVICE_CATALOG

Estado: OFFICIAL
Ultima actualizacion: 2026-09-09

## Criterios

- TIER 0: financiero, seguridad, datos criticos o acceso privilegiado.
- TIER 1: operacion principal de cliente/negocio/admin.
- TIER 2: degradacion operativa con alternativa temporal.
- TIER 3: impacto limitado.

RTO/RPO no estan definidos formalmente. Donde aplique se marca `DECISION REQUERIDA`.

## Catalogo

| Componente | Donde vive | Proposito | Tier | Dependencias | Verificacion real | Logs/metricas reales | Recuperacion | Rollback | Owner |
|---|---|---:|---:|---|---|---|---|---|---|
| Backend API FastAPI | Railway via `Dockerfile`, `railway.json` | API unica, auth, ordenes, creditos, admin, soporte | 0/1 | Supabase Postgres, Upstash Redis, Supabase Storage, Telegram, Base RPC | `GET /health`, `/ready`, `/version` y `/api/v1/*` | Python logging redacted, `X-NODO-Process-Time-Ms`, `Server-Timing` | Restart Railway, redeploy SHA anterior, revisar readiness | Provider rollback nativo requerido, redeploy staging documentado | OWNER PRIMARY: Carlos; BACKUP NOT DEFINED |
| Frontend Web / Mini Apps | Cloudflare Pages / Next export | Cliente, Negocio, Admin Web | 1 | Backend API, Telegram WebApp para mini apps | `corepack pnpm --filter @nodo/web build`, `corepack pnpm deploy:web:staging`, browser smoke | Cloudflare logs no documentados | Redeploy SHA anterior desde worktree limpio | Provider rollback nativo requerido, deploy script staging existe | OWNER PRIMARY: Carlos; BACKUP NOT DEFINED |
| PostgreSQL / Supabase | Supabase | Datos canonicos, idempotencia DB, audit, ordenes, creditos | 0 | Backend API | `scripts/validate_staging_schema.py`, `/ready` | Supabase metrics no integradas al repo | Restore backup Supabase requerido | DB rollback por migraciones down, restore no probado | OWNERSHIP NOT DEFINED - RELEASE RISK |
| Redis / Upstash | Upstash Redis | Rate limits, idempotencia, locks, marketplace cache | 0/1 | Backend API | `/ready`, staging guardrails, scripts de stress | Upstash metrics no integradas | Reconfigurar Redis URL o proveedor; riesgo de idempotencia | No rollback de datos Redis documentado | OWNERSHIP NOT DEFINED - RELEASE RISK |
| Supabase Storage privado | Supabase Storage | Evidencia, documentos intake, soporte, adjuntos | 0/1 | Backend API, service role backend-only | `scripts/staging_storage_smoke.py` | No metricas integradas | Revisar buckets/env, smoke upload/signed URL/delete | No rollback de objetos documentado | OWNERSHIP NOT DEFINED - RELEASE RISK |
| Telegram bot cliente | Telegram + `/api/v1/telegram/webhook/{secret}` | Entrada cliente y Mini App | 1 | BOT_TOKEN, Backend API | `scripts/staging_telegram_webhook_smoke.py --bot client` | Telegram/provider logs no integrados | Revalidar webhook secret/env y backend route | Revertir token/webhook en provider | OWNERSHIP NOT DEFINED - RELEASE RISK |
| Telegram bot registro negocios | Telegram + `/api/v1/business-intake/telegram/webhook/{secret}` | Intake conversacional de negocios | 1/2 | BUSINESS_INTAKE_BOT_TOKEN, Storage, DB | `scripts/staging_telegram_webhook_smoke.py --bot business-intake` | API logs, audit events | Revalidar token/webhook, revisar intake state | Revertir deploy/provider webhook | OWNERSHIP NOT DEFINED - RELEASE RISK |
| Base USDC credit verifier/watcher | Backend scheduler interno `_base_usdc_credit_watcher_loop` + worker object `verify_base_usdc_credit_purchases` | Acreditar creditos on-chain exact-once | 0 | BASE_RPC_URL, NODO_CREDIT_PAYMENT_NETWORK, NODO_CREDIT_RECEIVING_WALLET_BASE, DB | Tests; staging debe usar Base Sepolia/testnet hasta aprobacion Owner separada | Audit events, Telegram Admin Alerts de atencion, `base_usdc_credit_watcher_finished`, `base_usdc_credit_watcher_failed` con contadores redacted | Revisar logs, RPC/env y compras pending; reintentar por scheduler o ejecutar worker controlado | Desactivar `ONCHAIN_CREDIT_WATCHER_ENABLED`; Rechazo/admin review; no auto-refund | OWNER PRIMARY: Carlos; BACKUP NOT DEFINED |
| Stripe legacy webhook | `/api/v1/webhooks/stripe` | Acreditacion legacy/test de creditos | 0/2 | STRIPE_WEBHOOK_SECRET, DB | Tests de webhook firmado | Audit events | Revisar firma/idempotencia | Deshabilitar legacy si owner decide | OWNERSHIP NOT DEFINED - RELEASE RISK |
| Jobs expire/escalate | Worker en API state, admin dry-run | Expira ordenes/anuncios, notificaciones | 1/2 | Redis lock, DB | `POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run` | `job_runs`, audit logs | Dry-run, luego runner real si existe | No scheduler rollback documentado | OWNERSHIP NOT DEFINED - RELEASE RISK |
| Admin Web | Cloudflare + backend admin APIs | Control admin, staff, soporte, creditos | 0/1 | Backend API, JWT admin | Manual/admin smoke; tests | Audit logs | Bloquear usuario/staff, revertir deploy | Provider rollback | OWNERSHIP NOT DEFINED - RELEASE RISK |
| Support Ticket Center | Backend `support`, UI client/business/admin | Soporte cliente/negocio/admin | 1/2 | DB, storage, staff permissions | Tests `test_support_ticket_center.py` | Audit/ticket events | Staff/admin triage, runbook soporte | No rollback de mensajes | OWNERSHIP NOT DEFINED - RELEASE RISK |
| Staging validation tooling | `scripts/staging_*`, `capacity_real.py` | Migraciones, schema, storage, telegram, stress | 2 | Env local-only, Supabase, Railway, Upstash | `--help`, dry-runs, evidence JSON | JSON outputs | Re-run guarded scripts | N/A | OWNERSHIP NOT DEFINED - RELEASE RISK |

## Bloqueos de release

- RTO/RPO: DECISION REQUERIDA.
- Backup/restore real proveedor: no probado.
- Alertas provider-as-code: no implementadas; alertas Telegram Admin de eventos concretos si existen en app.
- Scheduler real para watcher Base USDC: existe dentro del API runtime; falta prueba provider/staging con tx controlada y alerta real.
- Rollback Cloudflare/Railway: redeploy staging de SHA anterior esta documentado; rollback nativo proveedor no esta validado.
