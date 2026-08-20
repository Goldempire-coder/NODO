# DEPLOY_READINESS_GATE.md

Gate obligatorio antes de cualquier deploy productivo.

## No negociable

- Owner aprueba el corte.
- `control_plane/11_OPERATIONS/STABILITY_GATE.md` ejecutado y sin hallazgos HIGH/CRITICAL abiertos.
- Existe manifiesto pre-deploy aprobado en `control_plane/13_HANDOFF/`.
- No hay archivos runtime importados que queden fuera del release candidate.
- No hay secretos hardcodeados.
- Migraciones probadas en staging.
- Rollback documentado.
- Variables de entorno completas.
- Webhooks Telegram y Stripe verificados en staging.
- Backup y restore probados.
- Backup/restore probado significa evidencia verificable de DB, storage privado, secrets recovery, rollback compatible con schema y validacion de integridad post-restore.
- Logs, metricas y alertas activos.
- Rate limits activos.
- Pruebas de concurrencia ejecutadas.
- Staging concurrency policy aplicada: c25/c50 pueden ser gates de producto; c100+ es probe de infraestructura/transporte y no bloquea producto por si solo si backend p95 esta bajo y domina TTFB/tcp_connect.
- `00_GOVERNANCE/ENGINEERING_GUARDRAILS.md` cumplido y sin hallazgos CRITICAL/HIGH abiertos.
- BUILDER_REPORT de cada slice entregado.

## Checklist tecnico

- Frontend build sin errores.
- Backend tests pasan.
- Workers levantan y procesan jobs.
- Cloudflare Pages deploy apunta al build correcto de `apps/web`.
- Railway API responde `/health`, `/ready` y `/version`.
- Railway worker/job process no corre duplicado sin lock.
- DB migrations aplican desde cero.
- DB migrations aplican sobre staging existente.
- Restore drill de Supabase PostgreSQL ejecutado en entorno aislado y validado.
- Restore drill de Supabase Storage privado ejecutado con reconciliacion `file_assets`.
- Secrets/env recovery validado sin imprimir secretos.
- Post-restore integrity validation ejecutado y aprobado.
- Supabase staging disponible con pooling.
- Upstash Redis disponible.
- Storage privado disponible.
- Cloudflare R2 o Supabase Storage no expone rutas internas de storage.
- Emails/notificaciones si aplican en modo seguro.
- Admin panel protegido.
- Audit logs escriben eventos.
- Stripe test webhook firmado acredita exactamente una vez.
- Telegram Mini App test valida `initData` real.

## Checklist de riesgo

- No hay copy de garantia financiera.
- No hay lenguaje de escrow.
- No hay auto-aprobacion manual de creditos.
- No hay estados inventados.
- No hay endpoints admin sin RBAC.
- No hay evidencia publica sin firma temporal.
- No hay doble acreditacion por webhook repetido.
- No hay doble creacion de orden por doble click/retry.

## Resultado permitido

El unico resultado permitido de este gate es:

- BLOCKED: falta evidencia.
- READY_FOR_OWNER_REVIEW: evidencia tecnica completa.

`READY_FOR_REAL_USE` no puede ser declarado por builder.

Si cualquier restore queda `UNKNOWN`, `PROVIDER_ACCESS_REQUIRED`, `COMMAND NOT AVAILABLE` o `NOT VALIDATED`, el deploy productivo queda `BLOCKED`.
