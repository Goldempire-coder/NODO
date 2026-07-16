# OPERATIONAL_READINESS_REPORT

Estado: OFFICIAL OWNER REVIEW
Fecha: 2026-07-11

## 1. DECISION

NOT OPERATIONALLY READY

NODO tiene una base tecnica fuerte para construir operaciones: health/readiness/version, scripts con guardrails, migraciones con ledger, storage smoke, Telegram smoke, tests, audit logs y stress tooling. Pero produccion queda bloqueada porque varios componentes Tier 0/Tier 1 no tienen aun ownership, alertas provider-as-code, backup/restore probado, rollback provider documentado, ni evidencia de game days.

## 2. MAPA DEL SISTEMA

Ver:

- `operations/SERVICE_CATALOG.md`
- `operations/SYSTEM_MAP.md`

Componentes Tier 0 principales:

- Backend API.
- Supabase PostgreSQL.
- Upstash Redis para idempotencia/rate/locks.
- Admin Web y Admin APIs.
- Creditos Base USDC verifier/watcher.
- Auth/JWT/Telegram validation.
- Staff/access control.

Componentes Tier 1 principales:

- Cliente Mini App.
- Negocio Mini App.
- Support Ticket Center.
- Telegram client bot.
- Telegram business intake bot.
- Supabase Storage privado.
- Jobs expire/escalate.

## 3. SOPs CREADOS

| SOP | Proposito | Validacion |
|---|---|---|
| `sops/DEPLOYMENT_SOP.md` | Predeploy y deploy gate | PARTIALLY VALIDATED |
| `sops/ROLLBACK_SOP.md` | Rollback seguro | NOT VALIDATED |
| `sops/POST_DEPLOY_VERIFICATION_SOP.md` | Verificacion post deploy | PARTIALLY VALIDATED |
| `sops/ENV_CONFIG_SOP.md` | Variables y secretos | PARTIALLY VALIDATED |
| `sops/STAGING_MIGRATION_SOP.md` | Migraciones staging con guardrails | PARTIALLY VALIDATED |
| `sops/STAGING_SCHEMA_VALIDATION_SOP.md` | Validacion schema | PARTIALLY VALIDATED |
| `sops/STORAGE_SMOKE_SOP.md` | Storage privado | PARTIALLY VALIDATED |
| `sops/TELEGRAM_WEBHOOK_SMOKE_SOP.md` | Smoke Telegram | PARTIALLY VALIDATED |
| `sops/SYNTHETIC_CLEANUP_SOP.md` | Limpieza sintetica | PARTIALLY VALIDATED |
| `sops/BUSINESS_ONBOARDING_ACCESS_SOP.md` | Alta/acceso negocio | NOT VALIDATED |
| `sops/BUSINESS_SUSPENSION_SOP.md` | Suspension negocio/acceso | NOT VALIDATED |
| `sops/CREDIT_TOPUP_INVESTIGATION_SOP.md` | Investigacion creditos | NOT VALIDATED |
| `sops/SUPPORT_TICKET_OPERATIONS_SOP.md` | Operacion soporte | PARTIALLY VALIDATED |
| `sops/AUDIT_REVIEW_SOP.md` | Revision audit logs | NOT VALIDATED |

## 4. RUNBOOKS CREADOS

| Runbook | Incidente cubierto | Validacion |
|---|---|---|
| `runbooks/API_5XX_RUNBOOK.md` | API devuelve 5xx | NOT VALIDATED |
| `runbooks/API_LATENCY_RUNBOOK.md` | API lenta | PARTIALLY VALIDATED |
| `runbooks/DATABASE_UNAVAILABLE_RUNBOOK.md` | DB no responde | NOT VALIDATED |
| `runbooks/DB_POOL_SATURATION_RUNBOOK.md` | conexiones/pool saturado | PARTIALLY VALIDATED |
| `runbooks/TELEGRAM_BOT_NO_RESPONSE_RUNBOOK.md` | bot no responde | PARTIALLY VALIDATED |
| `runbooks/BUSINESS_INTAKE_BOT_STUCK_RUNBOOK.md` | intake bot trabado | NOT VALIDATED |
| `runbooks/CREDITS_NOT_APPEARING_RUNBOOK.md` | creditos no aparecen | NOT VALIDATED |
| `runbooks/DUPLICATE_CREDITS_RUNBOOK.md` | creditos duplicados | NOT VALIDATED |
| `runbooks/STORAGE_UPLOAD_FAILURE_RUNBOOK.md` | storage falla | PARTIALLY VALIDATED |
| `runbooks/WORKER_NOT_PROCESSING_RUNBOOK.md` | worker no procesa | NOT VALIDATED |
| `runbooks/UNAUTHORIZED_ACCESS_RUNBOOK.md` | acceso indebido | NOT VALIDATED |
| `runbooks/PRIVACY_INCIDENT_RUNBOOK.md` | privacidad/secreto expuesto | NOT VALIDATED |
| `runbooks/DEPLOYMENT_DEFECT_RUNBOOK.md` | deploy defectuoso | NOT VALIDATED |

## 5. VACIOS OPERATIVOS

CRITICAL:

- No hay backup/restore probado para Supabase PostgreSQL.
- No hay owner tecnico/operativo definido para Tier 0/Tier 1.
- No hay alertas accionables configuradas como codigo o evidencia provider.
- No hay rollback provider documentado con comandos exactos.
- Scheduler real del watcher Base USDC no esta documentado como proceso operativo.

HIGH:

- No hay dashboard de observabilidad versionado.
- No hay runbook validado en nube para logs Railway por request ID.
- No hay RTO/RPO definidos.
- No hay game days ejecutados.
- No hay evidencia de restore de storage privado.

MEDIUM:

- SOPs de soporte/staff requieren simulacion.
- Cloud load runner existe solo para escenarios limitados.
- CSP aun tiene endurecimiento pendiente documentado en auditoria browser.

LOW:

- Se requiere normalizar ubicacion de evidencia operativa entre `operations/evidence` y `evidence/slice_runs`.

## 6. CAMBIOS DE CODIGO

No se modifico codigo de producto.

Cambios realizados: solo documentacion operativa nueva bajo `operations/`.

## 7. PRUEBAS REALIZADAS

Durante esta auditoria se validaron comandos seguros de lectura/inspeccion:

- Inventario root con PowerShell.
- Confirmacion de ausencia de `operations/`.
- `git status --short`.
- Lectura de `apps/api/app/main.py`.
- Lectura de `apps/api/app/core/config.py`.
- Lectura de `apps/api/app/routes/health.py`.
- Lectura de jobs, watcher, guardrails y smokes.
- Lectura de `railway.json`, `Dockerfile`, `docker-compose.local.yml`.
- Lectura de `control_plane/10_QA/DEPLOY_READINESS_GATE.md`.
- Lectura de `control_plane/11_OPERATIONS/ENVIRONMENT_VARIABLES.md`.
- Lectura de `control_plane/11_OPERATIONS/REAL_SERVICES_STAGING_SETUP.md`.

No se ejecutaron servicios reales, migraciones, deploys, cleanup, storage smoke mutante ni Telegram send.

## 8. PROCEDIMIENTOS NO VALIDADOS

- Deploy real Railway/Cloudflare.
- Rollback real Railway/Cloudflare.
- Backup Postgres.
- Restore Postgres.
- Restore storage privado.
- Recovery de Base USDC watcher.
- Simulacion de DB caida.
- Simulacion de Redis caido.
- Simulacion de webhook duplicado.
- Game day de deploy defectuoso.

## 9. RIESGOS DE PRODUCCION

### CRITICAL

- Produccion no debe abrirse sin backup/restore probado.
- Produccion no debe abrirse sin alertas para 5xx, readiness, DB, Redis, creditos duplicados y acceso indebido.
- Produccion no debe abrirse sin owner/on-call definido.

### HIGH

- Rollback provider no esta automatizado ni validado.
- Watcher Base USDC necesita scheduling operativo y alertas.
- Observabilidad no alcanza aun para diagnostico completo sin conocimiento del creador.

### MEDIUM

- Runbooks estan escritos pero no ejecutados en staging.
- Cloud load/stress remoto todavia debe ampliarse segun los siguientes pasos de escalabilidad.

### LOW

- Plantillas operativas iniciales deben madurar con cada nuevo slice.

## 10. VEREDICTO

REJECTED FOR PRODUCTION OPERATIONS

NODO puede seguir avanzando en staging y validaciones controladas. No esta listo para operacion productiva hasta cerrar los bloqueos Tier 0/Tier 1.
