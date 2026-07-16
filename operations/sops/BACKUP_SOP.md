# SOP: Backup

SOP_ID: SOP-BACKUP-001
Estado de validacion: NOT VALIDATED
Ultima actualizacion: 2026-07-11

## Proposito

Definir como preparar y verificar backups de NODO sin exportar datos reales hasta tener aprobacion owner.

## Alcance

- Supabase PostgreSQL.
- Supabase Storage privado o R2 privado.
- Configuracion Railway/Cloudflare.
- Secrets/env vars.
- Evidencia operacional.

## Cuando usar

- Antes de declarar readiness productiva.
- Antes de cambios Tier 0/Tier 1 con riesgo de datos.
- Como preparacion de restore drill 31C/31D.

## Cuando no usar

- Durante incidente activo sin Incident Commander.
- Contra produccion sin aprobacion explicita.
- Para exportar datos reales sin contrato privacy/owner.

## Permisos requeridos

- Owner approval.
- Acceso provider de solo lectura para verificar backup metadata.
- Acceso a entorno aislado para drills.

## Comandos reales

COMMAND NOT AVAILABLE para backup real.

Comandos seguros existentes solo para validacion previa:

```powershell
python scripts\validate_staging_schema.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --output evidence\slice_runs\backup_precheck_schema_<timestamp>.json
```

## Riesgos

- Export accidental de datos reales.
- Secret en logs/evidence.
- Backup DB sin storage.
- Backup storage sin DB metadata.
- Falsa confianza en provider sin restore test.

## Criterio de exito

- Backup source identificado por provider.
- Retencion visible y documentada.
- Permisos de restore identificados.
- Evidencia sin secretos.
- Restore drill planificado.

## Criterio de aborto

- Se detecta entorno production sin aprobacion explicita.
- Aparece secreto en output.
- Provider access no disponible.
- Backup location no verificable.

## Evidencia requerida

- Fecha/hora.
- Entorno.
- Provider/project id redacted.
- Retencion configurada.
- Backup id redacted si provider lo entrega.
- Persona aprobadora.

## Estado

BLOCKED hasta construir tooling 31C y obtener provider access.
