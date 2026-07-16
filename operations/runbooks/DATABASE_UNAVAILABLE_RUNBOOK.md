# RUNBOOK: Database unavailable

Estado de validacion: NOT VALIDATED

## SINTOMA

`/ready` devuelve 503 y check `database.ok=false`, o endpoints fallan con error DB.

## SEVERIDAD INICIAL

SEV-1.

## PRIMEROS CINCO MINUTOS

1. Confirmar `/ready`.
2. Revisar Supabase status/provider.
3. Revisar si hubo migracion reciente.
4. Congelar deploys.

## DIAGNOSTICO

```powershell
python scripts\validate_staging_schema.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --output evidence\slice_runs\db_unavailable_schema_<timestamp>.json
```

Solo ejecutar si el entorno es staging y guardrails estan correctos.

## MITIGACION

- Si es proveedor caido: comunicar incidente y esperar/failover si existe.
- Si es migracion reciente: evaluar rollback/restauracion.
- Si el proveedor de backup no esta disponible, usar `BACKUP_PROVIDER_UNAVAILABLE_RUNBOOK.md`.

## RECUPERACION

1. Restaurar conectividad DB si no hay perdida/corrupcion.
2. Si hay perdida/corrupcion, detener escrituras y usar `DB_CORRUPTION_OR_INCONSISTENCY_RUNBOOK.md`.
3. Cualquier restore debe seguir `operations/sops/RESTORE_SOP.md`.

Estado actual: no hay restore probado en repo ni evidencia provider verificada.

## PROHIBICIONES

- No resetear schema.
- No truncar tablas.
- No cambiar connection string sin confirmar entorno.
- No restaurar sobre produccion sin aprobacion explicita y plan de aborto.
