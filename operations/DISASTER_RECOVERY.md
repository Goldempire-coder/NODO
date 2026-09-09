# DISASTER_RECOVERY

Estado: BLOCKED FOR OPEN PRODUCTION - PILOT RISK ACCEPTANCE REQUIRED
Ultima actualizacion: 2026-09-09

## Decision operativa

Produccion abierta sigue bloqueada. NODO no tiene restore real validado para Tier 0/Tier 1.

Un piloto controlado puede evaluarse solo si el Owner acepta por escrito el riesgo de no tener restore provider probado y mantiene usuarios/negocios/montos limitados.

Este documento define el marco de DR. No afirma que exista evidencia provider ni que el restore ya fue probado.

## Estado real

Existe:

- Migraciones up/down en `database/migrations`.
- Ledger de migraciones staging en tooling.
- Guardrails staging.
- Schema validation local/staging.
- Smoke de storage privado.
- Smoke Telegram.
- Health/readiness/version.
- Rollback drill local hasta slice 11 sobre DB desechable con datos sinteticos.
- Tooling local sintetico de backup/restore en `scripts/local_synthetic_backup_restore.py`.
- Rollback staging por redeploy de SHA anterior documentado en `sops/ROLLBACK_SOP.md`.
- Alertas Telegram Admin para intake, disputas, compras de creditos que requieren atencion, prueba y modo emergencia.

No existe todavia:

- Script de backup Postgres real contra proveedor.
- Script de restore Postgres real contra proveedor.
- Restore Supabase probado.
- Restore storage privado probado.
- Drill DB+storage con integridad post-restore.
- Confirmacion provider de backups/retencion.
- Backup de secretos/env vars.
- Comando provider versionado para Railway/Cloudflare rollback.
- Evidencia de restore en staging aislado.

## RTO/RPO

Ver `operations/BACKUP_RESTORE_MATRIX.md`.

Todos los RTO/RPO quedan `DECISION REQUIRED` hasta aprobacion owner.

## Prioridad DR

1. Tier 0: dinero, auth, permisos, audit, datos privados.
2. Tier 1: operacion principal cliente/negocio/admin/bots.
3. Tier 2: degradable o reconstruible.
4. Tier 3: no critico.

## Prohibiciones

- No probar restore sobre produccion.
- No truncar datos para demostrar recuperacion.
- No ejecutar `down.sql` como sustituto de backup.
- No confiar solo en backups automaticos provider sin restore test.
- No exportar datos reales sin contrato privacy/owner.
- No restaurar DB sin plan para storage privado.
- No restaurar storage sin validar `file_assets`.
- No rotar secretos durante incidente sin `SECRETS_RECOVERY_SOP`.

## Fases aprobadas futuras

- 31C: tooling seguro local/sintetico de backup metadata y verification. Existe script local; falta evidencia actualizada si no hay run reciente.
- 31D: restore drill staging/entorno aislado con proveedor.
- 31E: integrity validation after restore.
- 31F: recurring restore test policy.

## Estado de produccion

BACKUP_RESTORE_NOT_READY_FOR_PRODUCTION.
