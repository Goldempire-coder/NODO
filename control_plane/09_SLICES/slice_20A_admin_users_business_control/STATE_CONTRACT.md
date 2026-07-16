# STATE_CONTRACT.md

## users.status

Transiciones permitidas por 20A:

- `active -> restricted` por `POST /api/v1/admin/users/{id}/suspend`.
- `restricted -> active` por `POST /api/v1/admin/users/{id}/reactivate`.
- `dormant -> active` por `POST /api/v1/admin/users/{id}/reactivate`.
- `active -> blocked` por `POST /api/v1/admin/users/{id}/block`.
- `restricted -> blocked` por `POST /api/v1/admin/users/{id}/block`.
- `dormant -> blocked` por `POST /api/v1/admin/users/{id}/block`.

Transiciones no permitidas en 20A:
- `blocked -> active` salvo contrato futuro explicito de unblock/review.
- hard delete de usuario.
- cambio de rol desde estas acciones.
- crear un estado `suspended` nuevo en `users.status`.

## Protecciones admin

- `support` no muta estados.
- `admin` no muta usuarios `admin` o `super_admin`.
- `super_admin` puede mutar `admin`, `support`, `business_owner` y `remitter` con reason/idempotencia/audit.
- Ningun actor puede bloquear o suspender el ultimo `super_admin active`.

## business_access_links.status

20A reusa transiciones de 14B1:
- `active -> suspended`
- `suspended -> active`
- `active|suspended -> revoked`
- `active|suspended -> blocked`

`revoked` y `blocked` no se reactivan en 20A salvo contrato futuro explicito.
