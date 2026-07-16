# ERROR_CASES.md

- `USER_NOT_FOUND`: usuario inexistente o no visible para el actor.
- `USER_STATUS_INVALID`: status fuera del enum canonico.
- `USER_STATUS_TRANSITION_INVALID`: transicion no permitida.
- `USER_STATUS_MUTATION_NOT_ALLOWED`: actor no puede mutar ese usuario/rol.
- `LAST_SUPER_ADMIN_REQUIRED`: la accion dejaria sin `super_admin active`.
- `BUSINESS_ACCESS_LINK_NOT_FOUND`: link inexistente o no visible.
- `BUSINESS_ACCESS_LINK_REQUIRED`: operacion requiere link existente.
- `ADMIN_REASON_REQUIRED`: reason faltante o vacio.
- `IDEMPOTENCY_KEY_REQUIRED`: mutacion critica sin key.
- `IDEMPOTENCY_CONFLICT`: key en conflicto.
- `IDEMPOTENCY_PAYLOAD_MISMATCH`: misma key con payload distinto.
- `FORBIDDEN`: actor sin permiso.
- `UNAUTHENTICATED`: JWT faltante/invalido.
- `RATE_LIMITED`: limite de accion admin.

Errores no deben incluir stack traces, SQL, secretos, tokens, `storage_path`, `account_value` ni datos sensibles completos.
