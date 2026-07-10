# AUDIT_EVENTS.md

## Eventos obligatorios

No se debe auditar cada busqueda de marketplace.

Eventos permitidos:

- `runtime_capacity_guard_triggered`
- `db_pool_saturation_detected`
- `marketplace_cache_invalidated`
- `marketplace_cache_unavailable`

## Reglas

- No incluir tokens.
- No incluir queries completas con datos sensibles.
- No incluir `account_value`.
- No incluir `storage_path`.
- No saturar `audit_logs` con eventos por request.

