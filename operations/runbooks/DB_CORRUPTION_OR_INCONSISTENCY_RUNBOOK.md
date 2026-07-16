# RUNBOOK: DB corruption or data inconsistency

Estado de validacion: NOT VALIDATED
Ultima actualizacion: 2026-07-11

## Sintoma

- Ledger/wallet inconsistente.
- Orden sin state event esperado.
- Audit faltante para mutacion sensible.
- Constraints o indexes faltantes.
- Datos restaurados no coinciden con invariantes.

## Severidad inicial

SEV-1 si afecta dinero, permisos, audit o datos privados.

## Primeros cinco minutos

1. Congelar deploys y migraciones.
2. Confirmar entorno.
3. Guardar request IDs/evidencia sin datos privados.
4. Ejecutar solo checks read-only aprobados.

## Diagnostico

```powershell
python scripts\validate_staging_schema.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --output evidence\slice_runs\db_integrity_schema_<timestamp>.json
```

Integrity checks completos: COMMAND NOT AVAILABLE hasta 31C/31E.

## Mitigacion

- No escribir datos manualmente.
- Si afecta creditos/ordenes, pausar operaciones afectadas por procedimiento owner.
- Escalar a owner + DB reliability.

## Recuperacion

Usar `RESTORE_SOP.md` solo con aprobacion.

## Prohibiciones

- No truncar tablas.
- No editar saldos manualmente.
- No borrar audit logs.
- No ejecutar restore sobre produccion sin plan.
