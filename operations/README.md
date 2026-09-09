# NODO Operations

Estado: OFFICIAL OPERATIONS PACKAGE - PILOT ALIGNMENT
Ultima actualizacion: 2026-09-09

Este directorio documenta como operar, diagnosticar y recuperar NODO con los componentes reales encontrados en el repositorio.

Decision operativa actual: NOT READY FOR OPEN PRODUCTION.

NODO puede prepararse para un piloto controlado solo con evidencia Owner, limites pequenos y riesgos aceptados. Produccion abierta sigue bloqueada.

Motivo: existen health checks, readiness checks, guardrails de staging, migraciones seguras, smokes para storage/Telegram, deploy web con guardrails, alertas Telegram Admin para eventos concretos y modo emergencia. Siguen faltando rollback provider validado, backup/restore real probado, ownership formal con backup, dashboards/alertas provider-as-code y evidencia de recuperacion de Tier 0/Tier 1.

## Reglas de uso

- No incluir secretos reales.
- No ejecutar comandos mutantes contra staging sin `--confirm-staging` y `STAGING_VALIDATION_ACK`.
- No ejecutar acciones destructivas en produccion.
- No declarar recuperacion solo porque una alerta desaparecio.
- Guardar evidencia en `operations/evidence/` o `evidence/slice_runs/`.
- Si un SOP dice `BLOCKED`, no improvisar. Escalar.

## Estructura

- `SERVICE_CATALOG.md`: componentes reales, tiers, dependencias y gaps.
- `SYSTEM_MAP.md`: mapa operativo y flujos.
- `INCIDENT_RESPONSE.md`: proceso oficial de incidentes.
- `SEVERITY_MATRIX.md`: criterios SEV.
- `ON_CALL_PLAYBOOK.md`: playbook de las 2 AM.
- `MONITORING.md`: observabilidad actual y faltante.
- `STAGING_CONCURRENCY_POLICY.md`: interpretacion oficial de c25/c50 product gates y c100+ como probe de transporte/infra.
- `ALERT_CATALOG.md`: alertas accionables requeridas.
- `PILOT_CONTROLLED_GATE.md`: gate minimo para piloto pequeno sin declarar produccion abierta.
- `ACCESS_CONTROL.md`: controles operativos de acceso.
- `CHANGE_MANAGEMENT.md`: cambios, deploy y rollback.
- `DISASTER_RECOVERY.md`: backup/restore y riesgos.
- `BACKUP_RESTORE_MATRIX.md`: matriz Tier/RTO/RPO/ownership/backup/restore por componente.
- `POSTMORTEM_TEMPLATE.md`: plantilla sin culpa.
- `sops/`: procedimientos operativos.
- `runbooks/`: diagnostico por sintoma.
- `evidence/`: espacio para evidencia operacional.

## Backup/restore y DR

El paquete oficial de backup/restore queda documentado, pero no validado contra proveedor real. Antes de produccion abierta deben existir evidencias de:

- Backup/restore de Supabase PostgreSQL.
- Restore de Supabase Storage privado y reconciliacion con `file_assets`.
- Recuperacion de secrets/env vars sin imprimir secretos.
- Validacion de integridad post-restore.
- Rollback provider documentado para Railway y Cloudflare.
- Owners asignados por componente.

Los SOPs relevantes son:

- `sops/BACKUP_SOP.md`
- `sops/RESTORE_SOP.md`
- `sops/STORAGE_RESTORE_SOP.md`
- `sops/SECRETS_RECOVERY_SOP.md`
- `sops/POST_RESTORE_INTEGRITY_VALIDATION_SOP.md`
- `sops/ROLLBACK_SOP.md`

Los runbooks de DR relevantes son:

- `runbooks/DATABASE_UNAVAILABLE_RUNBOOK.md`
- `runbooks/DB_CORRUPTION_OR_INCONSISTENCY_RUNBOOK.md`
- `runbooks/STORAGE_PRIVATE_LOSS_RUNBOOK.md`
- `runbooks/PARTIAL_DB_RESTORE_WITHOUT_STORAGE_RUNBOOK.md`
- `runbooks/SECRETS_COMPROMISED_OR_LOST_RUNBOOK.md`
- `runbooks/SCHEMA_DEPLOY_INCOMPATIBILITY_RUNBOOK.md`
- `runbooks/REDIS_LOST_ACTIVE_OPERATION_RUNBOOK.md`
- `runbooks/AUDIT_LOG_TRACEABILITY_RISK_RUNBOOK.md`
- `runbooks/BACKUP_PROVIDER_UNAVAILABLE_RUNBOOK.md`

## Validacion

Los documentos estan conectados a comandos y archivos reales del repo. Para piloto, usar `PILOT_CONTROLLED_GATE.md`. Para produccion abierta, cualquier SOP marcado `NOT VALIDATED`, `COMMAND NOT AVAILABLE`, `PROVIDER_ACCESS_REQUIRED` o `BLOCKED` sigue bloqueando.
