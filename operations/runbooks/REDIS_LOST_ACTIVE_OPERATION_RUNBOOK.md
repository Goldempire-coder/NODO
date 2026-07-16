# RUNBOOK: Redis lost during active operation

Estado de validacion: NOT VALIDATED
Ultima actualizacion: 2026-07-11

## Sintoma

- `/ready` falla Redis.
- Rate limit/idempotency/locks fallan.
- Marketplace cache miss masivo.
- Jobs no toman lock.

## Severidad inicial

SEV-1 si afecta idempotency/locks de dinero, creditos, ordenes o jobs.
SEV-2 si afecta solo cache publica degradable.

## Primeros cinco minutos

1. Confirmar `/ready`.
2. Revisar Upstash provider status.
3. No cambiar Redis URL sin confirmar entorno.
4. Congelar mutaciones sensibles si idempotency/locks no son confiables.

## Diagnostico

```powershell
python scripts\validate_staging_schema.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --output evidence\slice_runs\redis_lost_<timestamp>.json
```

## Recuperacion

- Reconfigurar Redis provider/URL solo con owner approval.
- DB sigue siendo autoridad para dinero/ordenes/permisos.
- Cache marketplace puede reconstruirse.

## Prohibiciones

- No usar Redis stale para autorizar mutaciones.
- No desactivar idempotency para "desbloquear" pagos/creditos.
