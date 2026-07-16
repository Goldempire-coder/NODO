# DATA_CONTRACT.md

## Tablas activas

No se requiere tabla nueva para MVP 20A.

Se usan:
- `users`
- `businesses`
- `business_access_links`
- `audit_logs`
- idempotency store existente para mutaciones admin

## users

Campos relevantes:
- `id`
- `telegram_id`
- `username`
- `first_name`
- `last_name`
- `phone`
- `role`
- `status`
- `trust_level`
- `created_at`
- `updated_at`
- `last_seen_at`

`users.status` canonico:
- `active`
- `restricted`
- `blocked`
- `dormant`

Regla 20A:
- Admin action `suspend` setea `users.status = restricted`.
- Admin action `reactivate` setea `restricted|dormant -> active`.
- Admin action `block` setea `active|restricted|dormant -> blocked`.
- `blocked` no se borra ni elimina historial.
- Reason de mutaciones vive en audit/idempotency metadata, no en una nueva columna de `users`.

## business_access_links

Se mantiene el modelo canonico de 14B1:
- `active`
- `suspended`
- `revoked`
- `blocked`

20A agrega contratos de lectura por usuario y negocio; las mutaciones existentes siguen exigiendo reason, idempotencia y audit.

## Indices requeridos para build

- `users(telegram_id)` unique ya existente.
- `users(status, created_at desc)` ya existente.
- `users(role, status)` ya existente.
- `users(phone)` parcial cuando `phone is not null` para busqueda admin si no existe.
- `lower(users.username)` parcial cuando `username is not null` para busqueda admin si no existe.
- `business_access_links(business_id, status)` ya contratado.
- `business_access_links(user_id, status)` ya contratado.
- `business_access_links(telegram_id_snapshot, status)` ya contratado.

Si una migracion no puede crear indices faltantes sin riesgo, el builder debe bloquear con `BLOCKED_BY_MISSING_CONTRACT` o `BLOCKED_BY_SECURITY_GAP`.
