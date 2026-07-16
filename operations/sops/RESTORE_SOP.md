# SOP: Restore

SOP_ID: SOP-RESTORE-001
Estado de validacion: NOT VALIDATED
Ultima actualizacion: 2026-07-11

## Proposito

Restaurar NODO desde backup de forma controlada, verificable y sin afectar produccion.

## Alcance

- Restore Postgres/Supabase.
- Restore DB + storage privado.
- Revalidacion de app Railway/Cloudflare despues del restore.

## Cuando usar

- Restore drill aprobado en entorno aislado.
- Incidente de datos confirmado con aprobacion owner/Incident Commander.

## Cuando no usar

- Para corregir bugs de aplicacion.
- Para revertir deploy sin perdida/corrupcion de datos.
- Sobre produccion sin plan aprobado.
- Si storage privado no tiene plan compatible.

## Permisos requeridos

- Owner approval.
- Incident Commander.
- Acceso provider Supabase.
- Acceso a entorno aislado.

## Comandos reales

COMMAND NOT AVAILABLE para restore real.

Comandos existentes post-restore:

```powershell
python scripts\validate_staging_schema.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --output evidence\slice_runs\restore_schema_<timestamp>.json
```

```powershell
python scripts\staging_storage_smoke.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --run-id restore_storage_<timestamp> --confirm-staging --output evidence\slice_runs\restore_storage_<timestamp>.json
```

## Riesgos

- Restaurar datos viejos encima de datos nuevos.
- Perder audit trail.
- Duplicar creditos/ledger.
- Dejar `file_assets` apuntando a objetos inexistentes.
- Rehabilitar usuarios/staff/access links revocados.
- Ejecutar app incompatible con schema restaurado.

## Criterio de exito

- Restore ejecutado solo en entorno aislado o aprobado.
- Schema validation OK.
- Integridad post-restore OK.
- Storage object existence OK para muestra aprobada.
- Health/ready/version OK.
- No secretos en evidencia.

## Criterio de aborto

- Target no es entorno aprobado.
- Restore provider falla.
- Integrity validation falla.
- `audit_logs` faltan o quedan truncados inesperadamente.
- Wallet/ledger inconsistente.

## Evidencia requerida

- Backup id redacted.
- Restore target.
- Timestamp inicio/fin.
- Validaciones ejecutadas.
- Request IDs.
- Resultado de `POST_RESTORE_INTEGRITY_VALIDATION_SOP`.

## Estado

BLOCKED hasta 31C/31D.
