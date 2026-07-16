# SOP: Synthetic Data Cleanup

SOP_ID: SOP-CLEANUP-001
Estado de validacion: PARTIALLY VALIDATED

## Dry-run

```powershell
python scripts\staging_cleanup_synthetic_run.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --run-id <RUN_ID> --output evidence\slice_runs\cleanup_<RUN_ID>_dry.json
```

## Apply

Solo con aprobacion:

```powershell
$env:STAGING_VALIDATION_ACK = "<RUN_ID>"
python scripts\staging_cleanup_synthetic_run.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --run-id <RUN_ID> --apply --confirm-staging --output evidence\slice_runs\cleanup_<RUN_ID>_apply.json
```

## Abort

- Run ID no corresponde al test.
- Guardrails fallan.
- Conteos inesperados.
