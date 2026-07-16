# RUNBOOK: DB pool or connection saturation

Estado de validacion: PARTIALLY VALIDATED

## SINTOMA

Errores `too many clients`, `DB_POOL_SATURATED`, timeouts o p95 alto con DB sana.

## SEVERIDAD INICIAL

SEV-1/2.

## PRIMEROS CINCO MINUTOS

1. Revisar Railway worker count.
2. Revisar `NODO_DB_POOL_MAX_SIZE`.
3. Calcular `WEB_CONCURRENCY x NODO_DB_POOL_MAX_SIZE`.
4. Comparar contra limite Supabase.

## DIAGNOSTICO

- Buscar en logs: `too many clients`, `DB_POOL_SATURATED`, `OperationalError`.
- Revisar evidencia de capacity si existe.

## MITIGACION

- Bajar workers o pool si excede limite.
- Reducir trafico de stress.
- Mantener mutaciones con auth fuerte e idempotencia.

## PROHIBICIONES

- No subir workers a ciegas.
- No aumentar pool sin limite Supabase.
