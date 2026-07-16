# RUNBOOK: Audit log traceability risk

Estado de validacion: NOT VALIDATED
Ultima actualizacion: 2026-07-11

## Sintoma

- Mutacion sensible sin audit esperado.
- `audit_logs` ausente, truncado o corrupto.
- No se puede reconstruir una accion admin/crediticia/access.

## Severidad inicial

SEV-1.

## Primeros cinco minutos

1. Congelar mutaciones sensibles afectadas.
2. No borrar ni compactar logs.
3. Guardar request IDs, correlation IDs y timestamps.
4. Revisar si hubo restore/migracion/deploy.

## Diagnostico

COMMAND NOT AVAILABLE para audit integrity completo hasta 31C/31E.

Checks permitidos:

- Conteo de eventos por ventana.
- Comparar audit con recurso afectado.
- Revisar `request_id` de accion sensible.

## Recuperacion

- Si audit se perdio por restore, el restore no puede declararse exitoso.
- Escalar a owner/security.

## Prohibiciones

- No recrear audit logs manualmente sin procedimiento forense.
- No ocultar gaps de trazabilidad.
