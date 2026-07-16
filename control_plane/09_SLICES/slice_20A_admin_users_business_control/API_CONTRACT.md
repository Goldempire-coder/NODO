# API_CONTRACT.md

Todos los endpoints usan `/api/v1`, JWT admin valido, backend RBAC y errores seguros.

## GET /api/v1/admin/users

Query:
- `phone`
- `telegram_id`
- `username`
- `role`
- `status`
- `cursor`
- `limit` 1..50

Rules:
- `telegram_id` completo solo se devuelve a `admin`/`super_admin`.
- `support` recibe `telegram_id_masked` y `phone_masked`, nunca valores completos.
- Cursor pagination; no offset.
- No devuelve tokens, session hashes, refresh hashes, secrets ni storage paths.

## GET /api/v1/admin/users/{id}

Devuelve detalle operativo seguro:
- usuario enmascarado por defecto;
- links de negocio;
- negocios asociados;
- contadores operativos;
- capabilities admin calculadas para la vista.

No devuelve tokens, refresh token hashes, session internals, raw auth headers, secretos, `storage_path` ni `account_value`.

## POST /api/v1/admin/users/{id}/suspend

Headers:
- `Authorization`
- `Idempotency-Key`
- `X-Request-Id`

Body:

```json
{
  "reason": "Actividad sospechosa pendiente de revision"
}
```

Response: usuario con `status = restricted`.

Rules:
- `admin` y `super_admin` segun protecciones de rol.
- `support` recibe `FORBIDDEN`.
- Reason obligatorio.
- Audit `user_suspended`.
- Idempotente por key/payload.

## POST /api/v1/admin/users/{id}/reactivate

Reactiva `restricted|dormant -> active`.

Rules:
- Reason obligatorio.
- `Idempotency-Key` obligatorio.
- Audit `user_reactivated`.
- No reactiva usuarios `blocked` en 20A.

## POST /api/v1/admin/users/{id}/block

Bloquea `active|restricted|dormant -> blocked`.

Rules:
- Reason obligatorio.
- `Idempotency-Key` obligatorio.
- Audit `user_blocked`.
- Protege ultimo `super_admin active`.

## GET /api/v1/admin/businesses/{id}/access-links

Lista links del negocio con datos de usuario enmascarados.

## GET /api/v1/admin/users/{id}/access-links

Lista links del usuario con datos de negocio y estado de link.

## Mutaciones access links

Se reutilizan endpoints contratados:
- `POST /api/v1/admin/businesses/{id}/access-links`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/suspend`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/reactivate`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/revoke`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/block`

Todas requieren `admin|super_admin`, reason, `Idempotency-Key` y audit.

## Errores

- UNAUTHENTICATED
- FORBIDDEN
- USER_NOT_FOUND
- USER_STATUS_INVALID
- USER_STATUS_TRANSITION_INVALID
- USER_STATUS_MUTATION_NOT_ALLOWED
- LAST_SUPER_ADMIN_REQUIRED
- BUSINESS_NOT_FOUND
- BUSINESS_ACCESS_LINK_NOT_FOUND
- BUSINESS_ACCESS_LINK_REQUIRED
- ADMIN_REASON_REQUIRED
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_CONFLICT
- IDEMPOTENCY_PAYLOAD_MISMATCH
- RATE_LIMITED
