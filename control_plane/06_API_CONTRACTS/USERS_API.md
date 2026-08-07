# USERS_API.md

Contrato de usuario autenticado.

## GET /api/v1/users/me

Devuelve perfil propio del usuario autenticado.

Slice 14:
- La respuesta puede incluir capabilities/surfaces calculadas por backend si se mantiene dentro del contrato de `SURFACE_SESSION_API.md`.
- El frontend no puede inferir acceso a Mini App Negocio o Admin Web solo por `role`; debe usar backend capabilities.

Response 200:

```json
{
  "data": {
    "id": "uuid",
    "username": "string|null",
    "first_name": "string|null",
    "last_name": "string|null",
    "role": "remitter|business_owner|admin|super_admin|support",
    "status": "active|restricted|blocked|dormant",
    "trust_level": "string|null",
    "last_seen_at": "timestamp|null"
  },
  "request_id": "req_..."
}
```

Rules:

- Requiere JWT valido.
- Solo devuelve el perfil propio.
- No devuelve `telegram_id`.
- No devuelve secretos ni tokens.
- Usuario `blocked` o suspendido debe recibir error seguro en el siguiente
  request operativo; un valor stale en cache de proceso no puede autorizarlo.

## PATCH /api/v1/users/me

Post-MVP salvo aprobacion explicita.

No permite cambiar rol, status, trust_level ni Telegram ID desde usuario.

## Admin user control

Los endpoints admin para buscar usuarios, ver detalle operativo y cambiar estados viven en `ADMIN_API.md`.

Reglas:
- Usuario comun nunca cambia `role`, `status`, `trust_level` ni `telegram_id` desde `USERS_API.md`.
- `GET /api/v1/users/me` no reemplaza `GET /api/v1/surface/session`.
- `GET /api/v1/users/me` no devuelve permisos admin por si solo.
- `GET /api/v1/users/me` no devuelve permisos staff por si solo; Admin Web debe usar endpoints/capabilities backend de staff.
- Admin user control requiere backend RBAC, reason, idempotencia y audit segun `slice_20A_admin_users_business_control`.
