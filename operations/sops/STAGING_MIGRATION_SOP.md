# SOP: Staging Migration

SOP_ID: SOP-DB-001
Estado de validacion: PARTIALLY VALIDATED

## Proposito

Aplicar migraciones en staging con guardrails.

## Procedimiento dry-run

```powershell
$runId = "staging_migration_" + (Get-Date -Format "yyyyMMddHHmmss")
python scripts\apply_staging_migrations.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --run-id $runId --plan --output evidence\slice_runs\$runId-plan.json
```

## Procedimiento apply

Solo con aprobacion owner:

```powershell
$runId = "staging_migration_" + (Get-Date -Format "yyyyMMddHHmmss")
$env:STAGING_VALIDATION_ACK = $runId
python scripts\apply_staging_migrations.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --run-id $runId --apply --confirm-staging --output evidence\slice_runs\$runId-apply.json
```

## Resultado esperado

- Guardrails OK.
- Sin checksum mismatch.
- Ledger actualizado.

## Abort

- `CHECKSUM_MISMATCH`.
- `MIGRATION_LOCK_NOT_ACQUIRED`.
- Cualquier drift sin investigacion.

## Rollback

No ejecutar down migrations contra staging sin plan especifico.
