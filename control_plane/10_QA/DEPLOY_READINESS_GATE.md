# DEPLOY_READINESS_GATE.md

Gate obligatorio antes de cualquier deploy productivo.

## No negociable

- Owner aprueba el corte.
- No hay secretos hardcodeados.
- Migraciones probadas en staging.
- Rollback documentado.
- Variables de entorno completas.
- Webhooks Telegram y Stripe verificados en staging.
- Backup y restore probados.
- Logs, metricas y alertas activos.
- Rate limits activos.
- Pruebas de concurrencia ejecutadas.
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
- Supabase staging disponible con pooling.
- Upstash Redis disponible.
- Storage privado disponible.
- Cloudflare R2 o Supabase Storage no expone `storage_path`.
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
