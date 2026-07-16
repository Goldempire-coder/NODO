# SOP: Staging Schema Validation

SOP_ID: SOP-DB-002
Estado de validacion: PARTIALLY VALIDATED

## Procedimiento

```powershell
python scripts\validate_staging_schema.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --output evidence\slice_runs\schema_validation_<timestamp>.json
```

## Resultado esperado

- `failures: []`.
- Redis ping OK.
- Tablas/indices requeridos presentes.

## Si falla

- No aplicar migraciones a ciegas.
- Si falta ledger, usar reconciliacion solo despues de dry-run.
- Si falta un indice concreto, usar `apply_staging_single_migration.py` solo con aprobacion.
