# RUNBOOK: Deploy incompatible with schema

Estado de validacion: NOT VALIDATED
Ultima actualizacion: 2026-07-11

## Sintoma

- Error comienza justo despues de deploy o migracion.
- Backend nuevo espera columna/constraint que no existe.
- Backend viejo no entiende schema nuevo.

## Severidad inicial

SEV-1/2 segun impacto.

## Primeros cinco minutos

1. Congelar deploys.
2. Capturar `/version`, `/ready` y ultimo migration plan.
3. Identificar si hubo migracion.
4. No ejecutar down migration improvisada.

## Diagnostico

```powershell
python scripts\validate_staging_schema.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --output evidence\slice_runs\schema_deploy_incompat_<timestamp>.json
```

## Mitigacion

- Si no hubo migracion incompatible: considerar provider rollback con `ROLLBACK_SOP.md`.
- Si hubo migracion: escalar; rollback app puede ser inseguro.

## Prohibiciones

- No hacer deploy encima sin causa.
- No resetear schema.
- No modificar migraciones ya aplicadas sin nuevo slice.
