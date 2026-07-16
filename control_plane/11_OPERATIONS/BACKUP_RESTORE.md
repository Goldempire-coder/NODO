# BACKUP_RESTORE.md

Estado: OFFICIAL CONTRACT - NOT VALIDATED
Ultima actualizacion: 2026-07-11

## Decision

NODO no puede declararse listo para uso real hasta tener backup, restore e integridad post-restore probados para componentes Tier 0 y Tier 1.

El texto historico "Backups diarios DB. Retencion 7-30 dias" queda reemplazado por este contrato:

- La existencia de backups provider es `PROVIDER_ACCESS_REQUIRED` hasta verificarse en Supabase/Railway/Cloudflare/Upstash.
- La retencion final y el RTO/RPO son `DECISION REQUIRED` hasta aprobacion owner.
- Ningun restore se considera probado sin evidencia guardada en `operations/evidence/` o `evidence/slice_runs/`.

## RTO/RPO propuestos para decision owner

Estos valores son propuesta tecnica, no aceptacion final.

| Tier | Ejemplos | RTO propuesto | RPO propuesto | Estado |
|---|---|---:|---:|---|
| Tier 0 | auth, permisos, creditos, ledger, ordenes, audit, storage privado sensible | 4 horas | 15 minutos | DECISION REQUIRED |
| Tier 1 | soporte, intake, bots, ads operativos, notificaciones principales | 8 horas | 1 hora | DECISION REQUIRED |
| Tier 2 | cache, dashboards agregados, evidencia sintetica, tooling staging | 24 horas | 24 horas | DECISION REQUIRED |
| Tier 3 | artefactos no criticos, outputs regenerables | 72 horas | best effort | DECISION REQUIRED |

## Principios

- Postgres/Supabase es fuente canonica para datos de negocio, dinero, permisos y audit.
- Supabase Storage/R2 privado es fuente canonica para documentos/evidencias referenciadas por `file_assets`.
- Redis/Upstash no debe ser fuente canonica de dinero, ordenes, permisos ni audit.
- Backups provider no sustituyen restore drill.
- Restore DB sin storage puede dejar evidencia privada irrecuperable.
- Restore storage sin DB puede dejar objetos huerfanos.
- Down migrations no son backup.
- Cleanup sintetico no es restore.
- Deploy rollback no es data restore.

## Componentes cubiertos

- Supabase PostgreSQL: todas las tablas canonicas.
- Supabase Storage o R2 privado: buckets de documentos/evidencias/adjuntos/intake.
- Upstash Redis: rate limit, idempotency, locks y cache runtime.
- Railway backend: imagen/config/env.
- Cloudflare Pages frontend: build exportado/env publica.
- Secrets/env vars: Railway, Cloudflare, Telegram, Supabase, Upstash, Base RPC.
- Telegram bots/webhooks.
- Base USDC watcher/verifier.
- Audit logs.
- Notification jobs.

## Estados canonicos de backup/restore

- `UNKNOWN`: no verificable desde repo/evidencia local.
- `PROVIDER_ACCESS_REQUIRED`: requiere dashboard/API provider.
- `DOCUMENTED_NOT_VALIDATED`: existe SOP, no hay evidencia de ejecucion.
- `PARTIALLY_VALIDATED`: probado en local o smoke parcial sin restore real.
- `VALIDATED_STAGING`: restore probado en staging/entorno aislado con evidencia.
- `PRODUCTION_READY`: solo owner puede aprobar tras restore recurrente y alertas.

## Criterio minimo para desbloquear produccion

- RTO/RPO aprobados por owner.
- Owner tecnico, owner operativo y backup owner definidos para Tier 0/Tier 1.
- Backup location y permisos documentados.
- Restore Postgres probado en entorno aislado.
- Restore storage privado probado en entorno aislado.
- Validacion DB + storage post-restore ejecutada.
- Secrets recovery documentado y probado sin imprimir secretos.
- Rollback provider documentado con comandos o procedimiento exacto.
- Alertas para backup/restore failure definidas y configuradas.

## Referencias operativas

- `operations/BACKUP_RESTORE_MATRIX.md`
- `operations/DISASTER_RECOVERY.md`
- `operations/sops/BACKUP_SOP.md`
- `operations/sops/RESTORE_SOP.md`
- `operations/sops/STORAGE_RESTORE_SOP.md`
- `operations/sops/SECRETS_RECOVERY_SOP.md`
- `operations/sops/POST_RESTORE_INTEGRITY_VALIDATION_SOP.md`
